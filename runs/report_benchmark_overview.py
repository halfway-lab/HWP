#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from runs.report_timing import parse_summaries


def load_rows(results_path: Path) -> list[dict[str, str]]:
    with results_path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def load_context(context_path: Path) -> dict[str, str]:
    context: dict[str, str] = {}
    if not context_path.exists():
        return context

    for raw_line in context_path.read_text(encoding="utf-8").splitlines():
        if "=" not in raw_line:
            continue
        key, value = raw_line.split("=", 1)
        context[key.strip()] = value.strip()
    return context


def load_session_ids(session_file: Path) -> list[str]:
    if not session_file.exists():
        return []
    return [line.strip() for line in session_file.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_timing_index(run_log: Path) -> dict[str, dict[str, str]]:
    if not run_log.exists():
        return {}
    return {item["session_id"]: item for item in parse_summaries(run_log)}


def summarize_timing(session_ids: list[str], timing_index: dict[str, dict[str, str]]) -> dict[str, str]:
    matched = [timing_index[session_id] for session_id in session_ids if session_id in timing_index]
    if not matched:
        return {
            "chains": "0",
            "rounds": "0",
            "round_avg_sec": "",
            "round_max_sec": "",
            "chain_avg_sec": "",
            "chain_max_sec": "",
        }

    round_avgs = [float(item["avg"]) for item in matched]
    round_maxes = [float(item["max"]) for item in matched]
    chain_secs = [float(item["chain"]) for item in matched]
    rounds = [int(item["rounds"]) for item in matched]
    return {
        "chains": str(len(matched)),
        "rounds": str(sum(rounds)),
        "round_avg_sec": f"{sum(round_avgs) / len(round_avgs):.2f}",
        "round_max_sec": f"{max(round_maxes):.2f}",
        "chain_avg_sec": f"{sum(chain_secs) / len(chain_secs):.2f}",
        "chain_max_sec": f"{max(chain_secs):.2f}",
    }


def summarize_overall(rows: list[dict[str, str]], per_benchmark: list[dict[str, str]]) -> list[str]:
    total = len(rows)
    run_pass = sum(1 for row in per_benchmark if row.get("run_status") == "pass")
    full_pass = sum(
        1 for row in per_benchmark if row.get("run_status") == "pass" and row.get("verifier_status") == "pass"
    )
    chains_found = sum(int(row.get("timing_chains", "0") or 0) for row in per_benchmark)
    rounds_completed = sum(int(row.get("timing_rounds", "0") or 0) for row in per_benchmark)

    return [
        f"- Benchmarks run: {total}",
        f"- Run success: {run_pass}/{total}" if total else "- Run success: 0/0",
        f"- Full protocol pass: {full_pass}/{total}" if total else "- Full protocol pass: 0/0",
        f"- Chains with timing found: {chains_found}",
        f"- Total completed rounds observed: {rounds_completed}",
        f"- Total wall duration (sec): {sum(int(row.get('duration_sec', '0') or 0) for row in rows)}",
    ]


def build_overview_rows(rows: list[dict[str, str]], timing_index: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    overview_rows: list[dict[str, str]] = []
    for row in rows:
        report_dir = Path(row["report_dir"])
        sessions = load_session_ids(report_dir / "session_ids.txt")
        timing = summarize_timing(sessions, timing_index)
        verifier_status = (
            "pass"
            if row.get("structured") == "pass"
            and row.get("blind_spot") == "pass"
            and row.get("continuity") == "pass"
            and row.get("semantic_groups") == "pass"
            else "fail"
        )
        overview_rows.append(
            {
                "benchmark": row["benchmark"],
                "run_status": row.get("run_status", "unknown"),
                "verifier_status": verifier_status,
                "duration_sec": row.get("duration_sec", "0"),
                "log_count": row.get("log_count", "0"),
                "timing_chains": timing["chains"],
                "timing_rounds": timing["rounds"],
                "round_avg_sec": timing["round_avg_sec"],
                "round_max_sec": timing["round_max_sec"],
                "chain_avg_sec": timing["chain_avg_sec"],
                "chain_max_sec": timing["chain_max_sec"],
                "failure_reason": row.get("failure_reason", ""),
                "report_dir": row["report_dir"],
            }
        )
    return overview_rows


def render_markdown(
    rows: list[dict[str, str]],
    context: dict[str, str],
    overview_rows: list[dict[str, str]],
) -> str:
    provider_type = context.get("provider_type", rows[0].get("provider_type", "unknown") if rows else "unknown")
    provider_name = context.get("provider_name", rows[0].get("provider_name", "unknown") if rows else "unknown")

    lines = [
        "# Benchmark Overview",
        "",
        f"- Provider: {provider_type}/{provider_name}",
    ]
    report_dir = context.get("report_dir")
    if report_dir:
        lines.append(f"- Report dir: {report_dir}")
    benchmark_file = context.get("benchmark_file")
    if benchmark_file:
        lines.append(f"- Benchmark file: {benchmark_file}")
    started_at = context.get("started_at")
    if started_at:
        lines.append(f"- Started at: {started_at}")

    lines.extend(["", "## Overall", ""])
    lines.extend(summarize_overall(rows, overview_rows))
    lines.extend(
        [
            "",
            "## Per Benchmark",
            "",
            "| benchmark | run | verifier | duration_sec | logs | timing_chains | timing_rounds | round_avg_sec | round_max_sec | chain_avg_sec | chain_max_sec | failure_reason | report_dir |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )

    for row in overview_rows:
        lines.append(
            "| {benchmark} | {run_status} | {verifier_status} | {duration_sec} | {log_count} | {timing_chains} | {timing_rounds} | {round_avg_sec} | {round_max_sec} | {chain_avg_sec} | {chain_max_sec} | {failure_reason} | {report_dir} |".format(
                **row
            )
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- `duration_sec` is the benchmark wall-clock runtime measured by `run_benchmarks.sh`.",
            "- `timing_*` fields are derived from chain summaries written by `runs/run_sequential.sh` to `logs/run.log`.",
            "- Empty timing fields usually mean the benchmark did not produce a matching chain summary.",
            "",
        ]
    )
    return "\n".join(lines)


def write_overview_tsv(overview_rows: list[dict[str, str]], output_path: Path) -> None:
    fieldnames = [
        "benchmark",
        "run_status",
        "verifier_status",
        "duration_sec",
        "log_count",
        "timing_chains",
        "timing_rounds",
        "round_avg_sec",
        "round_max_sec",
        "chain_avg_sec",
        "chain_max_sec",
        "failure_reason",
        "report_dir",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(overview_rows)


def main() -> int:
    if len(sys.argv) not in (5, 6):
        print(
            "Usage: python3 runs/report_benchmark_overview.py <results.tsv> <context.txt> <run.log> <overview.md> [overview.tsv]",
            file=sys.stderr,
        )
        return 1

    results_path = Path(sys.argv[1])
    context_path = Path(sys.argv[2])
    run_log_path = Path(sys.argv[3])
    overview_path = Path(sys.argv[4])

    rows = load_rows(results_path)
    context = load_context(context_path)
    timing_index = build_timing_index(run_log_path)
    overview_rows = build_overview_rows(rows, timing_index)
    overview_path.write_text(render_markdown(rows, context, overview_rows), encoding="utf-8")
    if len(sys.argv) == 6:
        write_overview_tsv(overview_rows, Path(sys.argv[5]))
    print(overview_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
