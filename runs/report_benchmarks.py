#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path


def load_rows(results_path: Path) -> list[dict[str, str]]:
    with results_path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def status_counter(rows: list[dict[str, str]], key: str) -> Counter[str]:
    counter: Counter[str] = Counter()
    for row in rows:
        counter[row.get(key, "unknown") or "unknown"] += 1
    return counter


def summarize_results(rows: list[dict[str, str]]) -> list[str]:
    run_counts = status_counter(rows, "run_status")
    structured_counts = status_counter(rows, "structured")
    blind_counts = status_counter(rows, "blind_spot")
    continuity_counts = status_counter(rows, "continuity")
    semantic_counts = status_counter(rows, "semantic_groups")

    lines = [
        "# Benchmark Summary",
        "",
        f"- Benchmarks run: {len(rows)}",
        f"- Provider: {rows[0].get('provider_type', 'unknown')}/{rows[0].get('provider_name', 'unknown')}" if rows else "- Provider: unknown/unknown",
        f"- Run success: {run_counts.get('pass', 0)}",
        f"- Run failed: {run_counts.get('fail', 0)}",
        f"- Structured pass: {structured_counts.get('pass', 0)}",
        f"- Blind spot pass: {blind_counts.get('pass', 0)}",
        f"- Continuity pass: {continuity_counts.get('pass', 0)}",
        f"- Semantic groups pass: {semantic_counts.get('pass', 0)}",
        f"- Total duration (sec): {sum(int(row.get('duration_sec', '0') or 0) for row in rows)}",
        "",
        "| benchmark | run | duration_sec | logs | structured | blind_spot | continuity | semantic_groups | failure_reason | verifier_reason | report_dir |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    for row in rows:
        verifier_reason = (
            row.get("structured_reason")
            or row.get("blind_spot_reason")
            or row.get("continuity_reason")
            or row.get("semantic_groups_reason")
            or ""
        )
        lines.append(
            "| {benchmark} | {run_status} | {duration_sec} | {log_count} | {structured} | {blind_spot} | {continuity} | {semantic_groups} | {failure_reason} | {verifier_reason} | {report_dir} |".format(
                benchmark=row["benchmark"],
                run_status=row["run_status"],
                duration_sec=row.get("duration_sec", "0"),
                log_count=row["log_count"],
                structured=row.get("structured", "skipped"),
                blind_spot=row["blind_spot"],
                continuity=row["continuity"],
                semantic_groups=row["semantic_groups"],
                failure_reason=row.get("failure_reason", ""),
                verifier_reason=verifier_reason,
                report_dir=row["report_dir"],
            )
        )
    lines.append("")
    return lines


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python3 runs/report_benchmarks.py <results.tsv> <summary.md>", file=sys.stderr)
        return 1

    results_path = Path(sys.argv[1])
    summary_path = Path(sys.argv[2])
    rows = load_rows(results_path)
    summary_path.write_text("\n".join(summarize_results(rows)), encoding="utf-8")
    print(summary_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
