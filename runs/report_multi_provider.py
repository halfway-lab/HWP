#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Any


def load_tsv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def load_context(path: Path) -> dict[str, str]:
    context: dict[str, str] = {}
    if not path.exists():
        return context
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in raw_line:
            continue
        key, value = raw_line.split("=", 1)
        context[key.strip()] = value.strip()
    return context


def load_provider_statuses(multi_report_dir: Path) -> list[dict[str, str]]:
    return load_tsv(multi_report_dir / "provider_status.tsv")


def load_provider_results(multi_report_dir: Path) -> dict[str, dict[str, Any]]:
    provider_data: dict[str, dict[str, Any]] = {}

    for provider_dir in multi_report_dir.iterdir():
        if not provider_dir.is_dir():
            continue

        provider_name = provider_dir.name
        overview_rows = load_tsv(provider_dir / "overview.tsv")
        results_rows = load_tsv(provider_dir / "results.tsv")
        if not overview_rows and not results_rows:
            continue

        provider_data[provider_name] = {
            "provider": provider_name,
            "rows": overview_rows or results_rows,
            "context": load_context(provider_dir / "context.txt"),
            "has_overview": bool(overview_rows),
        }

    return provider_data


def calculate_provider_score(rows: list[dict[str, str]]) -> dict[str, Any]:
    if not rows:
        return {"score": 0, "total": 0}

    total = len(rows)
    passed = sum(1 for r in rows if r.get("run_status") == "pass")
    verifier_pass = sum(
        1
        for r in rows
        if r.get("verifier_status") == "pass"
        or (
            r.get("structured") == "pass"
            and r.get("blind_spot") == "pass"
            and r.get("continuity") == "pass"
            and r.get("semantic_groups") == "pass"
        )
    )
    timing_rows = [r for r in rows if r.get("chain_avg_sec")]
    avg_chain_sec = (
        sum(float(r.get("chain_avg_sec", "0") or 0) for r in timing_rows) / len(timing_rows) if timing_rows else 0.0
    )
    max_chain_sec = max((float(r.get("chain_max_sec", "0") or 0) for r in timing_rows), default=0.0)

    score = (
        passed * 2 +
        verifier_pass * 3
    )
    max_score = total * 5

    return {
        "score": score,
        "max_score": max_score,
        "percentage": (score / max_score * 100) if max_score > 0 else 0,
        "run_pass": passed,
        "verifier_pass": verifier_pass,
        "timing_coverage": len(timing_rows),
        "avg_chain_sec": avg_chain_sec,
        "max_chain_sec": max_chain_sec,
        "total": total,
    }


def generate_comparison_table(provider_data: dict[str, dict[str, Any]]) -> list[str]:
    lines = [
        "## Provider Overview",
        "",
        "| Provider | Source | Score | Run | Full Pass | Timing | Avg Chain Sec | Max Chain Sec |",
        "|----------|--------|-------|-----|-----------|--------|---------------|---------------|",
    ]

    scores = []
    for provider, payload in provider_data.items():
        score_data = calculate_provider_score(payload["rows"])
        scores.append((provider, payload, score_data))

    scores.sort(key=lambda x: x[2]["percentage"], reverse=True)

    for provider, payload, score_data in scores:
        source = "overview.tsv" if payload.get("has_overview") else "results.tsv"
        lines.append(
            f"| {provider} | "
            f"{source} | "
            f"{score_data['percentage']:.1f}% | "
            f"{score_data['run_pass']}/{score_data['total']} | "
            f"{score_data['verifier_pass']}/{score_data['total']} | "
            f"{score_data['timing_coverage']}/{score_data['total']} | "
            f"{score_data['avg_chain_sec']:.2f} | "
            f"{score_data['max_chain_sec']:.2f} |"
        )

    return lines


def generate_provider_status_table(status_rows: list[dict[str, str]]) -> list[str]:
    if not status_rows:
        return []

    lines = [
        "## Provider Execution Status",
        "",
        "| Provider | Status | Reason | Env Path | Report Dir |",
        "|----------|--------|--------|----------|------------|",
    ]
    for row in status_rows:
        lines.append(
            f"| {row.get('provider', '')} | {row.get('status', '')} | {row.get('reason', '')} | {row.get('env_path', '')} | {row.get('report_dir', '')} |"
        )
    lines.append("")
    return lines


def generate_benchmark_breakdown(provider_data: dict[str, dict[str, Any]]) -> list[str]:
    lines = [
        "",
        "## Benchmark Breakdown",
        "",
    ]

    all_benchmarks = set()
    for payload in provider_data.values():
        for row in payload["rows"]:
            all_benchmarks.add(row.get("benchmark", "unknown"))

    for benchmark in sorted(all_benchmarks):
        lines.extend([
            f"### {benchmark}",
            "",
            "| Provider | Run | Verifier | Duration Sec | Avg Chain Sec | Max Chain Sec | Failure |",
            "|----------|-----|----------|--------------|---------------|---------------|---------|",
        ])

        for provider, payload in provider_data.items():
            bench_row = None
            for row in payload["rows"]:
                if row.get("benchmark") == benchmark:
                    bench_row = row
                    break

            if bench_row:
                verifier = bench_row.get("verifier_status")
                if not verifier:
                    verifier = (
                        "pass"
                        if bench_row.get("structured") == "pass"
                        and bench_row.get("blind_spot") == "pass"
                        and bench_row.get("continuity") == "pass"
                        and bench_row.get("semantic_groups") == "pass"
                        else "fail"
                    )
                lines.append(
                    f"| {provider} | "
                    f"{bench_row.get('run_status', 'N/A')} | "
                    f"{verifier} | "
                    f"{bench_row.get('duration_sec', '')} | "
                    f"{bench_row.get('chain_avg_sec', '')} | "
                    f"{bench_row.get('chain_max_sec', '')} | "
                    f"{bench_row.get('failure_reason', '')} |"
                )
            else:
                lines.append(f"| {provider} | N/A | N/A |  |  |  |  |")

        lines.append("")

    return lines


def generate_recommendations(provider_data: dict[str, dict[str, Any]]) -> list[str]:
    lines = [
        "",
        "## Recommendations",
        "",
    ]

    stability: dict[str, tuple[float, float]] = {}
    for provider, payload in provider_data.items():
        rows = payload["rows"]
        if not rows:
            continue

        total = len(rows)
        all_pass = sum(
            1
            for r in rows
            if r.get("run_status") == "pass"
            and (
                r.get("verifier_status") == "pass"
                or (
                    r.get("structured") == "pass"
                    and r.get("blind_spot") == "pass"
                    and r.get("continuity") == "pass"
                    and r.get("semantic_groups") == "pass"
                )
            )
        )
        avg_chain = sum(float(r.get("chain_avg_sec", "0") or 0) for r in rows if r.get("chain_avg_sec"))
        avg_chain = avg_chain / max(sum(1 for r in rows if r.get("chain_avg_sec")), 1)
        stability[provider] = (all_pass / total if total > 0 else 0, avg_chain)

    if stability:
        best_provider = max(stability, key=lambda key: (stability[key][0], -stability[key][1] if stability[key][1] else 0))
        lines.extend([
            f"- Best default provider: **{best_provider}** (full-pass rate: {stability[best_provider][0]:.1%})",
            "",
            "### Provider Notes",
            "",
        ])

        for provider, (rate, avg_chain) in sorted(stability.items(), key=lambda x: (x[1][0], -x[1][1] if x[1][1] else 0), reverse=True):
            if rate >= 0.8:
                lines.append(f"- **{provider}**: high stability ({rate:.1%}) with avg chain {avg_chain:.2f}s.")
            elif rate >= 0.5:
                lines.append(f"- **{provider}**: medium stability ({rate:.1%}); keep it under observation.")
            else:
                lines.append(f"- **{provider}**: low stability ({rate:.1%}); check config, model fit, or verifier regressions.")

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
    status_rows = load_provider_statuses(multi_report_dir)
    
    if not provider_data and not status_rows:
        print("Warning: No provider data found", file=sys.stderr)
        output_path.write_text("# Multi-Provider Comparison\n\nNo data available.\n", encoding="utf-8")
        return 0
    
    # 生成报告
    lines = [
        "# HWP Multi-Provider Benchmark Overview",
        "",
        f"**Total Providers With Results**: {len(provider_data)}",
        "",
    ]

    lines.extend(generate_provider_status_table(status_rows))
    if provider_data:
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
