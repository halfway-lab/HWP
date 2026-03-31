#!/usr/bin/env python3
import json
import re
import sys
from collections.abc import Mapping
from typing import Any


def clamp01(value: float) -> float:
    if value < 0:
        return 0.0
    if value > 1:
        return 1.0
    return value


def safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def round_metric(value: float) -> float:
    return round(value, 2)


def clamp_int(value: Any, minimum: int, maximum: int) -> int:
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        return minimum
    if numeric < minimum:
        return minimum
    if numeric > maximum:
        return maximum
    return numeric


def ensure_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a JSON object")
    return dict(value)


def parse_json_object_arg(raw: str, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} must be valid JSON: {exc}") from exc
    return ensure_object(value, label)


def parse_round_arg(raw: str) -> int:
    try:
        round_num = int(raw)
    except ValueError as exc:
        raise ValueError("round must be an integer") from exc
    if round_num < 1:
        raise ValueError("round must be >= 1")
    return round_num


def parse_bool_arg(raw: str, label: str) -> bool:
    normalized = raw.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError(f"{label} must be 'true' or 'false'")


def tension_id(idx: int, value: Any) -> str:
    if isinstance(value, dict) and value.get("id"):
        return str(value["id"])
    return f"tension_{idx + 1:02d}"


def normalize_tensions(inner: dict[str, Any]) -> list[dict[str, Any]]:
    tensions = inner.get("tensions") or []
    normalized = []
    for idx, value in enumerate(tensions):
        if isinstance(value, dict):
            description = value.get("description") or value.get("id") or f"Tension {idx + 1}"
            status = value.get("status") or "active"
        else:
            description = str(value)
            status = "active"
        normalized.append(
            {
                "id": tension_id(idx, value),
                "description": description,
                "status": status,
            }
        )
    return normalized


def severity_from_impact(impact: str) -> str:
    impact_text = (impact or "").lower()
    if re.search(r"critical|severe|irreversible|fundamental", impact_text):
        return "high"
    return "medium"


def blind_spot_signals_from_paths(inner: dict[str, Any]) -> list[dict[str, Any]]:
    signals = []
    for path in inner.get("paths") or []:
        if not isinstance(path, dict):
            continue
        blind_spot = path.get("blind_spot") or {}
        if not isinstance(blind_spot, dict):
            continue
        description = blind_spot.get("description") or ""
        if not description:
            continue
        signals.append(
            {
                "type": "information_gap",
                "description": description,
                "severity": severity_from_impact(blind_spot.get("impact") or ""),
            }
        )
    return signals


def blind_spot_score_from_signals(signals: list[dict[str, Any]]) -> float:
    if not signals:
        return 0.0
    score = 0.0
    for signal in signals:
        score += 0.30 if signal.get("severity") == "high" else 0.18
    return clamp01(score)


def semantic_group_id(variables: list[Any]) -> str:
    if not variables:
        return "sg_empty"
    normalized = [
        re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")
        for value in variables
        if str(value).strip()
    ]
    if not normalized:
        return "sg_empty"
    head = "_".join(sorted(set(normalized))[:3])[:48].strip("_") or "empty"
    return "sg_" + head


def semantic_nodes(variables: list[Any]) -> list[dict[str, Any]]:
    nodes = []
    for idx, value in enumerate(variables):
        similarity_score = max((100 - idx) / 100, 0.55)
        nodes.append(
            {
                "node_id": f"var_node_{idx + 1}",
                "content": value,
                "similarity_score": similarity_score,
                "parent_node": None if idx == 0 else f"var_node_{idx}",
            }
        )
    return nodes


def semantic_group_payload(variables: list[Any], round_num: int, drift: float, shared: int) -> list[dict[str, Any]]:
    if not variables:
        return []
    return [
        {
            "group_id": semantic_group_id(variables),
            "group_name": "Primary Exploration Cluster",
            "nodes": semantic_nodes(variables),
            "coherence_score": clamp01(1 - (drift / 2)),
            "expansion_path": [f"var_node_{idx + 1}" for idx in range(len(variables))],
            "domain": "exploration",
            "group_metadata": {
                "created_round": 1,
                "last_expanded_round": round_num,
                "expansion_count": round_num - 1,
                "identifier_stable": shared >= max(min(len(variables), 10), 1),
            },
        }
    ]


def normalize_variable_payload(result: dict[str, Any]) -> list[str]:
    variables = result.get("variables")
    if not isinstance(variables, list):
        return []

    normalized = list(variables)
    notes = []

    if len(normalized) > 30:
        notes.append(f"Trimmed variables from {len(normalized)} to protocol max 30")
        normalized = normalized[:30]

    if normalized != variables:
        result["variables"] = normalized

    shared_count = result.get("shared_variable_count")
    if isinstance(shared_count, int) and shared_count > len(normalized):
        result["shared_variable_count"] = len(normalized)
        notes.append(f"Clamped shared_variable_count to {len(normalized)}")

    if notes:
        speed_metrics = result.get("speed_metrics")
        if not isinstance(speed_metrics, Mapping):
            speed_metrics = {}
        else:
            speed_metrics = dict(speed_metrics)
        actions = speed_metrics.get("action_taken")
        if isinstance(actions, list):
            action_taken = list(actions)
        else:
            action_taken = []
        action_taken.extend(notes)
        speed_metrics["action_taken"] = action_taken
        result["speed_metrics"] = speed_metrics

    return normalized


def derive_metric_snapshot(
    result: dict[str, Any],
    variables: list[str],
    parent_recovery_applied: bool,
) -> dict[str, Any]:
    variable_count = len(variables)
    parent_id = result.get("parent_id")
    shared_count = clamp_int(result.get("shared_variable_count", 0), 0, variable_count if variable_count else 0)

    if parent_id is None:
        shared_count = 0
        drift_rate = 0.0
        novelty_rate = 1.0
        collapse_detected = False
        recovery_applied = False
        mode = "Rg0"
    else:
        drift_rate = 1.0 if variable_count == 0 else round_metric(clamp01(1 - (shared_count / variable_count)))
        novelty_rate = 0.0 if variable_count == 0 else round_metric(clamp01((variable_count - shared_count) / variable_count))
        entropy_score = safe_float(result.get("entropy_score"), 0.0)
        collapse_detected = (
            variable_count > 30
            or drift_rate >= 0.70
            or (entropy_score >= 0.80 and drift_rate >= 0.30)
            or (novelty_rate <= 0.12 and drift_rate >= 0.30)
        )
        recovery_applied = collapse_detected
        if collapse_detected or parent_recovery_applied:
            mode = "Rg0"
        elif drift_rate < 0.30:
            mode = "Rg1"
        elif drift_rate > 0.70:
            mode = "Rg2"
        else:
            mode = "Rg0"

    return {
        "shared_variable_count": shared_count,
        "drift_rate": drift_rate,
        "novelty_rate": novelty_rate,
        "collapse_detected": collapse_detected,
        "recovery_applied": recovery_applied,
        "mode": mode,
    }


def apply_protocol_defaults(
    result: dict[str, Any],
    variables: list[str],
    parent_recovery_applied: bool,
) -> None:
    snapshot = derive_metric_snapshot(result, variables, parent_recovery_applied)
    result["shared_variable_count"] = snapshot["shared_variable_count"]
    result["drift_rate"] = snapshot["drift_rate"]
    result["novelty_rate"] = snapshot["novelty_rate"]
    result["collapse_detected"] = snapshot["collapse_detected"]
    result["recovery_applied"] = snapshot["recovery_applied"]

    speed_metrics = result.get("speed_metrics")
    if not isinstance(speed_metrics, Mapping):
        speed_metrics = {}
    else:
        speed_metrics = dict(speed_metrics)
    actions = speed_metrics.get("action_taken")
    if isinstance(actions, list):
        action_taken = list(actions)
    else:
        action_taken = []
    speed_metrics["mode"] = snapshot["mode"]
    speed_metrics["unfinished_inherited_count"] = clamp_int(
        speed_metrics.get("unfinished_inherited_count", 0),
        0,
        len(result.get("unfinished") or []),
    )
    speed_metrics["action_taken"] = action_taken
    result["speed_metrics"] = speed_metrics

    if snapshot["recovery_applied"]:
        keep_count = snapshot["shared_variable_count"]
        result["recovery_kept_variables"] = variables[:keep_count]
        result["recovery_new_variables"] = variables[keep_count:]
    else:
        result.pop("recovery_kept_variables", None)
        result.pop("recovery_new_variables", None)


def enrich_inner_json(inner: dict[str, Any], round_num: int, parent_recovery_applied: bool) -> dict[str, Any]:
    inner = ensure_object(inner, "inner_json")
    normalized_tensions = normalize_tensions(inner)
    derived_signals = blind_spot_signals_from_paths(inner)
    result = dict(inner)
    result["tensions"] = normalized_tensions
    variables = normalize_variable_payload(result)
    apply_protocol_defaults(result, variables, parent_recovery_applied)

    if "blind_spot_signals" not in result:
        result["blind_spot_signals"] = derived_signals
    if "blind_spot_score" not in result:
        result["blind_spot_score"] = blind_spot_score_from_signals(result["blind_spot_signals"])
    if "blind_spot_reason" not in result:
        if result["blind_spot_signals"]:
            result["blind_spot_reason"] = (
                f"Detected {len(result['blind_spot_signals'])} blind spot signals across current exploration paths"
            )
        else:
            result["blind_spot_reason"] = ""

    if "semantic_groups" not in result:
        result["semantic_groups"] = semantic_group_payload(
            variables,
            int(result.get("round", round_num)),
            safe_float(result.get("drift_rate"), 0.35),
            clamp_int(result.get("shared_variable_count", 0), 0, len(variables) if variables else 0),
        )
    if "group_count" not in result:
        result["group_count"] = len(result["semantic_groups"])
    if "cross_domain_contamination" not in result:
        result["cross_domain_contamination"] = False
    if "round_id" not in result:
        result["round_id"] = f"round_{round_num}"
    if "continuity_score" not in result:
        if result.get("parent_id") is None:
            result["continuity_score"] = 1
        elif variables:
            result["continuity_score"] = clamp01((result.get("shared_variable_count", 0) or 0) / len(variables))
        else:
            result["continuity_score"] = 0
    if "state_snapshot" not in result:
        if result.get("parent_id") is None:
            continuity_notes = ["Initial round establishes baseline state snapshot"]
        else:
            continuity_notes = [
                f"Inherited {result.get('shared_variable_count', 0) or 0} variables from parent",
                f"Maintained {len(result.get('tensions') or [])} active tensions into current round",
            ]
            if parent_recovery_applied:
                continuity_notes.append("Parent round used recovery; stabilization continuity applied")
        result["state_snapshot"] = {
            "inherited_variable_count": result.get("shared_variable_count", 0) or 0,
            "active_tension_ids": [tension.get("id") for tension in result.get("tensions") or [] if isinstance(tension, dict)],
            "parent_recovery_applied": parent_recovery_applied,
            "continuity_notes": continuity_notes,
        }
    return result


def repack_result_with_inner(result: dict[str, Any], inner: dict[str, Any]) -> dict[str, Any]:
    result = ensure_object(result, "result_json")
    inner = ensure_object(inner, "inner_json")
    repacked = dict(result)
    inner_text = json.dumps(inner, ensure_ascii=False, separators=(",", ":"))

    payloads = repacked.get("payloads")
    if isinstance(payloads, list) and payloads:
        new_payloads = list(payloads)
        first_payload = dict(new_payloads[0]) if isinstance(new_payloads[0], dict) else {}
        first_payload["text"] = inner_text
        new_payloads[0] = first_payload
        repacked["payloads"] = new_payloads
    else:
        repacked["payloads"] = [{"text": inner_text, "mediaUrl": None}]

    repacked["round"] = inner.get("round", repacked.get("round"))
    repacked["round_id"] = inner.get("round_id", repacked.get("round_id"))
    repacked["blind_spot_signals"] = inner.get("blind_spot_signals", [])
    repacked["blind_spot_score"] = inner.get("blind_spot_score", 0)
    repacked["blind_spot_reason"] = inner.get("blind_spot_reason", "")
    repacked["semantic_groups"] = inner.get("semantic_groups", [])
    repacked["group_count"] = inner.get("group_count", 0)
    semantic_groups = inner.get("semantic_groups") or []
    repacked["semantic_coherence"] = semantic_groups[0].get("coherence_score") if semantic_groups else None
    repacked["continuity_score"] = inner.get("continuity_score")
    repacked["state_snapshot"] = inner.get("state_snapshot", {})
    return repacked


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python3 -m hwp_protocol.transform <enrich|repack> ...", file=sys.stderr)
        return 1

    command = sys.argv[1]
    try:
        if command == "enrich":
            if len(sys.argv) != 5:
                print(
                    "usage: python3 -m hwp_protocol.transform enrich <inner_json> <round> <parent_recovery>",
                    file=sys.stderr,
                )
                return 1
            inner = parse_json_object_arg(sys.argv[2], "inner_json")
            round_num = parse_round_arg(sys.argv[3])
            parent_recovery_applied = parse_bool_arg(sys.argv[4], "parent_recovery")
            output = enrich_inner_json(inner, round_num, parent_recovery_applied)
        elif command == "repack":
            if len(sys.argv) != 4:
                print(
                    "usage: python3 -m hwp_protocol.transform repack <result_json> <inner_json>",
                    file=sys.stderr,
                )
                return 1
            result = parse_json_object_arg(sys.argv[2], "result_json")
            inner = parse_json_object_arg(sys.argv[3], "inner_json")
            output = repack_result_with_inner(result, inner)
        else:
            print(f"unknown command: {command}", file=sys.stderr)
            return 1
    except Exception as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(output, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
