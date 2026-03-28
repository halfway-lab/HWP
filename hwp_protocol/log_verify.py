#!/usr/bin/env python3
from dataclasses import dataclass
import sys
from pathlib import Path
from typing import Any

from hwp_protocol.jsonl_utils import iter_record_pairs, load_jsonl


@dataclass(frozen=True)
class VerificationMessage:
    status: str
    message: str


def emit(status: str, message: str) -> None:
    print(f"{status}|{message}")


def render_messages(messages: list[VerificationMessage]) -> None:
    for item in messages:
        emit(item.status, item.message)


def has_failures(messages: list[VerificationMessage]) -> bool:
    return any(item.status == "FAIL" for item in messages)


def collect_blind_spot_messages(path: Path) -> list[VerificationMessage]:
    records = load_jsonl(path)
    record_pairs = iter_record_pairs(records)
    if not records:
        return [
            VerificationMessage("WARN", "无法检查 blind_spot_signals（无可解析日志记录）"),
            VerificationMessage("WARN", "无法检查 blind_spot_score（无可解析日志记录）"),
            VerificationMessage("WARN", "无法检查 blind_spot_reason（无可解析日志记录）"),
            VerificationMessage("WARN", "无法检查范围（无可解析日志记录）"),
            VerificationMessage("WARN", "无法检查字段类型（无可解析日志记录）"),
        ]

    messages: list[VerificationMessage] = []

    signals_present = any(
        "blind_spot_signals" in record or "blind_spot_signals" in inner for record, inner in record_pairs
    )
    if signals_present:
        messages.append(VerificationMessage("PASS", "日志包含 blind_spot_signals 字段"))
        non_array = 0
        null_signals = 0
        checked = 0
        for record in records:
            value = record.get("blind_spot_signals")
            if value is None and "blind_spot_signals" in record:
                null_signals += 1
            elif "blind_spot_signals" in record:
                checked += 1
                if not isinstance(value, list):
                    non_array += 1
        if null_signals > 0:
            messages.append(VerificationMessage("FAIL", f"检测到 {null_signals} 处 blind_spot_signals 为 null（应为数组）"))
        elif non_array > 0:
            messages.append(VerificationMessage("WARN", "blind_spot_signals 可能不是数组类型"))
        else:
            messages.append(VerificationMessage("PASS", "blind_spot_signals 为数组类型"))
            messages.append(VerificationMessage("PASS", "blind_spot_signals 类型正确（非 null）"))
    else:
        messages.append(VerificationMessage("WARN", "日志中未找到 blind_spot_signals 字段（字段为 OPTIONAL）"))

    scores: list[Any] = [record["blind_spot_score"] for record in records if "blind_spot_score" in record]
    if scores:
        messages.append(VerificationMessage("PASS", "日志包含 blind_spot_score 字段"))
        invalid_scores = []
        string_scores = 0
        for score in scores:
            if isinstance(score, (int, float)):
                if 0.0 <= float(score) <= 1.0:
                    messages.append(VerificationMessage("PASS", f"blind_spot_score={score} 在有效范围 [0.0, 1.0] 内"))
                else:
                    invalid_scores.append(score)
            else:
                string_scores += 1
                invalid_scores.append(score)
        if invalid_scores:
            for invalid in invalid_scores:
                messages.append(
                    VerificationMessage("FAIL", f"检测到无效的 blind_spot_score: {invalid}（必须在 0.0-1.0 范围内）")
                )
        else:
            messages.append(VerificationMessage("PASS", "未发现超出范围的 blind_spot_score"))
        if string_scores > 0:
            messages.append(VerificationMessage("FAIL", f"检测到 {string_scores} 处 blind_spot_score 为字符串（应为数值）"))
        else:
            messages.append(VerificationMessage("PASS", "blind_spot_score 类型正确（数值型）"))
    else:
        messages.append(VerificationMessage("WARN", "日志中未找到 blind_spot_score 字段（字段为 OPTIONAL）"))
        messages.append(VerificationMessage("WARN", "无法检查范围（无 blind_spot_score 数据）"))
        messages.append(VerificationMessage("WARN", "无法检查字段类型（无 blind_spot_score 数据）"))

    reasons = [record["blind_spot_reason"] for record in records if "blind_spot_reason" in record]
    if reasons:
        messages.append(VerificationMessage("PASS", "日志包含 blind_spot_reason 字段"))
        if all(isinstance(reason, str) for reason in reasons):
            messages.append(VerificationMessage("PASS", "blind_spot_reason 为字符串类型"))
        else:
            messages.append(VerificationMessage("WARN", "blind_spot_reason 可能不是字符串类型"))
    else:
        messages.append(VerificationMessage("WARN", "日志中未找到 blind_spot_reason 字段（字段为 OPTIONAL）"))

    return messages


def collect_continuity_messages(path: Path) -> list[VerificationMessage]:
    records = load_jsonl(path)
    record_pairs = iter_record_pairs(records)
    if not records:
        return [VerificationMessage("WARN", "无日志文件可供分析")]

    messages: list[VerificationMessage] = []

    has_round = any(("round" in record) or ("turn" in record) or ("round" in inner) for record, inner in record_pairs)
    if has_round:
        messages.append(VerificationMessage("PASS", "日志包含轮次信息"))
    else:
        messages.append(VerificationMessage("WARN", "日志中未找到明确的轮次标记"))

    has_state = any(
        any(key in record for key in ("continuity_score", "state_snapshot", "context"))
        or any(key in inner for key in ("continuity_score", "state_snapshot", "context"))
        for record, inner in record_pairs
    )
    if has_state:
        messages.append(VerificationMessage("PASS", "日志包含状态/上下文字段"))
    else:
        messages.append(VerificationMessage("WARN", "日志中未找到明确的状态/上下文字段"))
    return messages


def collect_semantic_groups_messages(path: Path) -> list[VerificationMessage]:
    records = load_jsonl(path)
    record_pairs = iter_record_pairs(records)
    if not records:
        return [
            VerificationMessage("WARN", "无日志文件可供分析"),
            VerificationMessage("WARN", "无法检查语义组标识符（无可解析日志记录）"),
            VerificationMessage("WARN", "无法检查跨域污染（无可解析日志记录）"),
        ]

    messages: list[VerificationMessage] = []

    has_group_fields = any(
        any(key in record for key in ("semantic_groups", "group_id", "group_count"))
        or any(key in inner for key in ("semantic_groups", "group_id", "group_count"))
        for record, inner in record_pairs
    )
    if has_group_fields:
        messages.append(VerificationMessage("PASS", "日志包含语义组相关字段"))
    else:
        messages.append(VerificationMessage("WARN", "日志中未找到语义组字段（待 V06-003 完成后实现）"))

    has_coherence = any(
        any(key in record for key in ("semantic_coherence", "group_consistency"))
        or any(key in inner for key in ("semantic_coherence", "group_consistency"))
        for record, inner in record_pairs
    )
    if has_coherence:
        messages.append(VerificationMessage("PASS", "日志包含语义一致性标记"))
    else:
        messages.append(VerificationMessage("WARN", "日志中未找到语义一致性标记（待 V06-003 完成后实现）"))

    null_groups = 0
    contamination_hits = 0
    for record, inner in record_pairs:
        groups = record.get("semantic_groups")
        if not isinstance(groups, list):
            groups = inner.get("semantic_groups") if isinstance(inner.get("semantic_groups"), list) else []
        for group in groups:
            if not isinstance(group, dict):
                continue
            if "group_id" in group and group.get("group_id") is None:
                null_groups += 1
            if group.get("contaminated_domains"):
                contamination_hits += 1
            for node in group.get("nodes", []):
                if isinstance(node, dict) and node.get("contamination_flag") is True:
                    contamination_hits += 1
        if record.get("cross_domain_contamination") is True or inner.get("cross_domain_contamination") is True:
            contamination_hits += 1

    if null_groups > 0:
        messages.append(VerificationMessage("FAIL", f"检测到 {null_groups} 处语义组标识符为空（group_id: null）"))
    else:
        messages.append(VerificationMessage("PASS", "未发现语义组标识符断裂"))

    if contamination_hits > 0:
        messages.append(VerificationMessage("FAIL", f"检测到 {contamination_hits} 处跨域污染标记"))
    else:
        messages.append(VerificationMessage("PASS", "未发现跨域污染标记"))
    return messages


def verify_blind_spot(path: Path) -> int:
    messages = collect_blind_spot_messages(path)
    render_messages(messages)
    return 1 if has_failures(messages) else 0


def verify_continuity(path: Path) -> int:
    messages = collect_continuity_messages(path)
    render_messages(messages)
    return 1 if has_failures(messages) else 0


def verify_semantic_groups(path: Path) -> int:
    messages = collect_semantic_groups_messages(path)
    render_messages(messages)
    return 1 if has_failures(messages) else 0


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: python3 -m hwp_protocol.log_verify <blind_spot|continuity|semantic_groups> <log_path>",
            file=sys.stderr,
        )
        return 1

    suite = sys.argv[1]
    path = Path(sys.argv[2])
    if not path.exists():
        print("WARN|无日志文件可供分析")
        return 0

    if suite == "blind_spot":
        return verify_blind_spot(path)
    if suite == "continuity":
        return verify_continuity(path)
    if suite == "semantic_groups":
        return verify_semantic_groups(path)

    print(f"unknown suite: {suite}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
