#!/usr/bin/env python3
"""Ollama 适配器

支持本地 Ollama 服务的 LLM 调用。
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from typing import Any

from adapter_common import (
    fail,
    hwp_message,
    hwp_round,
    hwp_session_id,
    json_headers,
    optional_env,
    require_env,
)
from base_adapter import AdapterBase

# 保留原有的 post_json 导入，供测试 mock 使用
from adapter_common import post_json


SYSTEM_PROMPT = (
    "You are an execution adapter for HWP. "
    "Return exactly one JSON object and nothing else. "
    "Do not wrap the JSON in Markdown fences. "
    "Do not explain the answer."
)


class OllamaAdapter(AdapterBase):
    """Ollama API 适配器"""

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: int = 120,
        temperature: float = 0.7,
    ) -> None:
        # Ollama 不需要 API key
        super().__init__(base_url, model, api_key="", timeout=timeout)
        self.temperature = temperature

    def _get_endpoint(self) -> str:
        return "/api/generate"

    def _get_headers(self) -> dict[str, str]:
        return json_headers()

    def _build_payload(self, message: str) -> dict[str, Any]:
        return {
            "model": self.model,
            "stream": False,
            "format": "json",
            "system": SYSTEM_PROMPT,
            "prompt": (
                f"Session: {hwp_session_id()}\n"
                f"Round: {hwp_round() or 'unknown'}\n\n"
                f"{message}"
            ),
            "options": {
                "temperature": self.temperature,
            },
        }

    def _post_request(self, endpoint: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        """HTTP POST 封装 - 调用本模块作用域内的 post_json 供测试 mock"""
        url = f"{self.base_url}{endpoint}"
        return post_json(url, payload, headers, timeout=self.timeout)

    def _parse_response(self, response: dict[str, Any]) -> str:
        return response.get("response", "")


def main() -> int:
    try:
        model = require_env("OLLAMA_MODEL")
        base_url = optional_env("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        temperature = float(optional_env("HWP_OLLAMA_TEMPERATURE", "0.7"))
        timeout = int(optional_env("HWP_OLLAMA_TIMEOUT_SEC", "120"))

        adapter = OllamaAdapter(
            base_url=base_url,
            model=model,
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
