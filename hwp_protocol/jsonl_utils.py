#!/usr/bin/env python3
import json
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                records.append(data)
    return records


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
