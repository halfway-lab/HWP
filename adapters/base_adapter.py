#!/usr/bin/env python3
"""AdapterBase - 统一适配器框架基类

提供 LLM 适配器的通用接口和错误处理机制，降低新 adapter 编写复杂度。
仅使用 Python 标准库，零第三方依赖。
"""
from abc import ABC, abstractmethod
import concurrent.futures
import json
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from adapter_common import (
    extract_json_object_text,
    json_headers,
    post_json,
    wrap_result,
)


class AdapterBase(ABC):
    """LLM 适配器基类

    子类需要实现：
    - _parse_response(response: dict) -> str: 解析 LLM 返回的响应

    可选重写：
    - _build_payload(message: str) -> dict: 构建请求 payload
    - _get_endpoint() -> str: 获取 API endpoint
    - _get_headers() -> dict[str, str]: 获取请求头
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "",
        timeout: int = 120,
    ) -> None:
        """初始化适配器

        Args:
            base_url: API 基础 URL
            model: 模型名称
            api_key: API 密钥（可选）
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    def call(self, message: str) -> str:
        """统一调用入口

        Args:
            message: 发送给 LLM 的消息

        Returns:
            解析后的 JSON 文本字符串

        Raises:
            RuntimeError: 调用失败时抛出
        """
        try:
            endpoint = self._get_endpoint()
            payload = self._build_payload(message)
            headers = self._get_headers()

            response = self._post_request(endpoint, payload, headers)
            content = self._parse_response(response)
            inner_json_text = self._extract_json(content)

            return inner_json_text
        except Exception as exc:
            self._handle_error(exc, "call")

    def _post_request(
        self,
        endpoint: str,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> dict[str, Any]:
        """HTTP POST 封装

        Args:
            endpoint: API endpoint（将追加到 base_url）
            payload: 请求体
            headers: 请求头

        Returns:
            解析后的 JSON 响应
        """
        url = f"{self.base_url}{endpoint}"
        return post_json(url, payload, headers, timeout=self.timeout)

    @abstractmethod
    def _parse_response(self, response: dict[str, Any]) -> str:
        """解析 LLM 返回的响应（子类必须实现）

        Args:
            response: API 返回的 JSON 响应

        Returns:
            提取的内容文本
        """
        raise NotImplementedError

    def _build_payload(self, message: str) -> dict[str, Any]:
        """构建请求 payload（子类可重写）

        Args:
            message: 用户消息

        Returns:
            请求 payload 字典
        """
        raise NotImplementedError

    def _get_endpoint(self) -> str:
        """获取 API endpoint（子类可重写）

        Returns:
            API endpoint 路径
        """
        raise NotImplementedError

    def _get_headers(self) -> dict[str, str]:
        """获取请求头（子类可重写）

        Returns:
            请求头字典
        """
        return json_headers()

    def _handle_error(self, error: Exception, context: str) -> None:
        """统一错误处理

        Args:
            error: 异常对象
            context: 错误上下文描述

        Raises:
            RuntimeError: 总是抛出 RuntimeError，包含上下文信息
        """
        raise RuntimeError(f"[{context}] {error}") from error

    def _extract_json(self, text: str) -> str:
        """从文本中提取 JSON 对象

        Args:
            text: 可能包含 JSON 的文本

        Returns:
            提取的 JSON 文本
        """
        return extract_json_object_text(text)

    def wrap_and_print(self, inner_json_text: str) -> None:
        """包装结果并输出到 stdout

        Args:
            inner_json_text: 内部 JSON 文本
        """
        wrap_result(inner_json_text)

    def async_call(self, message: str, executor: concurrent.futures.Executor | None = None) -> concurrent.futures.Future[str]:
        """异步调用入口，使用 ThreadPoolExecutor 包装同步 HTTP 调用

        由于 urllib 不支持原生 async，且项目约束零第三方依赖（不使用 aiohttp），
        使用 concurrent.futures.ThreadPoolExecutor 实现异步调用。

        Args:
            message: 发送给 LLM 的消息
            executor: 可选的 ThreadPoolExecutor 实例。如果为 None，则创建默认 executor

        Returns:
            Future 对象，可通过 .result() 获取结果

        Example:
            adapter = OpenAICompatibleAdapter(...)
            future = adapter.async_call("Hello")
            result = future.result()  # 阻塞等待结果
        """
        if executor is None:
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        return executor.submit(self.call, message)
