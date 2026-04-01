#!/usr/bin/env python3
"""
HWP 回归报告生成器 - 第5步（最后一步）

用途：对比当前 benchmark 结果与历史基线，生成回归分析报告

核心问题：
1. 哪些输入通过了？
2. 哪些输入失败了？
3. 失败类型是什么？
4. 哪些指标比上次更差？
5. 哪个 provider 最稳定？
6. 哪个 provider 的 unfinished/path 质量最好？
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re


REPORT_DIR_RE = re.compile(r"^(?P<base>\d{8}T\d{6})(?:__.+)?$")


def load_results_tsv(tsv_path: Path) -> List[Dict[str, str]]:
    """加载 benchmark results.tsv"""
    if not tsv_path.exists():
        return []
    
    with tsv_path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def load_context(context_path: Path) -> Dict[str, str]:
    """加载 benchmark run context.txt"""
    data: Dict[str, str] = {}
    if not context_path.exists():
        return data

    for raw_line in context_path.read_text(encoding="utf-8").splitlines():
        if "=" not in raw_line:
            continue
        key, value = raw_line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def find_baseline_report(report_root: Path, current_report: Path) -> Optional[Path]:
    """找到最近的历史基线报告"""
    current_match = REPORT_DIR_RE.match(current_report.name)
    if not current_match:
        return None
    current_time = datetime.strptime(current_match.group("base"), "%Y%m%dT%H%M%S")
    
    baseline_candidates = []
    
    for report_dir in report_root.iterdir():
        if not report_dir.is_dir():
            continue
        if report_dir.name == current_report.name:
            continue
        if report_dir.name.startswith("multi_"):
            continue
        
        # 尝试解析时间戳
        try:
            match = REPORT_DIR_RE.match(report_dir.name)
            if not match:
                continue
            report_time = datetime.strptime(match.group("base"), "%Y%m%dT%H%M%S")
            if report_time < current_time:
                baseline_candidates.append((report_time, report_dir))
        except ValueError:
            continue
    
    if baseline_candidates:
        # 返回最近的历史报告
        baseline_candidates.sort(key=lambda x: x[0], reverse=True)
        return baseline_candidates[0][1]
    
    return None


def calculate_quality_score(row: Dict[str, str]) -> float:
    """计算单条 benchmark 的质量得分"""
    score = 0.0
    
    # 基础运行成功
    if row.get("run_status") == "pass":
        score += 2.0
    
    # 各项验证通过
    for key in ["structured", "blind_spot", "continuity", "semantic_groups"]:
        if row.get(key) == "pass":
            score += 1.0
    
    return score


def compare_with_baseline(
    current_results: List[Dict[str, str]],
    baseline_results: List[Dict[str, str]]
) -> Dict:
    """对比当前结果与基线"""
    
    # 建立索引
    baseline_by_benchmark = {r["benchmark"]: r for r in baseline_results}
    current_by_benchmark = {r["benchmark"]: r for r in current_results}
    
    comparison = {
        "new_pass": [],
        "new_fail": [],
        "improved": [],
        "regressed": [],
        "stable": [],
        "missing": [],
        "added": [],
    }
    
    # 检查每个当前 benchmark
    for bench_name, current in current_by_benchmark.items():
        if bench_name not in baseline_by_benchmark:
            comparison["added"].append({
                "benchmark": bench_name,
                "current": current,
            })
            continue
        
        baseline = baseline_by_benchmark[bench_name]
        
        current_score = calculate_quality_score(current)
        baseline_score = calculate_quality_score(baseline)
        
        # 判断是否通过
        current_pass = current.get("run_status") == "pass"
        baseline_pass = baseline.get("run_status") == "pass"
        
        if not baseline_pass and current_pass:
            comparison["new_pass"].append({
                "benchmark": bench_name,
                "baseline": baseline,
                "current": current,
            })
        elif baseline_pass and not current_pass:
            comparison["new_fail"].append({
                "benchmark": bench_name,
                "baseline": baseline,
                "current": current,
            })
        elif current_score > baseline_score:
            comparison["improved"].append({
                "benchmark": bench_name,
                "baseline": baseline,
                "current": current,
                "score_change": current_score - baseline_score,
            })
        elif current_score < baseline_score:
            comparison["regressed"].append({
                "benchmark": bench_name,
                "baseline": baseline,
                "current": current,
                "score_change": baseline_score - current_score,
            })
        else:
            comparison["stable"].append({
                "benchmark": bench_name,
                "baseline": baseline,
                "current": current,
            })
    
    # 检查消失的 benchmark
    for bench_name, baseline in baseline_by_benchmark.items():
        if bench_name not in current_by_benchmark:
            comparison["missing"].append({
                "benchmark": bench_name,
                "baseline": baseline,
            })
    
    return comparison


def calculate_provider_stability(results: List[Dict[str, str]]) -> Dict:
    """计算 provider 稳定性指标"""
    if not results:
        return {}
    
    total = len(results)
    passed = sum(1 for r in results if r.get("run_status") == "pass")
    
    # 全通过（所有验证都通过）
    all_passed = sum(1 for r in results if (
        r.get("run_status") == "pass" and
        r.get("structured") == "pass" and
        r.get("blind_spot") == "pass" and
        r.get("continuity") == "pass" and
        r.get("semantic_groups") == "pass"
    ))
    
    return {
        "total": total,
        "run_pass_rate": passed / total if total > 0 else 0,
        "full_pass_rate": all_passed / total if total > 0 else 0,
        "avg_quality_score": sum(calculate_quality_score(r) for r in results) / total if total > 0 else 0,
    }


def generate_regression_report(
    current_report_dir: Path,
    output_path: Path,
    baseline_report_dir: Optional[Path] = None
) -> None:
    """生成回归分析报告"""
    
    # 加载当前结果
    current_results = load_results_tsv(current_report_dir / "results.tsv")
    current_context = load_context(current_report_dir / "context.txt")
    
    if not current_results:
        output_path.write_text("# Regression Report\n\nNo current results found.\n", encoding="utf-8")
        return
    
    # 如果没有指定基线，自动查找
    if baseline_report_dir is None:
        report_root = current_report_dir.parent
        baseline_report_dir = find_baseline_report(report_root, current_report_dir)
    
    # 加载基线结果
    baseline_results = []
    baseline_context: Dict[str, str] = {}
    if baseline_report_dir:
        baseline_results = load_results_tsv(baseline_report_dir / "results.tsv")
        baseline_context = load_context(baseline_report_dir / "context.txt")
    
    lines = [
        "# HWP 回归分析报告",
        "",
        f"**当前报告**: {current_report_dir.name}",
    ]
    
    if baseline_report_dir:
        lines.append(f"**基线报告**: {baseline_report_dir.name}")
    else:
        lines.append("**基线报告**: 无（首次运行）")
    if current_context:
        lines.append(f"**当前 Provider**: {current_context.get('provider_type', 'unknown')}/{current_context.get('provider_name', 'unknown')}")
    if baseline_context:
        lines.append(f"**基线 Provider**: {baseline_context.get('provider_type', 'unknown')}/{baseline_context.get('provider_name', 'unknown')}")

    lines.append("")
    
    # 1. 当前运行概况
    lines.extend([
        "## 1. 当前运行概况",
        "",
        f"**总 Benchmark 数**: {len(current_results)}",
        "",
        "| 指标 | 通过数 | 失败数 | 通过率 |",
        "|------|--------|--------|--------|",
    ])
    
    run_pass = sum(1 for r in current_results if r.get("run_status") == "pass")
    run_fail = len(current_results) - run_pass
    run_rate = run_pass / len(current_results) * 100 if current_results else 0
    lines.append(f"| 运行 | {run_pass} | {run_fail} | {run_rate:.1f}% |")
    
    for key, name in [
        ("structured", "结构化验证"),
        ("blind_spot", "Blind Spot"),
        ("continuity", "连续性"),
        ("semantic_groups", "语义组"),
    ]:
        passed = sum(1 for r in current_results if r.get(key) == "pass")
        failed = len(current_results) - passed
        rate = passed / len(current_results) * 100 if current_results else 0
        lines.append(f"| {name} | {passed} | {failed} | {rate:.1f}% |")
    
    lines.append("")
    
    # 2. 与基线对比（如果有）
    if baseline_results:
        comparison = compare_with_baseline(current_results, baseline_results)
        
        lines.extend([
            "## 2. 与基线对比",
            "",
            "| 变化类型 | 数量 |",
            "|----------|------|",
            f"| 🟢 新增通过 | {len(comparison['new_pass'])} |",
            f"| 🔴 新增失败 | {len(comparison['new_fail'])} |",
            f"| ⬆️  质量提升 | {len(comparison['improved'])} |",
            f"| ⬇️  质量下降 | {len(comparison['regressed'])} |",
            f"| ➖ 保持稳定 | {len(comparison['stable'])} |",
            f"| 🆕 新增输入 | {len(comparison['added'])} |",
            f"| ❌ 移除输入 | {len(comparison['missing'])} |",
            "",
        ])
        
        # 详细变化
        if comparison['new_fail']:
            lines.extend([
                "### 🔴 新增失败",
                "",
            ])
            for item in comparison['new_fail']:
                lines.append(f"- **{item['benchmark']}**: 上次通过，本次失败")
            lines.append("")
        
        if comparison['regressed']:
            lines.extend([
                "### ⬇️  质量下降",
                "",
            ])
            for item in comparison['regressed']:
                lines.append(f"- **{item['benchmark']}**: 得分下降 {item['score_change']:.1f}")
            lines.append("")
    
    # 3. Provider 稳定性排名
    lines.extend([
        "## 3. Provider 稳定性排名",
        "",
    ])
    
    provider_name = "{}/{}".format(
        current_context.get("provider_type", "unknown"),
        current_context.get("provider_name", "unknown"),
    )
    stability = calculate_provider_stability(current_results)
    
    if stability:
        lines.extend([
            f"**{provider_name}**:",
            "",
            f"- 运行通过率: {stability['run_pass_rate']:.1%}",
            f"- 全验证通过率: {stability['full_pass_rate']:.1%}",
            f"- 平均质量得分: {stability['avg_quality_score']:.2f} / 6.0",
            "",
        ])
    
    # 4. 质量最佳 Benchmark
    lines.extend([
        "## 4. 质量最佳 Benchmark",
        "",
    ])
    
    # 按质量得分排序
    scored_benchmarks = [
        (r["benchmark"], calculate_quality_score(r))
        for r in current_results
    ]
    scored_benchmarks.sort(key=lambda x: x[1], reverse=True)
    
    lines.extend([
        "| 排名 | Benchmark | 质量得分 |",
        "|------|-----------|----------|",
    ])
    
    for i, (bench, score) in enumerate(scored_benchmarks[:5], 1):
        lines.append(f"| {i} | {bench} | {score:.1f} |")
    
    lines.append("")
    
    # 5. 需要关注的 Benchmark
    failed_benchmarks = [
        r for r in current_results
        if r.get("run_status") != "pass" or calculate_quality_score(r) < 4.0
    ]
    
    if failed_benchmarks:
        lines.extend([
            "## 5. 需要关注的 Benchmark",
            "",
        ])
        
        for r in failed_benchmarks:
            bench = r["benchmark"]
            score = calculate_quality_score(r)
            status = r.get("run_status", "unknown")
            
            failed_checks = []
            for key, name in [
                ("structured", "结构化"),
                ("blind_spot", "BlindSpot"),
                ("continuity", "连续性"),
                ("semantic_groups", "语义组"),
            ]:
                if r.get(key) != "pass":
                    failed_checks.append(name)
            
            lines.append(f"- **{bench}**: 运行={status}, 得分={score:.1f}, 失败项={', '.join(failed_checks) or '无'}")
        
        lines.append("")
    
    # 6. 行动建议
    lines.extend([
        "## 6. 行动建议",
        "",
    ])
    
    if failed_benchmarks:
        lines.append("- **优先修复**: 关注上述「需要关注的 Benchmark」，特别是运行失败的")
    
    if baseline_results and comparison['regressed']:
        lines.append("- **质量回归**: 检查质量下降的 benchmark，确认是协议变更还是 provider 问题")
    
    if not failed_benchmarks:
        lines.append("- ✅ **状态良好**: 所有 benchmark 均通过，可以考虑作为新的基线")
    
    lines.append("- **持续监控**: 定期运行 benchmark，建立长期趋势数据")
    
    lines.extend([
        "",
        "---",
        "",
        "*Generated by HWP Regression Report System*",
    ])
    
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Regression report generated: {output_path}")


def main() -> int:
    if len(sys.argv) not in [3, 4]:
        print("Usage: python3 runs/report_regression.py <current_report_dir> <output.md> [baseline_report_dir]", file=sys.stderr)
        return 1
    
    current_report_dir = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    baseline_report_dir = Path(sys.argv[3]) if len(sys.argv) == 4 else None
    
    if not current_report_dir.exists():
        print(f"Error: Directory not found: {current_report_dir}", file=sys.stderr)
        return 1
    
    generate_regression_report(current_report_dir, output_path, baseline_report_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
