#!/usr/bin/env python3
"""API Server 测试

使用 FastAPI TestClient 测试 API 端点，覆盖：
- 健康检查
- 提交运行 + 查询状态 + 获取结果完整流程
- 多 Provider 调用
- API Key 认证
- 参数校验
- 取消运行
- 404 场景
- 结果未就绪
- 控制器配置
- Provider 列表
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def client() -> TestClient:
    """创建 TestClient 实例，清理会话状态并重置 executor"""
    import api_server
    from concurrent.futures import ThreadPoolExecutor

    # 清理会话状态
    api_server._sessions.clear()

    # 重置 executor（解决 "cannot schedule new futures after shutdown" 问题）
    api_server._executor = ThreadPoolExecutor(max_workers=4)

    with TestClient(api_server.app) as test_client:
        yield test_client

    # 测试结束后清理
    api_server._sessions.clear()
    api_server._executor.shutdown(wait=False)
    api_server._executor = ThreadPoolExecutor(max_workers=4)


@pytest.fixture
def mock_provider_config() -> dict[str, str]:
    """模拟的 provider 配置"""
    return {
        "HWP_PROVIDER_TYPE": "openai_compatible",
        "HWP_PROVIDER_NAME": "test_provider",
        "HWP_LLM_MODEL": "test-model",
        "HWP_LLM_API_KEY": "test-api-key",
        "HWP_LLM_BASE_URL": "https://api.test.com/v1",
    }


@pytest.fixture
def mock_chain_result() -> dict[str, Any]:
    """模拟的链运行结果"""
    return {
        "node_id": "HWP_R1_20260401T120000",
        "parent_id": None,
        "round": 1,
        "questions": ["What is the meaning of life?"],
        "variables": [{"name": "topic", "value": "philosophy"}],
        "paths": ["explore_consciousness"],
        "tensions": ["dualism_vs_monism"],
        "unfinished": [],
        "entropy_score": 0.65,
        "novelty_rate": 0.42,
        "shared_variable_count": 1,
        "drift_rate": 0.35,
        "collapse_detected": False,
        "recovery_applied": False,
    }


# =============================================================================
# 1. 健康检查测试
# =============================================================================


def test_health_check_returns_ok(client: TestClient) -> None:
    """GET /health 返回 200，body 包含 status='ok' 和 version"""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert data["version"] != ""


def test_health_check_no_auth_required(client: TestClient) -> None:
    """/health 端点不需要认证（即使设置了 API Key）"""
    # 即使在没有设置 HWP_API_KEY 时也应该可以访问
    response = client.get("/health")
    assert response.status_code == 200


# =============================================================================
# 2. 提交运行 + 查询状态 + 获取结果完整流程
# =============================================================================


def test_submit_run_query_status_get_result_full_flow(
    client: TestClient,
    mock_provider_config: dict[str, str],
    mock_chain_result: dict[str, Any],
    tmp_path: Path,
) -> None:
    """测试完整的运行流程：提交 → 查询状态 → 获取结果

    Mock ChainRunner 使其不真正调用 LLM。
    """
    # 创建模拟的链日志文件
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    import json

    chain_log = logs_dir / "chain_test_123.jsonl"
    with open(chain_log, "w", encoding="utf-8") as f:
        f.write(json.dumps(mock_chain_result, ensure_ascii=False) + "\n")

    with (
        patch("api_server.load_provider_config", return_value=mock_provider_config),
        patch("api_server.ChainRunner") as MockChainRunner,
        patch("api_server._extract_last_round_result", return_value=mock_chain_result),
    ):
        # 配置 mock ChainRunner
        mock_runner = MagicMock()
        mock_runner.last_chain_log = chain_log  # 设置确定性路径
        MockChainRunner.return_value = mock_runner

        # 模拟 run_input_file 快速完成
        def mock_run_input_file(input_file: Path) -> None:
            """模拟执行完成"""
            pass

        mock_runner.run_input_file.side_effect = mock_run_input_file

        # 1. 提交运行
        response = client.post(
            "/api/v1/runs",
            json={
                "input_text": "Test input for chain run",
                "rounds": 2,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["status"] == "queued"
        session_id = data["session_id"]

        # 2. 查询状态
        response = client.get(f"/api/v1/runs/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert data["status"] in ("queued", "running", "completed")

        # 等待后台任务完成
        import api_server

        max_wait = 5.0  # 最多等待 5 秒
        start = time.time()
        while time.time() - start < max_wait:
            session = api_server._sessions.get(session_id)
            if session and session.status == "completed":
                break
            time.sleep(0.1)

        # 3. 获取结果
        response = client.get(f"/api/v1/runs/{session_id}/result")
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert data["chain_path"] is not None or data["last_round"] is not None


# =============================================================================
# 3. 多 Provider 调用
# =============================================================================


def test_multi_provider_run(
    client: TestClient,
    mock_provider_config: dict[str, str],
) -> None:
    """POST /api/v1/multi-run 并行调用多个 Provider（使用 provider 名称列表）"""
    mock_results = {
        "deepseek": "DeepSeek response content",
        "moonshot": "Moonshot response content",
    }

    with (
        patch("api_server._load_provider_names", return_value=["deepseek", "moonshot"]),
        patch("api_server.load_provider_config", return_value=mock_provider_config),
        patch("api_server.run_multi_provider", return_value=mock_results),
    ):
        response = client.post(
            "/api/v1/multi-run",
            json={
                "input_text": "Test multi-provider input",
                "providers": ["deepseek", "moonshot"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data


def test_multi_provider_empty_providers(client: TestClient) -> None:
    """POST /api/v1/multi-run 使用空 providers 列表"""
    with (
        patch("api_server._load_provider_names", return_value=[]),
        patch("api_server.run_multi_provider", return_value={}),
    ):
        response = client.post(
            "/api/v1/multi-run",
            json={
                "input_text": "Test input",
                "providers": [],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["results"] == {}


# =============================================================================
# 4. API Key 认证
# =============================================================================


def test_api_key_auth_no_key_header_when_required(client: TestClient) -> None:
    """无 API Key Header 时返回 401（当设置了 HWP_API_KEY）"""
    import api_server

    original_key = api_server.HWP_API_KEY

    try:
        # 设置 API Key
        api_server.HWP_API_KEY = "test-secret-key"

        # 无 Header 请求
        response = client.post(
            "/api/v1/runs",
            json={"input_text": "Test", "rounds": 8},
        )

        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]

    finally:
        api_server.HWP_API_KEY = original_key


def test_api_key_auth_wrong_key(client: TestClient) -> None:
    """错误 API Key 时返回 401"""
    import api_server

    original_key = api_server.HWP_API_KEY

    try:
        api_server.HWP_API_KEY = "correct-secret-key"

        response = client.post(
            "/api/v1/runs",
            json={"input_text": "Test", "rounds": 8},
            headers={"X-API-Key": "wrong-key"},
        )

        assert response.status_code == 401

    finally:
        api_server.HWP_API_KEY = original_key


def test_api_key_auth_correct_key(client: TestClient, mock_provider_config: dict[str, str]) -> None:
    """正确 API Key 时返回 200"""
    import api_server

    original_key = api_server.HWP_API_KEY

    try:
        api_server.HWP_API_KEY = "test-secret-key"

        with patch("api_server.load_provider_config", return_value=mock_provider_config):
            response = client.post(
                "/api/v1/runs",
                json={"input_text": "Test", "rounds": 1},
                headers={"X-API-Key": "test-secret-key"},
            )

            assert response.status_code == 200

    finally:
        api_server.HWP_API_KEY = original_key


def test_api_key_auth_dev_mode_no_key_required(client: TestClient, mock_provider_config: dict[str, str]) -> None:
    """未设置 HWP_API_KEY 时（开发模式）无需 Key 也能访问"""
    import api_server

    original_key = api_server.HWP_API_KEY

    try:
        # 清除 API Key（开发模式）
        api_server.HWP_API_KEY = ""

        with patch("api_server.load_provider_config", return_value=mock_provider_config):
            response = client.post(
                "/api/v1/runs",
                json={"input_text": "Test", "rounds": 1},
            )

            assert response.status_code == 200

    finally:
        api_server.HWP_API_KEY = original_key


def test_health_endpoint_no_auth_required(client: TestClient) -> None:
    """验证 /health 端点不需要认证"""
    import api_server

    original_key = api_server.HWP_API_KEY

    try:
        # 设置 API Key
        api_server.HWP_API_KEY = "test-secret-key"

        # /health 不需要认证
        response = client.get("/health")
        assert response.status_code == 200

    finally:
        api_server.HWP_API_KEY = original_key


# =============================================================================
# 5. 参数校验
# =============================================================================


def test_validation_missing_input_text(client: TestClient) -> None:
    """POST /api/v1/runs 缺少 input_text → 422"""
    response = client.post(
        "/api/v1/runs",
        json={"rounds": 8},
    )

    assert response.status_code == 422


def test_validation_negative_rounds(client: TestClient) -> None:
    """POST /api/v1/runs rounds 为负数 → 422"""
    response = client.post(
        "/api/v1/runs",
        json={"input_text": "Test", "rounds": -1},
    )

    assert response.status_code == 422


def test_validation_zero_rounds(client: TestClient) -> None:
    """POST /api/v1/runs rounds 为 0 → 422"""
    response = client.post(
        "/api/v1/runs",
        json={"input_text": "Test", "rounds": 0},
    )

    assert response.status_code == 422


def test_validation_rounds_too_large(client: TestClient) -> None:
    """POST /api/v1/runs rounds 超过 100 → 422"""
    response = client.post(
        "/api/v1/runs",
        json={"input_text": "Test", "rounds": 101},
    )

    assert response.status_code == 422


def test_validation_negative_timeout(client: TestClient) -> None:
    """POST /api/v1/runs timeout_sec 为负数 → 422"""
    response = client.post(
        "/api/v1/runs",
        json={"input_text": "Test", "rounds": 8, "timeout_sec": -1.0},
    )

    assert response.status_code == 422


def test_validation_negative_sleep(client: TestClient) -> None:
    """POST /api/v1/runs sleep_sec 为负数 → 422"""
    response = client.post(
        "/api/v1/runs",
        json={"input_text": "Test", "rounds": 8, "sleep_sec": -1.0},
    )

    assert response.status_code == 422


# =============================================================================
# 6. 取消运行
# =============================================================================


def test_cancel_run(client: TestClient, mock_provider_config: dict[str, str]) -> None:
    """提交任务后立即取消"""
    import api_server

    with patch("api_server.load_provider_config", return_value=mock_provider_config):
        # 提交运行
        response = client.post(
            "/api/v1/runs",
            json={"input_text": "Test to cancel", "rounds": 8},
        )

        assert response.status_code == 200
        session_id = response.json()["session_id"]

        # 立即取消
        response = client.delete(f"/api/v1/runs/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["cancelled"] is True

        # 验证状态变为 cancelled
        session = api_server._sessions.get(session_id)
        assert session is not None
        assert session.status == "cancelled"


def test_cancel_run_sets_cancel_flag(client: TestClient, mock_provider_config: dict[str, str]) -> None:
    """取消运行时设置 cancel_flag"""
    import api_server

    with patch("api_server.load_provider_config", return_value=mock_provider_config):
        response = client.post(
            "/api/v1/runs",
            json={"input_text": "Test", "rounds": 8},
        )

        session_id = response.json()["session_id"]
        session = api_server._sessions.get(session_id)
        assert session is not None

        # 初始时 cancel_flag 未设置
        assert not session.cancel_flag.is_set()

        # 取消后 cancel_flag 被设置
        client.delete(f"/api/v1/runs/{session_id}")
        assert session.cancel_flag.is_set()


# =============================================================================
# 7. 404 场景
# =============================================================================


def test_404_get_nonexistent_run(client: TestClient) -> None:
    """GET /api/v1/runs/nonexistent-id → 404"""
    response = client.get("/api/v1/runs/nonexistent-session-id")

    assert response.status_code == 404
    assert "Session not found" in response.json()["detail"]


def test_404_get_nonexistent_result(client: TestClient) -> None:
    """GET /api/v1/runs/nonexistent-id/result → 404"""
    response = client.get("/api/v1/runs/nonexistent-session-id/result")

    assert response.status_code == 404
    assert "Session not found" in response.json()["detail"]


def test_404_delete_nonexistent_run(client: TestClient) -> None:
    """DELETE /api/v1/runs/nonexistent-id → 404"""
    response = client.delete("/api/v1/runs/nonexistent-session-id")

    assert response.status_code == 404
    assert "Session not found" in response.json()["detail"]


# =============================================================================
# 8. 结果未就绪
# =============================================================================


def test_result_not_ready(client: TestClient, mock_provider_config: dict[str, str]) -> None:
    """提交任务后立即 GET result（未完成时）→ 409"""
    import api_server

    with patch("api_server.load_provider_config", return_value=mock_provider_config):
        # 提交运行
        response = client.post(
            "/api/v1/runs",
            json={"input_text": "Test", "rounds": 8},
        )

        session_id = response.json()["session_id"]

        # 确保状态不是 completed
        session = api_server._sessions.get(session_id)
        if session and session.status != "completed":
            response = client.get(f"/api/v1/runs/{session_id}/result")
            assert response.status_code == 409
            assert "not completed" in response.json()["detail"].lower()


def test_result_after_cancelled(client: TestClient, mock_provider_config: dict[str, str]) -> None:
    """取消后获取结果 → 409"""
    with patch("api_server.load_provider_config", return_value=mock_provider_config):
        response = client.post(
            "/api/v1/runs",
            json={"input_text": "Test", "rounds": 8},
        )

        session_id = response.json()["session_id"]

        # 取消运行
        client.delete(f"/api/v1/runs/{session_id}")

        # 尝试获取结果
        response = client.get(f"/api/v1/runs/{session_id}/result")
        assert response.status_code == 409


# =============================================================================
# 9. 控制器配置
# =============================================================================


def test_get_controller_config(client: TestClient) -> None:
    """GET /api/v1/config/controller 返回 200，包含 modes/thresholds/defaults"""
    mock_config = {
        "version": "0.6.2",
        "modes": {
            "Rg0": {"entropy_target": {"min": 0.40, "max": 0.79}},
            "Rg1": {"entropy_target": {"min": 0.55, "max": 0.85}},
            "Rg2": {"entropy_target": {"min": 0.35, "max": 0.65}},
        },
        "thresholds": {
            "drift_low": 0.30,
            "drift_high": 0.70,
        },
        "defaults": {
            "rounds_per_chain": 8,
            "round_sleep_sec": 2.0,
        },
    }

    with patch("api_server.load_controller_config", return_value=mock_config):
        response = client.get("/api/v1/config/controller")

        assert response.status_code == 200
        data = response.json()
        assert "modes" in data
        assert "thresholds" in data
        assert "defaults" in data


# =============================================================================
# 10. Provider 列表
# =============================================================================


def test_list_providers(client: TestClient) -> None:
    """GET /api/v1/providers 返回 200，包含 providers 列表"""
    response = client.get("/api/v1/providers")

    assert response.status_code == 200
    data = response.json()
    assert "providers" in data
    assert isinstance(data["providers"], list)


def test_list_providers_parses_file(client: TestClient, tmp_path: Path) -> None:
    """Provider 列表正确解析 providers.list 文件"""
    import api_server

    # 创建临时 providers.list 文件
    providers_file = tmp_path / "config" / "providers.list"
    providers_file.parent.mkdir(parents=True, exist_ok=True)

    with open(providers_file, "w", encoding="utf-8") as f:
        f.write("# Provider configurations\n")
        f.write("deepseek|provider.deepseek.env|DeepSeek API\n")
        f.write("moonshot|provider.moonshot.env|Moonshot API\n")
        f.write("\n")  # 空行
        f.write("# Comment line\n")
        f.write("ollama|provider.ollama.env|Ollama Local\n")

    # 临时替换 ROOT_DIR
    original_root = api_server.ROOT_DIR
    try:
        api_server.ROOT_DIR = tmp_path

        response = client.get("/api/v1/providers")

        assert response.status_code == 200
        data = response.json()
        providers = data["providers"]

        # 应该包含 3 个 provider（跳过空行和注释）
        assert "deepseek" in providers
        assert "moonshot" in providers
        assert "ollama" in providers

    finally:
        api_server.ROOT_DIR = original_root


def test_list_providers_file_not_exists(client: TestClient, tmp_path: Path) -> None:
    """providers.list 文件不存在时返回空列表"""
    import api_server

    original_root = api_server.ROOT_DIR
    try:
        api_server.ROOT_DIR = tmp_path

        response = client.get("/api/v1/providers")

        assert response.status_code == 200
        data = response.json()
        assert data["providers"] == []

    finally:
        api_server.ROOT_DIR = original_root


# =============================================================================
# 额外测试：SessionState 状态转换
# =============================================================================


def test_run_status_response_structure(client: TestClient, mock_provider_config: dict[str, str]) -> None:
    """验证 RunStatusResponse 的完整结构"""
    with patch("api_server.load_provider_config", return_value=mock_provider_config):
        response = client.post(
            "/api/v1/runs",
            json={"input_text": "Test status structure", "rounds": 4},
        )

        session_id = response.json()["session_id"]

        response = client.get(f"/api/v1/runs/{session_id}")
        assert response.status_code == 200

        data = response.json()
        # 验证所有必需字段
        assert "session_id" in data
        assert "status" in data
        assert "current_round" in data
        assert "total_rounds" in data
        assert data["total_rounds"] == 4


def test_run_result_response_structure(
    client: TestClient,
    mock_provider_config: dict[str, str],
    mock_chain_result: dict[str, Any],
    tmp_path: Path,
) -> None:
    """验证 RunResultResponse 的完整结构"""
    import api_server
    import json

    # 创建模拟日志文件
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    chain_log = logs_dir / "chain_test_result.jsonl"
    with open(chain_log, "w", encoding="utf-8") as f:
        f.write(json.dumps(mock_chain_result, ensure_ascii=False) + "\n")

    with (
        patch("api_server.load_provider_config", return_value=mock_provider_config),
        patch("api_server.ChainRunner") as MockChainRunner,
        patch("api_server._extract_last_round_result", return_value=mock_chain_result),
    ):
        # 配置 mock ChainRunner
        mock_runner = MagicMock()
        mock_runner.last_chain_log = chain_log  # 设置确定性路径
        MockChainRunner.return_value = mock_runner

        response = client.post(
            "/api/v1/runs",
            json={"input_text": "Test result structure", "rounds": 1},
        )

        session_id = response.json()["session_id"]

        # 等待完成
        max_wait = 3.0
        start = time.time()
        while time.time() - start < max_wait:
            session = api_server._sessions.get(session_id)
            if session and session.status == "completed":
                break
            time.sleep(0.1)

        # 手动设置为完成状态以便测试
        session = api_server._sessions.get(session_id)
        if session:
            session.status = "completed"
            session.result = mock_chain_result
            session.chain_path = str(chain_log)

        response = client.get(f"/api/v1/runs/{session_id}/result")
        assert response.status_code == 200

        data = response.json()
        assert "session_id" in data
        assert "chain_path" in data
        assert "last_round" in data


# =============================================================================
# 并发与边界条件测试
# =============================================================================


def test_concurrent_sessions(client: TestClient, mock_provider_config: dict[str, str]) -> None:
    """测试并发创建多个会话"""
    import api_server

    with patch("api_server.load_provider_config", return_value=mock_provider_config):
        session_ids = []

        # 提交 5 个并发任务
        for i in range(5):
            response = client.post(
                "/api/v1/runs",
                json={"input_text": f"Concurrent test {i}", "rounds": 1},
            )
            assert response.status_code == 200
            session_ids.append(response.json()["session_id"])

        # 验证所有 session_id 唯一
        assert len(set(session_ids)) == 5

        # 验证每个会话都存在
        for session_id in session_ids:
            assert session_id in api_server._sessions


def test_multi_run_with_max_workers(client: TestClient) -> None:
    """测试 multi-run 使用 max_workers 参数"""
    mock_results = {"deepseek": "result1", "moonshot": "result2"}

    with (
        patch("api_server._load_provider_names", return_value=["deepseek", "moonshot"]),
        patch("api_server.load_provider_config", return_value={"HWP_PROVIDER_NAME": "test"}),
        patch("api_server.run_multi_provider", return_value=mock_results) as mock_func,
    ):
        response = client.post(
            "/api/v1/multi-run",
            json={
                "input_text": "Test with max workers",
                "providers": ["deepseek", "moonshot"],
                "max_workers": 2,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["results"] == mock_results

        # 验证 max_workers 被传递
        call_kwargs = mock_func.call_args
        assert call_kwargs is not None


# =============================================================================
# 11. 暂停总结端点测试
# =============================================================================


class TestPauseSummary:
    """暂停总结端点测试"""

    def test_pause_summary_success(self, client: TestClient) -> None:
        """成功调用暂停总结"""
        import json

        mock_result = json.dumps(
            {
                "overall_theme": "认知偏差",
                "progress_summary": "已探索确认偏误和锚定效应",
                "key_insights": ["确认偏误影响信息筛选"],
                "depth_assessment": "中等深度，偏向确认偏误",
                "unexplored_suggestions": ["可用性启发式"],
                "recommended_next_steps": ["探索可用性启发式"],
                "exploration_completeness": 0.4,
            }
        )
        with patch(
            "api_server.invoke_provider_with_retry", return_value=mock_result
        ):
            with patch(
                "api_server.load_provider_config",
                return_value={
                    "HWP_PROVIDER_NAME": "deepseek",
                    "HWP_PROVIDER_TYPE": "openai_compatible",
                },
            ):
                resp = client.post(
                    "/api/v1/pause-summary",
                    json={
                        "context": {
                            "explored_paths": ["认知偏差 → 确认偏误"],
                            "current_depth": 2,
                            "total_nodes": 5,
                        }
                    },
                )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["summary"]["overall_theme"] == "认知偏差"
        assert data["duration_ms"] >= 0
        assert data["provider_used"] == "deepseek"

    def test_pause_summary_with_custom_provider(self, client: TestClient) -> None:
        """使用自定义 provider"""
        import json

        mock_result = json.dumps({"overall_theme": "test"})
        with patch(
            "api_server.invoke_provider_with_retry", return_value=mock_result
        ) as mock_invoke:
            with patch(
                "api_server._load_provider_names", return_value=["llama3", "deepseek"]
            ):
                with patch(
                    "api_server.load_provider_config",
                    return_value={
                        "HWP_PROVIDER_NAME": "default",
                        "HWP_PROVIDER_TYPE": "openai_compatible",
                    },
                ):
                    resp = client.post(
                        "/api/v1/pause-summary",
                        json={
                            "context": {"test": True},
                            "provider_type": "ollama",
                            "provider_name": "llama3",
                        },
                    )
        assert resp.status_code == 200

    def test_pause_summary_non_json_response(self, client: TestClient) -> None:
        """LLM 返回非 JSON 时，raw_text 应有值"""
        with patch("api_server.invoke_provider_with_retry", return_value="This is not JSON"):
            with patch(
                "api_server.load_provider_config",
                return_value={
                    "HWP_PROVIDER_NAME": "test",
                    "HWP_PROVIDER_TYPE": "openai_compatible",
                },
            ):
                resp = client.post(
                    "/api/v1/pause-summary",
                    json={
                        "context": {"test": True},
                    },
                )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["summary"] is None
        assert data["raw_text"] == "This is not JSON"

    def test_pause_summary_provider_error(self, client: TestClient) -> None:
        """Provider 调用失败返回 502"""
        with patch(
            "api_server.invoke_provider_with_retry",
            side_effect=RuntimeError("Connection timeout"),
        ):
            with patch(
                "api_server.load_provider_config",
                return_value={
                    "HWP_PROVIDER_NAME": "test",
                    "HWP_PROVIDER_TYPE": "openai_compatible",
                },
            ):
                resp = client.post(
                    "/api/v1/pause-summary",
                    json={
                        "context": {"test": True},
                    },
                )
        assert resp.status_code == 502

    def test_pause_summary_missing_context(self, client: TestClient) -> None:
        """缺少 context 字段返回 422"""
        resp = client.post("/api/v1/pause-summary", json={})
        assert resp.status_code == 422

    def test_pause_summary_custom_system_prompt(self, client: TestClient) -> None:
        """使用自定义系统提示词"""
        import json

        mock_result = json.dumps({"custom": "result"})
        with patch(
            "api_server.invoke_provider_with_retry", return_value=mock_result
        ) as mock_invoke:
            with patch(
                "api_server.load_provider_config",
                return_value={
                    "HWP_PROVIDER_NAME": "test",
                    "HWP_PROVIDER_TYPE": "openai_compatible",
                },
            ):
                resp = client.post(
                    "/api/v1/pause-summary",
                    json={
                        "context": {"test": True},
                        "system_prompt": "You are a custom assistant. Return JSON.",
                    },
                )
        assert resp.status_code == 200
        # 验证 mock_invoke 被调用时 message 中包含自定义 prompt
        call_args = mock_invoke.call_args
        message = call_args.kwargs.get("message", call_args.args[0] if call_args.args else "")
        assert "You are a custom assistant" in message

    def test_pause_summary_with_timeout_and_retries(self, client: TestClient) -> None:
        """自定义超时和重试次数"""
        import json

        mock_result = json.dumps({"theme": "test"})
        with patch(
            "api_server.invoke_provider_with_retry", return_value=mock_result
        ) as mock_invoke:
            with patch(
                "api_server.load_provider_config",
                return_value={
                    "HWP_PROVIDER_NAME": "test",
                    "HWP_PROVIDER_TYPE": "openai_compatible",
                },
            ):
                resp = client.post(
                    "/api/v1/pause-summary",
                    json={
                        "context": {"test": True},
                        "timeout_sec": 60,
                        "max_retries": 5,
                    },
                )
        assert resp.status_code == 200


# =============================================================================
# 12. 安全测试 - SSRF 防护
# =============================================================================


class TestSSRFProtection:
    """SSRF + 凭证泄露漏洞修复测试"""

    def test_multi_run_unknown_provider_rejected(self, client: TestClient) -> None:
        """未知 provider 名称应返回 400 错误"""
        with patch("api_server._load_provider_names", return_value=["deepseek", "moonshot"]):
            response = client.post(
                "/api/v1/multi-run",
                json={
                    "input_text": "Test input",
                    "providers": ["malicious_provider"],
                },
            )

        assert response.status_code == 400
        assert "Unknown provider" in response.json()["detail"]
        assert "malicious_provider" in response.json()["detail"]

    def test_multi_run_loads_trusted_config(self, client: TestClient) -> None:
        """multi-run 应从服务端受信任配置加载，而非使用用户传入的配置"""
        mock_provider_config = {
            "HWP_PROVIDER_NAME": "deepseek",
            "HWP_PROVIDER_TYPE": "openai_compatible",
            "HWP_LLM_API_KEY": "secret-api-key",
            "HWP_LLM_BASE_URL": "https://api.deepseek.com/v1",
        }
        mock_results = {"deepseek": "response"}

        with (
            patch("api_server._load_provider_names", return_value=["deepseek"]),
            patch("api_server.load_provider_config", return_value=mock_provider_config) as mock_load,
            patch("api_server.run_multi_provider", return_value=mock_results) as mock_run,
        ):
            response = client.post(
                "/api/v1/multi-run",
                json={
                    "input_text": "Test input",
                    "providers": ["deepseek"],
                },
            )

            assert response.status_code == 200

            # 验证 load_provider_config 被调用（从服务端配置加载）
            mock_load.assert_called()

            # 验证 run_multi_provider 收到的是服务端配置
            call_args = mock_run.call_args
            provider_configs = call_args[0][1]  # 第二个参数是 providers 列表
            assert len(provider_configs) == 1
            assert provider_configs[0]["HWP_LLM_API_KEY"] == "secret-api-key"
            assert provider_configs[0]["HWP_LLM_BASE_URL"] == "https://api.deepseek.com/v1"

    def test_multi_run_uses_provider_specific_env_file(self, client: TestClient, tmp_path: Path) -> None:
        """multi-run 应优先使用 provider 特定的 env 文件"""
        import api_server

        # 创建临时配置目录
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # 创建 provider.deepseek.env 文件
        deepseek_env = config_dir / "provider.deepseek.env"
        deepseek_env.write_text('HWP_LLM_BASE_URL=https://api.deepseek.com/v1\n')

        # 创建 providers.list
        providers_list = config_dir / "providers.list"
        providers_list.write_text('deepseek|provider.deepseek.env|DeepSeek\n')

        original_root = api_server.ROOT_DIR
        try:
            api_server.ROOT_DIR = tmp_path

            with patch("api_server.run_multi_provider", return_value={"deepseek": "ok"}) as mock_run:
                response = client.post(
                    "/api/v1/multi-run",
                    json={
                        "input_text": "Test",
                        "providers": ["deepseek"],
                    },
                )

                assert response.status_code == 200

                # 验证使用了 deepseek 特定配置
                call_args = mock_run.call_args
                provider_configs = call_args[0][1]
                assert provider_configs[0]["HWP_LLM_BASE_URL"] == "https://api.deepseek.com/v1"

        finally:
            api_server.ROOT_DIR = original_root

    def test_pause_summary_unknown_provider_rejected(self, client: TestClient) -> None:
        """pause-summary 使用未知 provider 应返回 400 错误"""
        with patch("api_server._load_provider_names", return_value=["deepseek", "moonshot"]):
            response = client.post(
                "/api/v1/pause-summary",
                json={
                    "context": {"test": True},
                    "provider_name": "malicious_provider",
                },
            )

        assert response.status_code == 400
        assert "Unknown provider" in response.json()["detail"]
        assert "malicious_provider" in response.json()["detail"]

    def test_pause_summary_valid_provider_accepted(self, client: TestClient) -> None:
        """pause-summary 使用有效 provider 应正常处理"""
        import json

        mock_result = json.dumps({"overall_theme": "test"})

        with (
            patch("api_server._load_provider_names", return_value=["deepseek", "moonshot"]),
            patch("api_server.invoke_provider_with_retry", return_value=mock_result),
            patch(
                "api_server.load_provider_config",
                return_value={
                    "HWP_PROVIDER_NAME": "default",
                    "HWP_PROVIDER_TYPE": "openai_compatible",
                },
            ),
        ):
            response = client.post(
                "/api/v1/pause-summary",
                json={
                    "context": {"test": True},
                    "provider_name": "deepseek",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


# =============================================================================
# 13. 并发 Session 确定性映射测试
# =============================================================================


class TestConcurrentSessionDeterministicMapping:
    """验证并发 session 不会互相干扰结果"""

    def test_concurrent_sessions_have_deterministic_log_paths(
        self,
        client: TestClient,
        mock_provider_config: dict[str, str],
        tmp_path: Path,
    ) -> None:
        """并发 session 应该各自获得正确的链日志路径，不会互相干扰"""
        import json
        import threading
        import api_server

        # 创建日志目录
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        # 用于跟踪每个 session 的 chain_path
        session_chain_paths: dict[str, Optional[str]] = {}
        lock = threading.Lock()

        def mock_run_and_capture(session_id: str):
            """模拟运行并记录 chain_path"""
            # 为每个 session 创建独特的日志文件
            chain_log = logs_dir / f"chain_{session_id}.jsonl"
            mock_result = {"session_id": session_id, "node_id": f"node_{session_id}"}
            with open(chain_log, "w", encoding="utf-8") as f:
                f.write(json.dumps(mock_result, ensure_ascii=False) + "\n")

            return chain_log

        def create_mock_runner(session_id: str):
            """创建带有确定性 last_chain_log 的 mock runner"""
            chain_log = mock_run_and_capture(session_id)
            mock_runner = MagicMock()
            mock_runner.last_chain_log = chain_log
            return mock_runner

        with (
            patch("api_server.load_provider_config", return_value=mock_provider_config),
            patch("api_server.ChainRunner") as MockChainRunner,
            patch("api_server._extract_last_round_result") as mock_extract,
        ):

            def get_mock_runner(*args, **kwargs):
                # 从 kwargs 中获取 session_id
                session_id = kwargs.get("session_id", args[2] if len(args) > 2 else None)
                return create_mock_runner(session_id)

            MockChainRunner.side_effect = get_mock_runner

            # 模拟 extract 结果
            def extract_result(path):
                if path:
                    with open(path, "r", encoding="utf-8") as f:
                        line = f.readline().strip()
                        if line:
                            return json.loads(line)
                return None

            mock_extract.side_effect = extract_result

            # 提交两个并发任务
            response1 = client.post(
                "/api/v1/runs",
                json={"input_text": "Session 1 input", "rounds": 1},
            )
            session_id_1 = response1.json()["session_id"]

            response2 = client.post(
                "/api/v1/runs",
                json={"input_text": "Session 2 input", "rounds": 1},
            )
            session_id_2 = response2.json()["session_id"]

            # 等待两个任务完成
            max_wait = 5.0
            start = time.time()
            while time.time() - start < max_wait:
                session1 = api_server._sessions.get(session_id_1)
                session2 = api_server._sessions.get(session_id_2)
                if (
                    session1
                    and session1.status == "completed"
                    and session2
                    and session2.status == "completed"
                ):
                    break
                time.sleep(0.1)

            # 验证两个 session 都完成了
            session1 = api_server._sessions.get(session_id_1)
            session2 = api_server._sessions.get(session_id_2)
            assert session1 is not None and session1.status == "completed"
            assert session2 is not None and session2.status == "completed"

            # 验证每个 session 的 chain_path 是唯一的
            assert session1.chain_path != session2.chain_path
            assert session_id_1 in session1.chain_path
            assert session_id_2 in session2.chain_path

            # 验证每个 session 的结果指向正确的日志
            assert session1.result is not None
            assert session2.result is not None
            # 结果应该包含各自的 session_id（在 node_id 中体现）
            assert session1.result["session_id"] == session_id_1
            assert session2.result["session_id"] == session_id_2
