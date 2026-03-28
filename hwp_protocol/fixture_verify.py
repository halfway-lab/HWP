#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from typing import Any


def validate_blind_spot(sample_data: dict[str, Any], _: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if "blind_spot_score" not in sample_data:
        errors.append("Missing blind_spot_score")
    if "blind_spot_signals" not in sample_data:
        errors.append("Missing blind_spot_signals")
    if "blind_spot_reason" not in sample_data:
        errors.append("Missing blind_spot_reason")

    score = sample_data.get("blind_spot_score")
    if score is not None:
        if not isinstance(score, (int, float)):
            errors.append(f"blind_spot_score is not numeric: {type(score)}")
        elif score < 0.0 or score > 1.0:
            errors.append(f"blind_spot_score out of range: {score}")

    signals = sample_data.get("blind_spot_signals")
    if signals is not None and not isinstance(signals, list):
        errors.append(f"blind_spot_signals is not array: {type(signals)}")
    if signals is None and "blind_spot_signals" in sample_data:
        errors.append("blind_spot_signals is null (should be array)")

    if isinstance(signals, list):
        valid_types = {"information_gap", "logic_break", "assumption_conflict", "boundary_blindspot"}
        valid_severities = {"low", "medium", "high", "critical"}
        for idx, signal in enumerate(signals):
            if not isinstance(signal, dict):
                continue
            sig_type = signal.get("type", "")
            if sig_type and sig_type not in valid_types:
                errors.append(f"Signal[{idx}]: invalid type '{sig_type}'")
            severity = signal.get("severity", "")
            if severity and severity not in valid_severities:
                errors.append(f"Signal[{idx}]: invalid severity '{severity}'")

    return errors


def validate_continuity(sample_data: dict[str, Any], sample: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    round_num = sample.get("round", 0)

    if "node_id" not in sample_data:
        errors.append("Missing node_id")
    if "variables" not in sample_data:
        errors.append("Missing variables")
    if "shared_variable_count" not in sample_data:
        errors.append("Missing shared_variable_count")
    if "drift_rate" not in sample_data:
        errors.append("Missing drift_rate")

    variables = sample_data.get("variables", [])
    shared_count = sample_data.get("shared_variable_count", 0)
    drift_rate = sample_data.get("drift_rate", 0)
    tensions = sample_data.get("tensions", [])
    parent_id = sample_data.get("parent_id")
    collapse_detected = sample_data.get("collapse_detected", False)

    if round_num > 1:
        if shared_count < 10:
            errors.append(f"shared_variable_count too low: {shared_count} (threshold: 10)")
        if drift_rate > 0.6:
            errors.append(f"drift_rate too high: {drift_rate} (threshold: 0.6)")
        if collapse_detected and drift_rate > 0.6:
            errors.append(f"collapse_detected=true with high drift_rate: {drift_rate}")

    if round_num > 1 and len(tensions) == 0:
        errors.append("tensions array is empty (lost tension lineage)")

    if round_num > 1 and parent_id is None:
        errors.append("parent_id is null (broken chain continuity)")

    if len(variables) > 0:
        if shared_count > len(variables):
            errors.append(f"shared_variable_count ({shared_count}) exceeds total variables ({len(variables)})")
        valid_prefixes = ("var_", "new_var_", "stabilized_")
        actual_shared = sum(1 for value in variables if isinstance(value, str) and value.startswith(valid_prefixes))
        if round_num > 1 and actual_shared > 0 and actual_shared - shared_count > 10:
            errors.append(
                f"shared_variable_count ({shared_count}) significantly less than actual shared variables ({actual_shared})"
            )

    if collapse_detected and drift_rate < 0.5:
        errors.append(f"collapse_detected=true but drift_rate ({drift_rate}) is low")

    return errors


def validate_semantic_groups(sample_data: dict[str, Any], _: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    semantic_groups = sample_data.get("semantic_groups", [])
    cross_domain_contamination = sample_data.get("cross_domain_contamination", False)

    if not semantic_groups:
        errors.append("No semantic_groups found")
    else:
        for idx, group in enumerate(semantic_groups):
            if not isinstance(group, dict):
                errors.append(f"Group[{idx}]: not an object")
                continue
            group_id = group.get("group_id")
            coherence_score = group.get("coherence_score", 0)
            nodes = group.get("nodes", [])
            expansion_path = group.get("expansion_path", [])

            if group_id is None:
                errors.append(f"Group[{idx}]: group_id is null")
            elif not isinstance(group_id, str):
                errors.append(f"Group[{idx}]: group_id is not string: {type(group_id)}")

            previous_id = group.get("previous_group_id")
            if previous_id and group_id != previous_id:
                errors.append(f"Group[{idx}]: group_id changed from {previous_id} to {group_id}")

            if coherence_score < 0.5:
                errors.append(f"Group[{idx}]: coherence_score {coherence_score} below threshold (0.5)")

            node_ids = {node.get("node_id") for node in nodes if isinstance(node, dict)}
            path_ids = set(expansion_path)
            if path_ids and not path_ids.issubset(node_ids):
                missing = path_ids - node_ids
                errors.append(f"Group[{idx}]: expansion_path contains unknown nodes: {missing}")

            null_parent_count = 0
            for node_idx, node in enumerate(nodes):
                if not isinstance(node, dict):
                    continue
                parent_node = node.get("parent_node")
                node_id = node.get("node_id", f"Node[{node_idx}]")
                if parent_node is not None and parent_node not in node_ids:
                    errors.append(f"Group[{idx}].{node_id}: parent_node '{parent_node}' not found in group")
                if parent_node is None and "parent_node" in node:
                    null_parent_count += 1

            if null_parent_count > 1:
                errors.append(f"Group[{idx}]: {null_parent_count} nodes have parent_node=null (untraceable expansion)")

            contaminated = group.get("contaminated_domains", [])
            if contaminated:
                errors.append(f"Group[{idx}]: has contaminated_domains: {contaminated}")

    if cross_domain_contamination:
        errors.append("cross_domain_contamination flag is true")

    for group in semantic_groups:
        if not isinstance(group, dict):
            continue
        for node in group.get("nodes", []):
            if isinstance(node, dict) and node.get("contamination_flag"):
                errors.append(f"Node {node.get('node_id', '?')} has contamination_flag=true")

    return errors


VALIDATORS = {
    "blind_spot": validate_blind_spot,
    "continuity": validate_continuity,
    "semantic_groups": validate_semantic_groups,
}


def run_fixture_suite(suite: str, fixture_type: str) -> int:
    validator = VALIDATORS.get(suite)
    if validator is None:
        print(f"[ERROR] Unknown suite: {suite}")
        return 1

    fixture_file = Path(f"./tests/fixtures/{suite}_{fixture_type}.json")

    try:
        with fixture_file.open("r", encoding="utf-8") as handle:
            data = json.load(handle)

        samples = data.get("samples", [])
        total = len(samples)
        passed = 0
        failed = 0

        print(f"Testing {total} samples from {fixture_file}")
        print("")

        for idx, sample in enumerate(samples, 1):
            name = sample.get("name", f"Sample {idx}")
            sample_data = sample.get("data", {})
            expected = sample.get("expected_result", "PASS")
            violation = sample.get("violation", "")
            round_num = sample.get("round")

            if suite == "continuity" and round_num is not None:
                print(f"[{idx}/{total}] Round {round_num}: {name}")
            else:
                print(f"[{idx}/{total}] {name}")

            errors = validator(sample_data, sample)

            if expected == "PASS":
                if errors:
                    print("  [FAIL] Expected PASS but got errors:")
                    for error in errors:
                        print(f"    - {error}")
                    failed += 1
                else:
                    print("  [PASS] All validations passed")
                    passed += 1
            else:
                if errors:
                    print("  [PASS] Expected FAIL, detected errors:")
                    for error in errors:
                        print(f"    - {error}")
                    if violation:
                        print(f"    (Expected: {violation})")
                    passed += 1
                else:
                    print("  [FAIL] Expected FAIL but no errors found")
                    failed += 1
            print("")

        print("=" * 50)
        print(f"Fixture Test Summary: {passed} passed, {failed} failed (total: {total})")
        return 0 if failed == 0 else 1
    except Exception as exc:
        print(f"[ERROR] Failed to process fixture: {exc}")
        return 1


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: hwp_v06_fixture_verify.py <blind_spot|continuity|semantic_groups> <valid|invalid>", file=sys.stderr)
        return 1

    suite = sys.argv[1]
    fixture_type = sys.argv[2]
    return run_fixture_suite(suite, fixture_type)


if __name__ == "__main__":
    raise SystemExit(main())
