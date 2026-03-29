#!/usr/bin/env python3
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from adapter_common import (
    extract_json_object_text,
    fail,
    hwp_message,
    hwp_round,
    hwp_session_id,
    json_headers,
    optional_env,
    post_json,
    require_env,
    wrap_result,
)


SYSTEM_PROMPT = (
    "You are an execution adapter for HWP. "
    "Return exactly one JSON object and nothing else. "
    "Do not wrap the JSON in Markdown fences. "
    "Do not explain the answer."
)


def main() -> int:
    try:
        model = require_env("OLLAMA_MODEL")
        base_url = optional_env("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        temperature = float(optional_env("HWP_OLLAMA_TEMPERATURE", "0.7"))
        timeout = int(optional_env("HWP_OLLAMA_TIMEOUT_SEC", "120"))

        payload = {
            "model": model,
            "stream": False,
            "format": "json",
            "system": SYSTEM_PROMPT,
            "prompt": (
                f"Session: {hwp_session_id()}\n"
                f"Round: {hwp_round() or 'unknown'}\n\n"
                f"{hwp_message()}"
            ),
            "options": {
                "temperature": temperature,
            },
        }

        response = post_json(
            f"{base_url}/api/generate",
            payload,
            json_headers(),
            timeout=timeout,
        )

        content = response.get("response", "")
        inner_json_text = extract_json_object_text(content)
        wrap_result(inner_json_text)
        return 0
    except Exception as exc:
        fail(str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
