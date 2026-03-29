#!/usr/bin/env python3
import json
import os
import re
import sys
import urllib.error
import urllib.request
from typing import Any


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"missing required environment variable: {name}")
    return value


def optional_env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def first_env(*names: str, default: str = "") -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return default


def require_first_env(*names: str) -> str:
    value = first_env(*names)
    if value:
        return value
    raise RuntimeError(f"missing required environment variable: one of {', '.join(names)}")


def hwp_message() -> str:
    return require_env("HWP_AGENT_MESSAGE")


def hwp_session_id() -> str:
    return optional_env("HWP_AGENT_SESSION_ID", "hwp-session")


def hwp_round() -> str:
    return optional_env("HWP_AGENT_ROUND", "")


def json_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if extra:
        headers.update(extra)
    return headers


def post_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: int = 120) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"request failed: {exc.code} {exc.reason}: {body[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"request failed: {exc.reason}") from exc

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"provider returned non-JSON response: {raw[:500]}") from exc


def extract_json_object_text(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        raise RuntimeError("provider returned empty text")

    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
        stripped = stripped.strip()

    try:
        json.loads(stripped)
        return stripped
    except json.JSONDecodeError:
        pass

    start = stripped.find("{")
    if start == -1:
        raise RuntimeError(f"provider did not return a JSON object: {stripped[:500]}")

    depth = 0
    in_string = False
    escape = False
    for idx, char in enumerate(stripped[start:], start=start):
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                candidate = stripped[start : idx + 1]
                json.loads(candidate)
                return candidate

    raise RuntimeError(f"unable to recover JSON object from provider output: {stripped[:500]}")


def wrap_result(inner_json_text: str) -> None:
    result = {
        "result": {
            "payloads": [
                {
                    "text": inner_json_text,
                }
            ]
        }
    }
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))


def fail(message: str) -> None:
    print(f"FATAL: {message}", file=sys.stderr)
    raise SystemExit(1)
