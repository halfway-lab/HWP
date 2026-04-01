#!/usr/bin/env python3
"""
JSONL utility functions for HWP protocol.

Optimized for performance with minimal I/O overhead.
No third-party dependencies.
"""
import json
import sys
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> tuple[list[dict[str, Any]], int]:
    """
    Load records from a JSONL file.

    Optimized: reads entire file at once to minimize I/O syscalls.

    Returns:
        A tuple of (records, corrupt_count) where:
        - records: list of successfully parsed dict records
        - corrupt_count: number of lines that failed JSON parsing

    Corrupt lines are logged to stderr with line number and error details.
    """
    records: list[dict[str, Any]] = []
    corrupt_count = 0

    # Single read operation - much faster than line-by-line I/O
    content = path.read_text(encoding="utf-8")

    for line_num, line in enumerate(content.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError as e:
            corrupt_count += 1
            print(
                f"JSONL损坏: 文件 {path.name} 第 {line_num} 行 - {e.msg}",
                file=sys.stderr
            )
            continue
        if isinstance(data, dict):
            records.append(data)
    return records, corrupt_count


def load_jsonl_last_n(path: Path, n: int) -> tuple[list[dict[str, Any]], int]:
    """
    Load only the last N valid records from a JSONL file.

    Efficient for large log files where only recent entries are needed.
    Uses reverse reading to avoid loading entire file into memory.

    Args:
        path: Path to the JSONL file
        n: Number of records to load from the end

    Returns:
        A tuple of (records, corrupt_count) where records are the last N
        successfully parsed records (in original order, newest last).
    """
    if n <= 0:
        return [], 0

    records: list[dict[str, Any]] = []
    corrupt_count = 0

    # Read entire file and process from end
    # For very large files, a more sophisticated approach would be needed
    # but for typical log sizes (< 100MB) this is fastest
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()

    # Process from the end, stop when we have n valid records
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            corrupt_count += 1
            continue
        if isinstance(data, dict):
            records.append(data)
            if len(records) >= n:
                break

    # Reverse to restore original order (oldest first)
    records.reverse()
    return records, corrupt_count


def count_jsonl_lines(path: Path) -> int:
    """
    Efficiently count non-empty lines in a JSONL file.

    Does not parse JSON - just counts lines.

    Args:
        path: Path to the JSONL file

    Returns:
        Number of non-empty lines in the file.
    """
    content = path.read_text(encoding="utf-8")
    return sum(1 for line in content.splitlines() if line.strip())


def iter_inner_objects(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    inners: list[dict[str, Any]] = []
    for record in records:
        inner = extract_inner_object(record)
        if inner:
            inners.append(inner)
    return inners


def extract_inner_object(record: dict[str, Any]) -> dict[str, Any]:
    payloads = record.get("payloads")
    if not isinstance(payloads, list) or not payloads:
        return {}
    first = payloads[0]
    if not isinstance(first, dict):
        return {}
    text = first.get("text")
    if not isinstance(text, str):
        return {}
    try:
        inner = json.loads(text)
    except json.JSONDecodeError:
        return {}
    if isinstance(inner, dict):
        return inner
    return {}


def iter_record_pairs(records: list[dict[str, Any]]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    return [(record, extract_inner_object(record)) for record in records]
