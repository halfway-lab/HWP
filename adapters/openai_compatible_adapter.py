#!/usr/bin/env python3
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from adapter_common import (
    extract_json_object_text,
    fail,
    first_env,
    hwp_message,
    hwp_round,
    hwp_session_id,
    json_headers,
    optional_env,
    post_json,
    require_first_env,
    wrap_result,
)

PROVIDER_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "moonshot": "https://api.moonshot.cn/v1",
    "kimi": "https://api.moonshot.cn/v1",
    "siliconflow": "https://api.siliconflow.cn/v1",
    "groq": "https://api.groq.com/openai/v1",
    "together": "https://api.together.xyz/v1",
    "fireworks": "https://api.fireworks.ai/inference/v1",
    "perplexity": "https://api.perplexity.ai",
    "xai": "https://api.x.ai/v1",
}


SYSTEM_PROMPT = (
    "You are an execution adapter for HWP. "
    "Return exactly one JSON object and nothing else. "
    "Do not wrap the JSON in Markdown fences. "
    "Do not explain the answer."
)


def resolve_base_url(provider_name: str) -> str:
    explicit = first_env("HWP_LLM_BASE_URL", "OPENAI_BASE_URL", default="").rstrip("/")
    if explicit:
        return explicit

    normalized = (provider_name or "openai").lower()
    if normalized in PROVIDER_BASE_URLS:
        return PROVIDER_BASE_URLS[normalized]
    if normalized == "openai":
        return PROVIDER_BASE_URLS["openai"]

    raise RuntimeError(
        "missing required environment variable: HWP_LLM_BASE_URL (required when HWP_PROVIDER_NAME is custom or unknown)"
    )


def main() -> int:
    try:
        api_key = require_first_env("HWP_LLM_API_KEY", "OPENAI_API_KEY")
        model = require_first_env("HWP_LLM_MODEL", "OPENAI_MODEL")
        provider_name = first_env("HWP_PROVIDER_NAME", default="openai").lower()
        base_url = resolve_base_url(provider_name)
        temperature = float(first_env("HWP_LLM_TEMPERATURE", "HWP_OPENAI_TEMPERATURE", default="0.7"))
        timeout = int(first_env("HWP_LLM_TIMEOUT_SEC", "HWP_OPENAI_TIMEOUT_SEC", default="120"))

        payload = {
            "model": model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Session: {hwp_session_id()}\n"
                        f"Round: {hwp_round() or 'unknown'}\n\n"
                        f"{hwp_message()}"
                    ),
                },
            ],
        }

        response = post_json(
            f"{base_url}/chat/completions",
            payload,
            json_headers({"Authorization": f"Bearer {api_key}"}),
            timeout=timeout,
        )

        content = (
            response.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        inner_json_text = extract_json_object_text(content)
        wrap_result(inner_json_text)
        return 0
    except Exception as exc:
        fail(str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
