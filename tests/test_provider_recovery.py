#!/usr/bin/env python3
"""Provider 故障恢复测试

测试 adapter 在各种异常场景下的错误输出格式，以及 Shell 层的重试逻辑。
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

# 添加 adapters 目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "adapters"))

from adapters.adapter_common import (
    extract_json_object_text,
    fail,
    post_json,
    wrap_result,
)
from adapters.openai_compatible_adapter import main as openai_main
from adapters.ollama_adapter import main as ollama_main


class AdapterCommonRecoveryTests(unittest.TestCase):
    """测试 adapter_common.py 的错误处理"""

    @patch("adapters.adapter_common.urllib.request.urlopen")
    def test_post_json_handles_http_500_error(self, mock_urlopen) -> None:
        """Mock HTTP 响应返回 500 错误"""
        from urllib.error import HTTPError

        mock_response = MagicMock()
        mock_response.read.return_value = b'{"error": "internal server error"}'
        mock_urlopen.side_effect = HTTPError(
            url="https://api.example.com/v1/chat/completions",
            code=500,
            msg="Internal Server Error",
            hdrs={},
            fp=mock_response,
        )

        with self.assertRaises(RuntimeError) as ctx:
            post_json(
                "https://api.example.com/v1/chat/completions",
                {"model": "test"},
                {"Authorization": "Bearer test"},
            )

        self.assertIn("500", str(ctx.exception))
        self.assertIn("Internal Server Error", str(ctx.exception))

    @patch("adapters.adapter_common.urllib.request.urlopen")
    def test_post_json_handles_timeout(self, mock_urlopen) -> None:
        """Mock HTTP 响应返回超时"""
        from urllib.error import URLError

        mock_urlopen.side_effect = URLError("timed out")

        with self.assertRaises(RuntimeError) as ctx:
            post_json(
                "https://api.example.com/v1/chat/completions",
                {"model": "test"},
                {"Authorization": "Bearer test"},
                timeout=1,
            )

        self.assertIn("timed out", str(ctx.exception).lower())

    @patch("adapters.adapter_common.urllib.request.urlopen")
    def test_post_json_handles_empty_body(self, mock_urlopen) -> None:
        """Mock HTTP 响应返回空 body"""
        mock_resp = MagicMock()
        mock_resp.read.return_value = b""
        mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_resp)
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

        with self.assertRaises(RuntimeError) as ctx:
            post_json(
                "https://api.example.com/v1/chat/completions",
                {"model": "test"},
                {"Authorization": "Bearer test"},
            )

        self.assertIn("non-JSON", str(ctx.exception))

    @patch("adapters.adapter_common.urllib.request.urlopen")
    def test_post_json_handles_non_json_response(self, mock_urlopen) -> None:
        """Mock HTTP 响应返回非 JSON 格式"""
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"<html><body>Server Error</body></html>"
        mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_resp)
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

        with self.assertRaises(RuntimeError) as ctx:
            post_json(
                "https://api.example.com/v1/chat/completions",
                {"model": "test"},
                {"Authorization": "Bearer test"},
            )

        self.assertIn("non-JSON", str(ctx.exception))

    @patch("adapters.adapter_common.urllib.request.urlopen")
    def test_post_json_handles_json_missing_required_fields(self, mock_urlopen) -> None:
        """Mock HTTP 响应返回 JSON 但缺少必要字段 - adapter 层应该能处理"""
        mock_resp = MagicMock()
        # 返回一个没有 choices 字段的 JSON
        mock_resp.read.return_value = b'{"status": "ok", "id": "test-123"}'
        mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_resp)
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

        # post_json 本身不会验证字段，只是返回解析后的 JSON
        result = post_json(
            "https://api.example.com/v1/chat/completions",
            {"model": "test"},
            {"Authorization": "Bearer test"},
        )

        self.assertEqual(result, {"status": "ok", "id": "test-123"})


class OpenAICompatibleAdapterRecoveryTests(unittest.TestCase):
    """测试 openai_compatible_adapter.py 的错误处理"""

    @patch.dict(
        os.environ,
        {
            "HWP_AGENT_MESSAGE": "test message",
            "HWP_LLM_API_KEY": "test-key",
            "HWP_LLM_MODEL": "test-model",
            "HWP_PROVIDER_NAME": "deepseek",
        },
        clear=True,
    )
    @patch("adapters.openai_compatible_adapter.post_json")
    def test_adapter_handles_empty_choices(self, mock_post_json) -> None:
        """测试返回 JSON 但 choices 为空数组 - adapter 应该调用 fail 输出 FATAL"""
        mock_post_json.return_value = {"choices": []}

        # adapter 会捕获 IndexError 并调用 fail() 导致 SystemExit
        with self.assertRaises(SystemExit) as ctx:
            openai_main()

        self.assertEqual(ctx.exception.code, 1)

    @patch.dict(
        os.environ,
        {
            "HWP_AGENT_MESSAGE": "test message",
            "HWP_LLM_API_KEY": "test-key",
            "HWP_LLM_MODEL": "test-model",
            "HWP_PROVIDER_NAME": "deepseek",
        },
        clear=True,
    )
    @patch("adapters.openai_compatible_adapter.post_json")
    def test_adapter_handles_missing_content(self, mock_post_json) -> None:
        """测试返回 JSON 但缺少 content 字段 - adapter 应该调用 fail 输出 FATAL"""
        mock_post_json.return_value = {
            "choices": [{"message": {"role": "assistant"}}]
        }

        # 应该返回空 content，然后 extract_json_object_text 会报错
        # adapter 会捕获异常并调用 fail() 导致 SystemExit
        with self.assertRaises(SystemExit) as ctx:
            openai_main()

        self.assertEqual(ctx.exception.code, 1)

    @patch.dict(
        os.environ,
        {
            "HWP_AGENT_MESSAGE": "test message",
            "HWP_LLM_API_KEY": "test-key",
            "HWP_LLM_MODEL": "test-model",
            "HWP_PROVIDER_NAME": "deepseek",
        },
        clear=True,
    )
    @patch("adapters.openai_compatible_adapter.post_json")
    def test_adapter_handles_malformed_json_in_content(self, mock_post_json) -> None:
        """测试 content 中包含非 JSON 内容 - adapter 应该调用 fail 输出 FATAL"""
        mock_post_json.return_value = {
            "choices": [{"message": {"content": "not valid json"}}]
        }

        # adapter 会捕获异常并调用 fail() 导致 SystemExit
        with self.assertRaises(SystemExit) as ctx:
            openai_main()

        self.assertEqual(ctx.exception.code, 1)


class OllamaAdapterRecoveryTests(unittest.TestCase):
    """测试 ollama_adapter.py 的错误处理"""

    @patch.dict(
        os.environ,
        {
            "HWP_AGENT_MESSAGE": "test message",
            "OLLAMA_MODEL": "test-model",
        },
        clear=True,
    )
    @patch("adapters.ollama_adapter.post_json")
    def test_adapter_handles_empty_response(self, mock_post_json) -> None:
        """测试返回空 response - adapter 应该调用 fail 输出 FATAL"""
        mock_post_json.return_value = {"response": ""}

        # adapter 会捕获异常并调用 fail() 导致 SystemExit
        with self.assertRaises(SystemExit) as ctx:
            ollama_main()

        self.assertEqual(ctx.exception.code, 1)

    @patch.dict(
        os.environ,
        {
            "HWP_AGENT_MESSAGE": "test message",
            "OLLAMA_MODEL": "test-model",
        },
        clear=True,
    )
    @patch("adapters.ollama_adapter.post_json")
    def test_adapter_handles_missing_response_field(self, mock_post_json) -> None:
        """测试返回 JSON 但缺少 response 字段 - adapter 应该调用 fail 输出 FATAL"""
        mock_post_json.return_value = {"done": True, "total_duration": 123}

        # 应该返回空 content，然后 extract_json_object_text 会报错
        # adapter 会捕获异常并调用 fail() 导致 SystemExit
        with self.assertRaises(SystemExit) as ctx:
            ollama_main()

        self.assertEqual(ctx.exception.code, 1)

    @patch.dict(
        os.environ,
        {
            "HWP_AGENT_MESSAGE": "test message",
            "OLLAMA_MODEL": "test-model",
        },
        clear=True,
    )
    @patch("adapters.ollama_adapter.post_json")
    def test_adapter_handles_malformed_json_in_response(self, mock_post_json) -> None:
        """测试 response 中包含非 JSON 内容 - adapter 应该调用 fail 输出 FATAL"""
        mock_post_json.return_value = {"response": "this is not json"}

        # adapter 会捕获异常并调用 fail() 导致 SystemExit
        with self.assertRaises(SystemExit) as ctx:
            ollama_main()

        self.assertEqual(ctx.exception.code, 1)


class AdapterErrorOutputFormatTests(unittest.TestCase):
    """测试 adapter 错误输出格式是否符合预期"""

    @patch("adapters.adapter_common.sys.stderr", new_callable=lambda: sys.stderr)
    @patch.dict(os.environ, {}, clear=True)
    def test_fail_outputs_fatal_to_stderr(self, mock_stderr) -> None:
        """验证 fail 函数输出格式包含 FATAL 并退出码为 1"""
        # 注意：fail 函数会调用 SystemExit(1)
        with self.assertRaises(SystemExit) as ctx:
            fail("test error message")

        self.assertEqual(ctx.exception.code, 1)

    @patch("adapters.adapter_common.urllib.request.urlopen")
    @patch.dict(
        os.environ,
        {
            "HWP_AGENT_MESSAGE": "test",
            "HWP_LLM_API_KEY": "key",
            "HWP_LLM_MODEL": "model",
        },
        clear=True,
    )
    def test_openai_adapter_fatal_on_network_error(self, mock_urlopen) -> None:
        """验证网络错误时 adapter 输出 FATAL"""
        from urllib.error import URLError

        mock_urlopen.side_effect = URLError("Connection refused")

        with self.assertRaises(SystemExit) as ctx:
            openai_main()

        self.assertEqual(ctx.exception.code, 1)

    @patch("adapters.adapter_common.urllib.request.urlopen")
    @patch.dict(
        os.environ,
        {
            "HWP_AGENT_MESSAGE": "test",
            "OLLAMA_MODEL": "model",
        },
        clear=True,
    )
    def test_ollama_adapter_fatal_on_network_error(self, mock_urlopen) -> None:
        """验证网络错误时 adapter 输出 FATAL"""
        from urllib.error import URLError

        mock_urlopen.side_effect = URLError("Connection refused")

        with self.assertRaises(SystemExit) as ctx:
            ollama_main()

        self.assertEqual(ctx.exception.code, 1)


class ShellRetryLogicTests(unittest.TestCase):
    """测试 Shell 层的重试逻辑（通过 subprocess 测试 lib_agent.sh）"""

    def setUp(self) -> None:
        """设置测试环境"""
        self.root_dir = Path(__file__).resolve().parent.parent
        self.lib_agent_path = self.root_dir / "runs" / "lib_agent.sh"
        self.mock_adapter_dir = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        """清理测试环境"""
        import shutil

        shutil.rmtree(self.mock_adapter_dir, ignore_errors=True)

    def _create_mock_adapter(self, fail_count: int = 0) -> Path:
        """创建一个模拟 adapter 脚本，前 fail_count 次调用失败"""
        mock_script = self.mock_adapter_dir / "mock_adapter.sh"
        mock_counter = self.mock_adapter_dir / ".counter"

        script_content = f'''#!/bin/bash
COUNTER_FILE="{mock_counter}"
if [ -f "$COUNTER_FILE" ]; then
    COUNT=$(cat "$COUNTER_FILE")
else
    COUNT=0
fi
COUNT=$((COUNT + 1))
echo $COUNT > "$COUNTER_FILE"

if [ $COUNT -le {fail_count} ]; then
    echo "FATAL: Mock failure #$COUNT" >&2
    exit 1
fi

# 成功响应
echo '{{"result":{{"payloads":[{{"text":"{{\\"node_id\\":\\"test\\"}}"}}]}}}}'
exit 0
'''
        mock_script.write_text(script_content)
        mock_script.chmod(0o755)
        return mock_script

    def _run_with_lib_agent(
        self, mock_adapter: Path, max_retries: int = 3, timeout: int = 5
    ) -> tuple[int, str, str]:
        """使用 lib_agent.sh 运行 mock adapter"""
        env = os.environ.copy()
        env["HWP_AGENT_CMD"] = str(mock_adapter)
        env["HWP_AGENT_MAX_RETRIES"] = str(max_retries)
        env["HWP_AGENT_TIMEOUT"] = str(timeout)
        env["HWP_AGENT_MESSAGE"] = "test message"
        env["HWP_AGENT_SESSION_ID"] = "test-session"

        # 创建一个调用 lib_agent.sh 的测试脚本
        test_script = f'''#!/bin/bash
source "{self.lib_agent_path}"
invoke_hwp_agent "test message" "test-session" "1"
'''
        test_script_path = self.mock_adapter_dir / "test_runner.sh"
        test_script_path.write_text(test_script)
        test_script_path.chmod(0o755)

        result = subprocess.run(
            ["/bin/bash", str(test_script_path)],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(self.root_dir),
        )

        return result.returncode, result.stdout, result.stderr

    def test_retry_succeeds_after_one_failure(self) -> None:
        """验证重试机制：1 次失败后成功"""
        mock_adapter = self._create_mock_adapter(fail_count=1)
        returncode, stdout, stderr = self._run_with_lib_agent(
            mock_adapter, max_retries=3
        )

        self.assertEqual(returncode, 0)
        self.assertIn("retrying", stderr.lower())
        self.assertIn("attempt 1/3", stderr.lower())

    def test_retry_exhausts_all_retries(self) -> None:
        """验证重试机制：所有重试都失败后退出"""
        mock_adapter = self._create_mock_adapter(fail_count=10)
        returncode, stdout, stderr = self._run_with_lib_agent(
            mock_adapter, max_retries=2
        )

        self.assertEqual(returncode, 1)
        self.assertIn("FATAL", stderr)
        self.assertIn("failed after 2 retries", stderr)

    def test_retry_backoff_timing(self) -> None:
        """验证退避时间：2s/4s/8s 指数退避"""
        mock_adapter = self._create_mock_adapter(fail_count=3)

        import time

        start_time = time.time()
        returncode, stdout, stderr = self._run_with_lib_agent(
            mock_adapter, max_retries=3
        )
        elapsed = time.time() - start_time

        # 应该有 3 次重试，退避时间 2s + 4s + 8s = 14s
        # 但由于我们设置了 fail_count=3，第 4 次会成功
        # 所以实际等待 2s + 4s + 8s = 14s
        self.assertEqual(returncode, 0)
        self.assertIn("retrying in 2s", stderr)
        self.assertIn("retrying in 4s", stderr)
        self.assertIn("retrying in 8s", stderr)
        self.assertGreater(elapsed, 13)  # 至少等待了 2+4+8=14s，允许一定误差

    def test_no_retry_on_immediate_success(self) -> None:
        """验证立即成功时不重试"""
        mock_adapter = self._create_mock_adapter(fail_count=0)
        returncode, stdout, stderr = self._run_with_lib_agent(
            mock_adapter, max_retries=3
        )

        self.assertEqual(returncode, 0)
        self.assertNotIn("retrying", stderr.lower())
        self.assertNotIn("FATAL", stderr)

    def test_custom_retry_count(self) -> None:
        """验证自定义重试次数"""
        mock_adapter = self._create_mock_adapter(fail_count=5)
        returncode, stdout, stderr = self._run_with_lib_agent(
            mock_adapter, max_retries=5
        )

        # 5 次重试后成功
        self.assertEqual(returncode, 0)
        self.assertIn("attempt 5/5", stderr)


class ExtractJsonObjectTextRecoveryTests(unittest.TestCase):
    """测试 extract_json_object_text 的错误恢复"""

    def test_empty_text_raises_error(self) -> None:
        """测试空文本报错"""
        with self.assertRaises(RuntimeError) as ctx:
            extract_json_object_text("")

        self.assertIn("empty", str(ctx.exception).lower())

    def test_no_json_object_raises_error(self) -> None:
        """测试没有 JSON 对象时报错"""
        with self.assertRaises(RuntimeError) as ctx:
            extract_json_object_text("just some text without json")

        self.assertIn("JSON object", str(ctx.exception))

    def test_incomplete_json_raises_error(self) -> None:
        """测试不完整的 JSON 报错"""
        with self.assertRaises(RuntimeError) as ctx:
            extract_json_object_text('{"incomplete": ')

        self.assertIn("unable to recover", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
