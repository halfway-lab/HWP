#!/usr/bin/env python3
"""OpenAI 兼容适配器

支持 OpenAI、DeepSeek、Moonshot、Groq、OpenRouter 等兼容 API 的 LLM 服务。
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from typing import Any

from adapter_common import (
    fail,
    first_env,
    hwp_message,
    hwp_round,
    hwp_session_id,
    json_headers,
    require_first_env,
)
from base_adapter import AdapterBase

# 保留原有的 post_json 导入，供测试 mock 使用
from adapter_common import post_json


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
    """解析 provider 的 base URL

    Args:
        provider_name: provider 名称

    Returns:
        base URL
    """
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


class OpenAICompatibleAdapter(AdapterBase):
    """OpenAI 兼容 API 适配器"""

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str,
        timeout: int = 120,
        temperature: float = 0.7,
    ) -> None:
        super().__init__(base_url, model, api_key, timeout)
        self.temperature = temperature

    def _get_endpoint(self) -> str:
        return "/chat/completions"

    def _get_headers(self) -> dict[str, str]:
        return json_headers({"Authorization": f"Bearer {self.api_key}"})

    def _build_payload(self, message: str) -> dict[str, Any]:
        return {
            "model": self.model,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Session: {hwp_session_id()}\n"
                        f"Round: {hwp_round() or 'unknown'}\n\n"
                        f"{message}"
                    ),
                },
            ],
        }

    def _post_request(self, endpoint: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        """HTTP POST 封装 - 调用本模块作用域内的 post_json 供测试 mock"""
        url = f"{self.base_url}{endpoint}"
        return post_json(url, payload, headers, timeout=self.timeout)

    def _parse_response(self, response: dict[str, Any]) -> str:
        return (
            response.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )


def main() -> int:
    try:
        api_key = require_first_env("HWP_LLM_API_KEY", "OPENAI_API_KEY")
        model = require_first_env("HWP_LLM_MODEL", "OPENAI_MODEL")
        provider_name = first_env("HWP_PROVIDER_NAME", default="openai").lower()
        base_url = resolve_base_url(provider_name)
        temperature = float(first_env("HWP_LLM_TEMPERATURE", "HWP_OPENAI_TEMPERATURE", default="0.7"))
        timeout = int(first_env("HWP_LLM_TIMEOUT_SEC", "HWP_OPENAI_TIMEOUT_SEC", default="120"))

        adapter = OpenAICompatibleAdapter(
            base_url=base_url,
            model=model,
            api_key=api_key,
            timeout=timeout,
            temperature=temperature,
        )

        message = hwp_message()
        inner_json_text = adapter.call(message)
        adapter.wrap_and_print(inner_json_text)
        return 0
    except Exception as exc:
        fail(str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
