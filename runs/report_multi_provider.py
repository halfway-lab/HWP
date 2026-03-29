#!/usr/bin/env python3
"""
HWP 多 Provider 对比报告生成器 - 第3步

用途：读取多个 provider 的 benchmark 结果，生成对比报告
"""

import csv
import sys
from pathlib import Path
from collections import defaultdict


def load_provider_results(multi_report_dir: Path) -> dict[str, list[dict]]:
    """加载每个 provider 的 results.tsv"""
    provider_data = {}
    
    for provider_dir in multi_report_dir.iterdir():
        if not provider_dir.is_dir():
            continue
        
        provider_name = provider_dir.name
        results_file = provider_dir / "results.tsv"
        
        if not results_file.exists():
            continue
        
        with results_file.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            provider_data[provider_name] = list(reader)
    
    return provider_data


def calculate_provider_score(rows: list[dict]) -> dict:
    """计算 provider 的综合得分"""
    if not rows:
        return {"score": 0, "total": 0}
    
    total = len(rows)
    passed = sum(1 for r in rows if r.get("run_status") == "pass")
    structured_pass = sum(1 for r in rows if r.get("structured") == "pass")
    blind_pass = sum(1 for r in rows if r.get("blind_spot") == "pass")
    continuity_pass = sum(1 for r in rows if r.get("continuity") == "pass")
    semantic_pass = sum(1 for r in rows if r.get("semantic_groups") == "pass")
    
    # 综合得分：运行成功 + 各项验证通过
    score = (
        passed * 2 +  # 运行成功权重最高
        structured_pass +
        blind_pass +
        continuity_pass +
        semantic_pass
    )
    max_score = total * 6  # 每项最高6分
    
    return {
        "score": score,
        "max_score": max_score,
        "percentage": (score / max_score * 100) if max_score > 0 else 0,
        "run_pass": passed,
        "structured_pass": structured_pass,
        "blind_pass": blind_pass,
        "continuity_pass": continuity_pass,
        "semantic_pass": semantic_pass,
        "total": total,
    }


def generate_comparison_table(provider_data: dict[str, list[dict]]) -> list[str]:
    """生成 provider 对比表格"""
    lines = [
        "## Provider 综合对比",
        "",
        "| Provider | Score | Run | Structured | Blind Spot | Continuity | Semantic |",
        "|----------|-------|-----|------------|------------|------------|----------|",
    ]
    
    # 按得分排序
    scores = []
    for provider, rows in provider_data.items():
        score_data = calculate_provider_score(rows)
        scores.append((provider, score_data))
    
    scores.sort(key=lambda x: x[1]["percentage"], reverse=True)
    
    for provider, score_data in scores:
        lines.append(
            f"| {provider} | "
            f"{score_data['percentage']:.1f}% | "
            f"{score_data['run_pass']}/{score_data['total']} | "
            f"{score_data['structured_pass']}/{score_data['total']} | "
            f"{score_data['blind_pass']}/{score_data['total']} | "
            f"{score_data['continuity_pass']}/{score_data['total']} | "
            f"{score_data['semantic_pass']}/{score_data['total']} |"
        )
    
    return lines


def generate_benchmark_breakdown(provider_data: dict[str, list[dict]]) -> list[str]:
    """生成每个 benchmark 的跨 provider 对比"""
    lines = [
        "",
        "## Benchmark 详细对比",
        "",
    ]
    
    # 收集所有 benchmark
    all_benchmarks = set()
    for rows in provider_data.values():
        for row in rows:
            all_benchmarks.add(row.get("benchmark", "unknown"))
    
    for benchmark in sorted(all_benchmarks):
        lines.extend([
            f"### {benchmark}",
            "",
            "| Provider | Run | Structured | Blind Spot | Continuity | Semantic |",
            "|----------|-----|------------|------------|------------|----------|",
        ])
        
        for provider, rows in provider_data.items():
            # 找到对应 benchmark 的行
            bench_row = None
            for row in rows:
                if row.get("benchmark") == benchmark:
                    bench_row = row
                    break
            
            if bench_row:
                lines.append(
                    f"| {provider} | "
                    f"{bench_row.get('run_status', 'N/A')} | "
                    f"{bench_row.get('structured', 'N/A')} | "
                    f"{bench_row.get('blind_spot', 'N/A')} | "
                    f"{bench_row.get('continuity', 'N/A')} | "
                    f"{bench_row.get('semantic_groups', 'N/A')} |"
                )
            else:
                lines.append(f"| {provider} | N/A | N/A | N/A | N/A | N/A |")
        
        lines.append("")
    
    return lines


def generate_recommendations(provider_data: dict[str, list[dict]]) -> list[str]:
    """生成推荐建议"""
    lines = [
        "",
        "## 推荐建议",
        "",
    ]
    
    # 计算每个 provider 的稳定性
    stability = {}
    for provider, rows in provider_data.items():
        if not rows:
            continue
        
        total = len(rows)
        all_pass = sum(1 for r in rows 
                      if r.get("run_status") == "pass" 
                      and r.get("structured") == "pass"
                      and r.get("blind_spot") == "pass"
                      and r.get("continuity") == "pass"
                      and r.get("semantic_groups") == "pass")
        stability[provider] = all_pass / total if total > 0 else 0
    
    if stability:
        best_provider = max(stability, key=stability.get)
        lines.extend([
            f"- **最稳定 Provider**: {best_provider} (全通过率: {stability[best_provider]:.1%})",
            "",
            "### 各 Provider 特点",
            "",
        ])
        
        for provider, rate in sorted(stability.items(), key=lambda x: x[1], reverse=True):
            if rate >= 0.8:
                lines.append(f"- **{provider}**: 高稳定性 ({rate:.1%})，推荐用于生产环境")
            elif rate >= 0.5:
                lines.append(f"- **{provider}**: 中等稳定性 ({rate:.1%})，需要进一步调优")
            else:
                lines.append(f"- **{provider}**: 较低稳定性 ({rate:.1%})，建议检查配置或模型适配")
    
    return lines


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python3 runs/report_multi_provider.py <multi_report_dir> <output.md>", file=sys.stderr)
        return 1
    
    multi_report_dir = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    
    if not multi_report_dir.exists():
        print(f"Error: Directory not found: {multi_report_dir}", file=sys.stderr)
        return 1
    
    # 加载数据
    provider_data = load_provider_results(multi_report_dir)
    
    if not provider_data:
        print("Warning: No provider data found", file=sys.stderr)
        output_path.write_text("# Multi-Provider Comparison\n\nNo data available.\n", encoding="utf-8")
        return 0
    
    # 生成报告
    lines = [
        "# HWP Multi-Provider Benchmark Comparison",
        "",
        f"**Total Providers**: {len(provider_data)}",
        "",
    ]
    
    lines.extend(generate_comparison_table(provider_data))
    lines.extend(generate_benchmark_breakdown(provider_data))
    lines.extend(generate_recommendations(provider_data))
    
    lines.extend([
        "",
        "---",
        "",
        "*Generated by HWP Benchmark System*",
    ])
    
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Comparison report generated: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
