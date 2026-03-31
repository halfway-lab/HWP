#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


SUMMARY_PATTERN = re.compile(
    r"^\s*\[summary\]\s+(?:session_id=(?P<session>[^ ]+)\s+)?rounds_completed=(?P<rounds>\d+)\s+"
    r"round_avg_sec=(?P<avg>[0-9.]+)\s+"
    r"round_max_sec=(?P<max>[0-9.]+)\s+"
    r"chain_sec=(?P<chain>[0-9.]+)\s*$"
)


def parse_summaries(run_log: Path) -> list[dict[str, str]]:
    summaries: list[dict[str, str]] = []
    current_session = ""

    for raw_line in run_log.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        if line.startswith("开始链: "):
            current_session = line.split("开始链: ", 1)[1].split("，", 1)[0].strip()
            continue

        match = SUMMARY_PATTERN.match(line)
        if not match:
            continue

        item = match.groupdict()
        item["session_id"] = item.pop("session") or current_session or "(unknown)"
        summaries.append(item)

    return summaries


def render_markdown(summaries: list[dict[str, str]], limit: int) -> str:
    selected = summaries[-limit:] if limit > 0 else summaries

    lines = [
        "# Timing Summary",
        "",
        f"- Chains summarized: {len(selected)}",
        "",
        "| session_id | rounds_completed | round_avg_sec | round_max_sec | chain_sec |",
        "| --- | --- | --- | --- | --- |",
    ]

    for item in selected:
        lines.append(
            "| {session_id} | {rounds} | {avg} | {max} | {chain} |".format(
                session_id=item["session_id"],
                rounds=item["rounds"],
                avg=item["avg"],
                max=item["max"],
                chain=item["chain"],
            )
        )

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) not in (3, 4):
        print("Usage: python3 runs/report_timing.py <run.log> <summary.md> [limit]", file=sys.stderr)
        return 1

    run_log = Path(sys.argv[1])
    summary_path = Path(sys.argv[2])
    limit = int(sys.argv[3]) if len(sys.argv) == 4 else 10

    if not run_log.exists():
        print(f"run log not found: {run_log}", file=sys.stderr)
        return 1

    summaries = parse_summaries(run_log)
    summary_path.write_text(render_markdown(summaries, limit), encoding="utf-8")
    print(summary_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
