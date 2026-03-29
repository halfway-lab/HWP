#!/usr/bin/env python3
"""
HWP 失败分类与日志汇总 - 第4步

用途：自动分析 benchmark 运行日志，分类失败类型，生成汇总报告

失败类型分类：
1. TRANSPORT_ERROR - Provider 网络/连接错误
2. TIMEOUT - 请求超时
3. NON_JSON_RESPONSE - 返回非 JSON 格式
4. MALFORMED_JSON - JSON 格式错误
5. MISSING_REQUIRED_FIELDS - 缺少必填字段
6. PROVIDER_BLOCK - Provider 安全拦截/拒绝
7. PROTOCOL_REGRESSION - 协议质量回归
8. UNKNOWN - 未知错误
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# 失败类型定义
FAILURE_TYPES = {
    "TRANSPORT_ERROR": {
        "patterns": [
            r"connection.*refused",
            r"connection.*reset",
            r"network.*unreachable",
            r"dns.*error",
            r"ssl.*error",
            r"certificate.*verify.*failed",
        ],
        "description": "Provider 网络/连接错误",
    },
    "TIMEOUT": {
        "patterns": [
            r"timeout",
            r"timed out",
            r"deadline exceeded",
            r"context deadline",
        ],
        "description": "请求超时",
    },
    "NON_JSON_RESPONSE": {
        "patterns": [
            r"invalid json",
            r"json decode error",
            r"expecting.*json",
            r"not valid json",
        ],
        "description": "返回非 JSON 格式",
    },
    "MALFORMED_JSON": {
        "patterns": [
            r"json parse failed",
            r"unexpected token",
            r"invalid character",
            r"malformed json",
        ],
        "description": "JSON 格式错误",
    },
    "MISSING_REQUIRED_FIELDS": {
        "patterns": [
            r"missing.*field",
            r"required field",
            r"field.*not found",
            r"MISSING_FIELDS",
        ],
        "description": "缺少必填字段",
    },
    "PROVIDER_BLOCK": {
        "patterns": [
            r"safety.*block",
            r"content.*filter",
            r"policy.*violation",
            r"blocked",
            r"refused",
            r"moderation",
        ],
        "description": "Provider 安全拦截/拒绝",
    },
    "PROTOCOL_REGRESSION": {
        "patterns": [
            r"constraint.*failed",
            r"validation.*failed",
            r"out of range",
            r"not in \[",
        ],
        "description": "协议质量回归",
    },
}


def classify_error(error_text: str) -> str:
    """根据错误文本分类失败类型"""
    error_lower = error_text.lower()
    
    for failure_type, config in FAILURE_TYPES.items():
        for pattern in config["patterns"]:
            if re.search(pattern, error_lower):
                return failure_type
    
    return "UNKNOWN"


def parse_log_file(log_path: Path) -> List[Dict]:
    """解析单个日志文件，提取错误信息"""
    errors = []
    
    if not log_path.exists():
        return errors
    
    with log_path.open(encoding="utf-8") as f:
        content = f.read()
    
    # 按行解析，查找错误标记
    for line_num, line in enumerate(content.split("\n"), 1):
        # 匹配 [FAIL] 或 ERROR 标记
        if "[FAIL]" in line or "ERROR" in line.upper():
            error_type = classify_error(line)
            errors.append({
                "line": line_num,
                "text": line.strip(),
                "type": error_type,
            })
    
    return errors


def analyze_benchmark_report(report_dir: Path) -> Dict:
    """分析单个 benchmark 报告目录"""
    result = {
        "benchmark": report_dir.name,
        "errors": [],
        "error_counts": Counter(),
        "has_run_log": False,
        "has_verifier_logs": False,
    }
    
    # 检查运行日志
    run_log = report_dir / "run_output.log"
    if run_log.exists():
        result["has_run_log"] = True
        errors = parse_log_file(run_log)
        result["errors"].extend(errors)
    
    # 检查 verifier 日志
    for verifier_log in report_dir.glob("verify_*.log"):
        result["has_verifier_logs"] = True
        errors = parse_log_file(verifier_log)
        result["errors"].extend(errors)
    
    # 统计错误类型
    for error in result["errors"]:
        result["error_counts"][error["type"]] += 1
    
    return result


def generate_failure_report(multi_report_dir: Path, output_path: Path) -> None:
    """生成失败分类汇总报告"""
    
    # 收集所有 provider 的数据
    all_failures: Dict[str, List[Dict]] = defaultdict(list)
    provider_stats: Dict[str, Counter] = defaultdict(Counter)
    
    for provider_dir in multi_report_dir.iterdir():
        if not provider_dir.is_dir():
            continue
        
        provider_name = provider_dir.name
        
        # 分析该 provider 下的所有 benchmark
        for benchmark_dir in provider_dir.iterdir():
            if not benchmark_dir.is_dir():
                continue
            
            analysis = analyze_benchmark_report(benchmark_dir)
            
            if analysis["errors"]:
                all_failures[provider_name].extend(analysis["errors"])
                for error_type, count in analysis["error_counts"].items():
                    provider_stats[provider_name][error_type] += count
    
    # 生成报告
    lines = [
        "# HWP 失败分类与日志汇总报告",
        "",
        f"**分析目录**: {multi_report_dir}",
        "",
        "## 失败类型统计",
        "",
    ]
    
    # 全局统计
    global_counts = Counter()
    for counts in provider_stats.values():
        global_counts.update(counts)
    
    if global_counts:
        lines.extend([
            "| 失败类型 | 次数 | 描述 |",
            "|----------|------|------|",
        ])
        
        for error_type, count in global_counts.most_common():
            description = FAILURE_TYPES.get(error_type, {}).get(
                "description", "未知错误")
            lines.append(f"| {error_type} | {count} | {description} |")
    else:
        lines.append("✓ 未发现失败")
    
    # 各 Provider 详细分析
    lines.extend([
        "",
        "## 各 Provider 失败详情",
        "",
    ])
    
    for provider_name in sorted(all_failures.keys()):
        errors = all_failures[provider_name]
        stats = provider_stats[provider_name]
        
        lines.extend([
            f"### {provider_name}",
            "",
        ])
        
        if stats:
            lines.extend([
                "**错误统计**:",
                "",
                "| 类型 | 次数 |",
                "|------|------|",
            ])
            for error_type, count in stats.most_common():
                lines.append(f"| {error_type} | {count} |")
            
            # 显示具体错误示例（最多3个）
            lines.extend([
                "",
                "**错误示例**:",
                "",
            ])
            
            shown_types = set()
            for error in errors[:10]:  # 最多显示10个
                if error["type"] not in shown_types:
                    lines.append(f"- `[{error['type']}]` {error['text'][:100]}...")
                    shown_types.add(error["type"])
                    if len(shown_types) >= 3:
                        break
        else:
            lines.append("✓ 该 provider 无失败记录")
        
        lines.append("")
    
    # 建议
    lines.extend([
        "",
        "## 诊断建议",
        "",
    ])
    
    if global_counts.get("TRANSPORT_ERROR", 0) > 0:
        lines.append("- **TRANSPORT_ERROR**: 检查网络连接和 provider 服务端状态")
    
    if global_counts.get("TIMEOUT", 0) > 0:
        lines.append("- **TIMEOUT**: 考虑增加超时时间或优化请求")
    
    if global_counts.get("PROVIDER_BLOCK", 0) > 0:
        lines.append("- **PROVIDER_BLOCK**: 检查输入内容是否触发安全策略，考虑调整 prompt")
    
    if global_counts.get("MISSING_REQUIRED_FIELDS", 0) > 0:
        lines.append("- **MISSING_REQUIRED_FIELDS**: 检查 spec 版本和 runner 实现是否一致")
    
    if global_counts.get("PROTOCOL_REGRESSION", 0) > 0:
        lines.append("- **PROTOCOL_REGRESSION**: 对比历史版本，检查最近的协议变更")
    
    lines.extend([
        "",
        "---",
        "",
        "*Generated by HWP Failure Classification System*",
    ])
    
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Failure report generated: {output_path}")


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python3 runs/classify_failures.py <multi_report_dir> <output.md>", file=sys.stderr)
        return 1
    
    multi_report_dir = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    
    if not multi_report_dir.exists():
        print(f"Error: Directory not found: {multi_report_dir}", file=sys.stderr)
        return 1
    
    generate_failure_report(multi_report_dir, output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
