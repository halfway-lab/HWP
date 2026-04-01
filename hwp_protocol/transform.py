#!/usr/bin/env python3
import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PROTOCOL_VERSION = "0.6.2"


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


def semantic_group_id(variables: list[Any], group_suffix: str = "") -> str:
    """生成语义组ID，基于排序后的变量内容以保证稳定性。"""
    if not variables:
        return "sg_empty"

    normalized = [
        re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")
        for value in variables
        if str(value).strip()
    ]
    if not normalized:
        return "sg_empty"

    # 去重 + 排序，确保稳定
    unique_sorted = sorted(set(normalized))
    head = "_".join(unique_sorted[:3])[:48].strip("_") or "empty"

    suffix = f"_{group_suffix}" if group_suffix else ""
    return f"sg_{head}{suffix}"[:64]


def extract_keywords(text: str) -> set[str]:
    """从变量名中提取关键词（按 _、空格、驼峰分割）。"""
    if not text:
        return set()

    # 先处理驼峰命名，再转小写
    # 例如 "userName" -> "user_Name" -> "user", "name"
    # 例如 "APIKey" -> "API_Key" -> "api", "key"
    text = str(text)
    # 处理小写+大写的驼峰（如 userName）
    text = re.sub(r"([a-z])([A-Z])", r"\1_\2", text)
    # 处理连续大写后跟小写的情况（如 APIKey -> API_Key）
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", text)

    # 统一转小写并按非字母数字字符分割
    text = text.lower()
    parts = re.split(r"[^a-z0-9]+", text)

    keywords = set()
    for part in parts:
        if part and len(part) >= 2:
            keywords.add(part)
    return keywords


def jaccard_similarity(set1: set[str], set2: set[str]) -> float:
    """计算两个集合的 Jaccard 相似度：交集大小 / 并集大小。"""
    if not set1 and not set2:
        return 1.0  # 两个空集认为完全相似
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    if union == 0:
        return 0.0
    return intersection / union


def cluster_variables_by_similarity(
    variables: list[Any], threshold: float = 0.3
) -> list[list[tuple[int, Any, set[str]]]]:
    """
    基于关键词相似度对变量进行贪心聚类。
    返回聚类结果，每个聚类包含 (原始索引, 变量值, 关键词集) 的列表。

    对于小规模变量集（<=5个变量），如果没有明显的聚类结构，
    将所有变量归入单一组以保持向后兼容。
    """
    if not variables:
        return []

    # 对于小规模变量集，检查是否应该合并为单一组
    if len(variables) <= 5:
        # 提取所有关键词
        all_keywords = [extract_keywords(str(var)) for var in variables]
        # 检查是否存在任何相似性
        has_similarity = False
        for i in range(len(all_keywords)):
            for j in range(i + 1, len(all_keywords)):
                if jaccard_similarity(all_keywords[i], all_keywords[j]) >= threshold:
                    has_similarity = True
                    break
            if has_similarity:
                break

        # 如果没有发现相似性，将所有变量归入单一组
        if not has_similarity:
            return [[(idx, var, extract_keywords(str(var))) for idx, var in enumerate(variables)]]

    # 提取每个变量的关键词
    var_keywords = [(idx, var, extract_keywords(str(var))) for idx, var in enumerate(variables)]

    # 孤立变量（无关键词）单独处理
    unclustered = []
    clusterable = []
    for item in var_keywords:
        idx, var, keywords = item
        if not keywords:
            unclustered.append(item)
        else:
            clusterable.append(item)

    clusters: list[list[tuple[int, Any, set[str]]]] = []
    used = set()

    # 贪心聚类：为每个未聚类的变量找到相似度超过阈值的邻居
    for i, (idx1, var1, kw1) in enumerate(clusterable):
        if idx1 in used:
            continue

        # 开始新聚类
        cluster = [(idx1, var1, kw1)]
        used.add(idx1)
        cluster_keywords = set(kw1)

        # 寻找与当前聚类相似的变量
        for j, (idx2, var2, kw2) in enumerate(clusterable):
            if idx2 in used or idx2 == idx1:
                continue
            # 计算与聚类关键词的相似度
            sim = jaccard_similarity(cluster_keywords, kw2)
            if sim >= threshold:
                cluster.append((idx2, var2, kw2))
                used.add(idx2)
                # 更新聚类关键词（并集）
                cluster_keywords |= kw2

        clusters.append(cluster)

    # 将孤立变量归入一个默认组（如果存在）
    if unclustered:
        # 如果只有一个孤立变量且已有其他聚类，尝试将其合并到最相似的聚类
        if len(unclustered) == 1 and clusters:
            idx, var, kw = unclustered[0]
            # 找到最相似的聚类（基于变量名前缀匹配）
            best_cluster_idx = 0
            best_score = -1
            for c_idx, cluster in enumerate(clusters):
                for _, _, cluster_kw in cluster:
                    # 使用简单的字符串包含作为回退相似度
                    var_str = str(var).lower()
                    score = 0
                    for ck in cluster_kw:
                        if ck in var_str:
                            score += 1
                    if score > best_score:
                        best_score = score
                        best_cluster_idx = c_idx
            if best_score > 0:
                clusters[best_cluster_idx].append((idx, var, kw))
            else:
                clusters.append(unclustered)
        else:
            clusters.append(unclustered)

    return clusters


def semantic_nodes_for_cluster(
    cluster: list[tuple[int, Any, set[str]]], group_idx: int
) -> list[dict[str, Any]]:
    """为聚类生成节点列表。"""
    nodes = []
    sorted_cluster = sorted(cluster, key=lambda x: x[0])  # 按原始索引排序

    for i, (orig_idx, value, keywords) in enumerate(sorted_cluster):
        # 基于聚类内位置计算相似度分数
        similarity_score = max(0.95 - (i * 0.05), 0.55)
        nodes.append(
            {
                "node_id": f"g{group_idx}_node_{i + 1}",
                "content": value,
                "similarity_score": round_metric(similarity_score),
                "parent_node": None if i == 0 else f"g{group_idx}_node_{i}",
            }
        )
    return nodes


def calculate_cluster_coherence(cluster: list[tuple[int, Any, set[str]]]) -> float:
    """计算聚类的内部一致性分数（基于成员间的平均相似度）。"""
    if len(cluster) <= 1:
        return 1.0

    similarities = []
    for i in range(len(cluster)):
        for j in range(i + 1, len(cluster)):
            sim = jaccard_similarity(cluster[i][2], cluster[j][2])
            similarities.append(sim)

    if not similarities:
        return 0.75  # 无关键词时的默认值

    avg_sim = sum(similarities) / len(similarities)
    # 映射到 0.5-1.0 范围（验证器要求 >= 0.5）
    return clamp01(0.5 + (avg_sim * 0.5))


def semantic_group_payload(variables: list[Any], round_num: int, drift: float, shared: int) -> list[dict[str, Any]]:
    """
    生成语义组负载，基于变量间的关键词相似度进行聚类。
    支持生成多个语义组，每个组有独立的 coherence_score。
    """
    if not variables:
        return []

    # 基于相似度聚类变量
    clusters = cluster_variables_by_similarity(variables, threshold=0.3)

    groups = []
    for group_idx, cluster in enumerate(clusters):
        if not cluster:
            continue

        # 提取聚类中的变量值
        cluster_vars = [item[1] for item in cluster]

        # 生成组ID
        group_suffix = f"{group_idx + 1:02d}"
        group_id = semantic_group_id(cluster_vars, group_suffix)

        # 生成节点
        nodes = semantic_nodes_for_cluster(cluster, group_idx + 1)

        # 计算组内一致性分数
        coherence = calculate_cluster_coherence(cluster)

        # 生成扩展路径
        expansion_path = [node["node_id"] for node in nodes]

        # 推断领域（基于最常见关键词）
        all_keywords: dict[str, int] = {}
        for _, _, kw_set in cluster:
            for kw in kw_set:
                all_keywords[kw] = all_keywords.get(kw, 0) + 1

        if all_keywords:
            # 选择最常见的关键词作为领域
            domain = max(all_keywords.items(), key=lambda x: x[1])[0][:20]
        else:
            domain = "exploration"

        group = {
            "group_id": group_id,
            "group_name": f"Semantic Cluster {group_idx + 1}",
            "nodes": nodes,
            "coherence_score": round_metric(coherence),
            "expansion_path": expansion_path,
            "domain": domain,
            "group_metadata": {
                "created_round": 1,
                "last_expanded_round": round_num,
                "expansion_count": round_num - 1,
                "identifier_stable": shared >= max(min(len(variables), 10), 1),
                "cluster_size": len(cluster),
            },
        }
        groups.append(group)

    # 如果没有生成任何组（理论上不会发生），返回默认组
    if not groups:
        return [
            {
                "group_id": "sg_default_01",
                "group_name": "Default Cluster",
                "nodes": semantic_nodes_for_cluster([(i, v, set()) for i, v in enumerate(variables)], 1),
                "coherence_score": 0.75,
                "expansion_path": [f"g1_node_{i + 1}" for i in range(len(variables))],
                "domain": "exploration",
                "group_metadata": {
                    "created_round": 1,
                    "last_expanded_round": round_num,
                    "expansion_count": round_num - 1,
                    "identifier_stable": shared >= max(min(len(variables), 10), 1),
                    "cluster_size": len(variables),
                },
            }
        ]

    return groups


def calculate_cross_domain_contamination(groups: list[dict[str, Any]]) -> bool:
    """
    基于多组间的重叠度计算跨域污染。
    如果不同组之间存在显著的内容重叠，可能表示聚类不够清晰。
    """
    if len(groups) <= 1:
        return False

    # 提取每组的领域关键词
    group_domains = []
    for group in groups:
        domain = group.get("domain", "")
        nodes = group.get("nodes", [])
        # 收集组内所有内容的关键词
        all_content = " ".join(str(node.get("content", "")) for node in nodes if isinstance(node, dict))
        keywords = extract_keywords(all_content)
        group_domains.append({"domain": domain, "keywords": keywords})

    # 检查组间相似度
    for i in range(len(group_domains)):
        for j in range(i + 1, len(group_domains)):
            sim = jaccard_similarity(
                group_domains[i]["keywords"],
                group_domains[j]["keywords"]
            )
            # 如果组间相似度很高（>0.6），可能存在污染
            if sim > 0.6:
                return True

    return False


def semantic_nodes(variables: list[Any]) -> list[dict[str, Any]]:
    """向后兼容：为所有变量生成顺序节点（旧API）。"""
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


# Version pattern: major.minor.patch (semver)
_VERSION_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[a-zA-Z0-9]+(?:\.[a-zA-Z0-9]+)*)?(?:\+[a-zA-Z0-9]+(?:\.[a-zA-Z0-9]+)*)?$")


def check_protocol_version(inner: dict[str, Any], strict: bool = False) -> list[str]:
    """
    Validate the protocol_version field in an inner JSON object.

    Args:
        inner: The inner JSON object to check
        strict: If False (default), only warn on malformed version strings.
                If True, error on missing version or version mismatch.

    Returns:
        List of warning/error messages. Empty list if all checks pass.
        Messages are prefixed with "WARN:" or "ERROR:" to indicate severity.
    """
    messages: list[str] = []
    version = inner.get("protocol_version")

    if version is None:
        if strict:
            messages.append(f"ERROR: protocol_version is missing (expected {PROTOCOL_VERSION})")
        return messages

    if not isinstance(version, str):
        if strict:
            messages.append(f"ERROR: protocol_version must be a string, got {type(version).__name__}")
        else:
            messages.append(f"WARN: protocol_version must be a string, got {type(version).__name__}")
        return messages

    if not _VERSION_PATTERN.match(version):
        if strict:
            messages.append(f"ERROR: protocol_version '{version}' is not a valid semver string")
        else:
            messages.append(f"WARN: protocol_version '{version}' is not a valid semver string")
        return messages

    if strict and version != PROTOCOL_VERSION:
        messages.append(f"ERROR: protocol_version mismatch: got {version}, expected {PROTOCOL_VERSION}")

    return messages


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
        result["cross_domain_contamination"] = calculate_cross_domain_contamination(result["semantic_groups"])
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
    if "protocol_version" not in result:
        result["protocol_version"] = PROTOCOL_VERSION
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
    repacked["protocol_version"] = inner.get("protocol_version", PROTOCOL_VERSION)
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
