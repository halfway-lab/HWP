#!/usr/bin/env python3
"""HWP FastAPI Server - REST API 服务层

提供链运行的异步提交、状态查询、结果获取等功能。
支持多 Provider 并行调用和 API Key 认证。

运行方式:
    python3 api_server.py
    或
    uvicorn api_server:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# =============================================================================
# HWP Core Imports
# =============================================================================

from hwp_protocol.runner import (
    ChainRunner,
    RunnerConfig,
    invoke_provider_with_retry,
    load_controller_config,
    load_provider_config,
    run_multi_provider,
)


# =============================================================================
# Configuration
# =============================================================================

ROOT_DIR = Path(__file__).resolve().parent
HWP_API_KEY = os.environ.get("HWP_API_KEY", "")
HWP_VERSION = "0.6.2"

# Thread pool for background execution
_executor = ThreadPoolExecutor(max_workers=4)


# =============================================================================
# Pydantic Models
# =============================================================================


class RunRequest(BaseModel):
    """链运行请求模型"""

    input_text: str = Field(..., description="输入文本（prompt）")
    provider_type: Optional[str] = Field(None, description="Provider 类型")
    provider_name: Optional[str] = Field(None, description="Provider 名称")
    rounds: int = Field(8, ge=1, le=100, description="每链轮次数")
    timeout_sec: float = Field(0.0, ge=0.0, description="链超时秒数，0 表示无超时")
    sleep_sec: float = Field(2.0, ge=0.0, description="轮次间休眠秒数")


class RunResponse(BaseModel):
    """链运行提交响应"""

    session_id: str = Field(..., description="会话 ID")
    status: str = Field("queued", description="初始状态")


class RunStatusResponse(BaseModel):
    """链运行状态响应"""

    session_id: str = Field(..., description="会话 ID")
    status: str = Field(
        ..., description="运行状态: queued/running/completed/failed/cancelled"
    )
    current_round: int = Field(0, description="当前轮次")
    total_rounds: int = Field(8, description="总轮次数")
    started_at: Optional[float] = Field(None, description="开始时间戳")
    completed_at: Optional[float] = Field(None, description="完成时间戳")
    error: Optional[str] = Field(None, description="错误信息")


class RunResultResponse(BaseModel):
    """链运行结果响应"""

    session_id: str = Field(..., description="会话 ID")
    chain_path: Optional[str] = Field(None, description="链日志文件路径")
    last_round: Optional[dict[str, Any]] = Field(None, description="最后一轮结果")


class MultiRunRequest(BaseModel):
    """多 Provider 并行调用请求"""

    input_text: str = Field(..., description="输入文本（prompt）")
    providers: list[str] = Field(
        ...,
        description="Provider 名称列表（如 ['deepseek', 'moonshot']），从服务端受信任配置加载",
        examples=[["deepseek", "moonshot"]],
    )
    max_workers: Optional[int] = Field(None, ge=1, le=16, description="最大并行数")


class MultiRunResponse(BaseModel):
    """多 Provider 并行调用响应"""

    results: dict[str, str] = Field(..., description="Provider 名称到结果的映射")


class CancelResponse(BaseModel):
    """取消运行响应"""

    cancelled: bool = Field(True, description="是否成功取消")


class HealthResponse(BaseModel):
    """健康检查响应"""

    status: str = Field("ok", description="服务状态")
    version: str = Field(..., description="服务版本")


class ProvidersResponse(BaseModel):
    """Provider 列表响应"""

    providers: list[str] = Field(..., description="Provider 名称列表")


class PauseSummaryRequest(BaseModel):
    """暂停总结请求 — 接收探索树结构化上下文"""

    context: dict[str, Any] = Field(
        ...,
        description="探索树结构化上下文，包含 explored_paths, depth, focus_areas, unexplored_regions 等",
        examples=[
            {
                "explored_paths": [
                    "认知偏差 → 确认偏误 → 信息筛选",
                    "认知偏差 → 锚定效应",
                ],
                "current_depth": 3,
                "focus_areas": ["确认偏误的神经机制"],
                "unexplored_regions": ["可用性启发式", "代表性启发式"],
                "total_nodes": 12,
                "session_rounds": 5,
            }
        ],
    )
    system_prompt: Optional[str] = Field(
        None,
        description="自定义系统提示词。为空时使用默认暂停总结提示词",
    )
    provider_type: Optional[str] = Field(None, description="覆盖默认 Provider 类型")
    provider_name: Optional[str] = Field(None, description="覆盖默认 Provider 名称")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="LLM 温度参数")
    timeout_sec: int = Field(30, ge=5, le=300, description="调用超时秒数")
    max_retries: int = Field(3, ge=1, le=10, description="最大重试次数")


class PauseSummaryResponse(BaseModel):
    """暂停总结响应"""

    request_id: str = Field(..., description="请求唯一标识")
    status: str = Field(..., description="success 或 error")
    summary: Optional[dict[str, Any]] = Field(None, description="AI 生成的总结结果")
    raw_text: Optional[str] = Field(None, description="LLM 原始返回文本（解析失败时提供）")
    duration_ms: int = Field(..., description="调用耗时毫秒")
    provider_used: Optional[str] = Field(None, description="实际使用的 Provider")
    error_message: Optional[str] = Field(None, description="错误信息")


# =============================================================================
# Default System Prompts
# =============================================================================


_PAUSE_SUMMARY_SYSTEM_PROMPT = (
    "You are a cognitive exploration assistant. "
    "The user has been exploring a topic through a question tree and wants to pause. "
    "Based on the exploration context provided, generate a structured JSON summary with the following fields:\n"
    "{\n"
    '  "overall_theme": "the main topic being explored",\n'
    '  "progress_summary": "a concise summary of what has been explored so far",\n'
    '  "key_insights": ["insight1", "insight2", ...],\n'
    '  "depth_assessment": "how deep the exploration has gone and whether it is balanced",\n'
    '  "unexplored_suggestions": ["suggestion1", "suggestion2", ...],\n'
    '  "recommended_next_steps": ["step1", "step2", ...],\n'
    '  "exploration_completeness": 0.0 to 1.0\n'
    "}\n"
    "Return exactly one JSON object and nothing else. "
    "Do not wrap the JSON in Markdown fences."
)


# =============================================================================
# Session Management
# =============================================================================


_MAX_SESSIONS = 1000
_SESSION_TTL_SEC = 3600.0  # 1 hour


@dataclass
class SessionState:
    """运行会话状态"""

    session_id: str
    status: str = "queued"  # queued, running, completed, failed, cancelled
    current_round: int = 0
    total_rounds: int = 8
    chain_path: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    cancel_flag: threading.Event = field(default_factory=threading.Event)
    last_access_at: float = field(default_factory=time.time)


# In-memory session store
_sessions: dict[str, SessionState] = {}
_sessions_lock = threading.Lock()


def _cleanup_expired_sessions() -> None:
    """清理过期或超出上限的 session"""
    with _sessions_lock:
        now = time.time()
        # 先清理已完成/失败/取消且超过 TTL 的
        expired = [
            sid for sid, s in _sessions.items()
            if s.status in ("completed", "failed", "cancelled")
            and now - s.last_access_at > _SESSION_TTL_SEC
        ]
        for sid in expired:
            _sessions.pop(sid, None)

        # 如果仍超过上限，按 last_access_at 排序删除最旧的已终止 session
        if len(_sessions) > _MAX_SESSIONS:
            terminated = sorted(
                [(sid, s) for sid, s in _sessions.items() if s.status in ("completed", "failed", "cancelled")],
                key=lambda x: x[1].last_access_at,
            )
            while len(_sessions) > _MAX_SESSIONS and terminated:
                sid, _ = terminated.pop(0)
                _sessions.pop(sid, None)


# =============================================================================
# API Key Authentication
# =============================================================================


async def verify_api_key(request: Request) -> None:
    """验证 API Key

    如果 HWP_API_KEY 环境变量未设置，则跳过认证（开发模式）。
    否则，检查请求头中的 X-API-Key 是否匹配。
    """
    if not HWP_API_KEY:
        # Development mode: no API key required
        return

    key = request.headers.get("X-API-Key", "")
    if key != HWP_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


# =============================================================================
# Application Lifespan
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    yield
    # Shutdown: cleanup executor
    _executor.shutdown(wait=False)


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="HWP API Server",
    description="HWP Protocol REST API - 链编排运行时服务",
    version=HWP_VERSION,
    lifespan=lifespan,
)

# CORS Middleware
origins = os.environ.get("HWP_CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Background Task Functions
# =============================================================================


def _execute_chain(session: SessionState, request: RunRequest) -> None:
    """后台执行链运行任务

    Args:
        session: 会话状态对象
        request: 运行请求参数
    """
    session.status = "running"
    session.started_at = time.time()

    try:
        # Check cancellation
        if session.cancel_flag.is_set():
            session.status = "cancelled"
            session.completed_at = time.time()
            return

        # Load provider configuration
        provider_config = load_provider_config(ROOT_DIR)

        # Apply request overrides
        if request.provider_type:
            provider_config["HWP_PROVIDER_TYPE"] = request.provider_type
        if request.provider_name:
            provider_config["HWP_PROVIDER_NAME"] = request.provider_name

        # Build runner config
        runner_config = RunnerConfig(
            root_dir=ROOT_DIR,
            rounds_per_chain=request.rounds,
            round_sleep_sec=request.sleep_sec,
            chain_timeout_sec=request.timeout_sec,
            provider_type=request.provider_type or "",
            provider_name=request.provider_name or "",
        )

        # Create runner with session_id for deterministic log path
        runner = ChainRunner(runner_config, provider_config, session_id=session.session_id)

        # Write input to temporary file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as tmp_file:
            tmp_file.write(request.input_text)
            tmp_file_path = Path(tmp_file.name)

        try:
            # Execute chain
            runner.run_input_file(tmp_file_path)
        finally:
            # Cleanup temp file
            try:
                tmp_file_path.unlink()
            except Exception:
                pass

        # Check cancellation after run
        if session.cancel_flag.is_set():
            session.status = "cancelled"
            session.completed_at = time.time()
            return

        # Use deterministic log path from runner, fallback to scan
        if runner.last_chain_log and runner.last_chain_log.exists():
            session.chain_path = str(runner.last_chain_log)
        else:
            session.chain_path = _find_latest_chain_log(session.session_id)
        session.result = _extract_last_round_result(session.chain_path)
        session.status = "completed"
        session.current_round = request.rounds
        session.completed_at = time.time()

    except Exception as exc:
        session.status = "failed"
        session.error = str(exc)
        session.completed_at = time.time()


def _find_latest_chain_log(session_id: str) -> Optional[str]:
    """查找最新的链日志文件

    Args:
        session_id: 会话 ID（用于辅助查找，但实际通过文件修改时间查找）

    Returns:
        最新的链日志文件路径，或 None
    """
    logs_dir = ROOT_DIR / "logs"
    if not logs_dir.exists():
        return None

    chain_logs = list(logs_dir.glob("chain_*.jsonl"))
    if not chain_logs:
        return None

    # Sort by modification time, get the most recent
    latest = max(chain_logs, key=lambda p: p.stat().st_mtime)
    return str(latest)


def _extract_last_round_result(chain_path: Optional[str]) -> Optional[dict]:
    """从链日志文件中提取最后一轮结果

    Args:
        chain_path: 链日志文件路径

    Returns:
        最后一轮的 JSON 数据，或 None
    """
    if not chain_path:
        return None

    try:
        path = Path(chain_path)
        if not path.exists():
            return None

        # Read all lines and get the last one
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if not lines:
            return None

        last_line = lines[-1].strip()
        if not last_line:
            return None

        return json.loads(last_line)
    except Exception:
        return None


# =============================================================================
# API Endpoints - Runs
# =============================================================================


@app.post(
    "/api/v1/runs",
    response_model=RunResponse,
    summary="提交链运行",
    description="异步提交一个新的链运行任务，立即返回会话 ID。",
    tags=["runs"],
)
async def create_run(
    request: RunRequest, _: None = Depends(verify_api_key)
) -> RunResponse:
    """提交链运行任务

    生成唯一的 session_id，创建会话状态，并提交后台执行任务。
    """
    _cleanup_expired_sessions()
    session_id = str(uuid.uuid4())

    session = SessionState(
        session_id=session_id,
        status="queued",
        total_rounds=request.rounds,
    )
    with _sessions_lock:
        _sessions[session_id] = session

    # Submit to executor
    _executor.submit(_execute_chain, session, request)

    return RunResponse(session_id=session_id, status="queued")


@app.get(
    "/api/v1/runs/{session_id}",
    response_model=RunStatusResponse,
    summary="查询运行状态",
    description="根据 session_id 查询链运行的状态。",
    tags=["runs"],
)
async def get_run_status(
    session_id: str, _: None = Depends(verify_api_key)
) -> RunStatusResponse:
    """查询链运行状态"""
    with _sessions_lock:
        session = _sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        session.last_access_at = time.time()

    return RunStatusResponse(
        session_id=session.session_id,
        status=session.status,
        current_round=session.current_round,
        total_rounds=session.total_rounds,
        started_at=session.started_at,
        completed_at=session.completed_at,
        error=session.error,
    )


@app.get(
    "/api/v1/runs/{session_id}/result",
    response_model=RunResultResponse,
    summary="获取运行结果",
    description="获取已完成链运行的结果。仅当状态为 completed 时可用。",
    tags=["runs"],
)
async def get_run_result(
    session_id: str, _: None = Depends(verify_api_key)
) -> RunResultResponse:
    """获取链运行结果"""
    with _sessions_lock:
        session = _sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        session.last_access_at = time.time()

    if session.status != "completed":
        raise HTTPException(
            status_code=409, detail="Run not completed yet"
        )

    return RunResultResponse(
        session_id=session.session_id,
        chain_path=session.chain_path,
        last_round=session.result,
    )


@app.delete(
    "/api/v1/runs/{session_id}",
    response_model=CancelResponse,
    summary="取消运行",
    description="取消正在运行或排队中的链运行任务。",
    tags=["runs"],
)
async def cancel_run(
    session_id: str, _: None = Depends(verify_api_key)
) -> CancelResponse:
    """取消链运行"""
    with _sessions_lock:
        session = _sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        session.last_access_at = time.time()

    # Set cancel flag
    session.cancel_flag.set()

    # Update status if still queued or running
    if session.status in ("queued", "running"):
        session.status = "cancelled"
        session.completed_at = time.time()

    return CancelResponse(cancelled=True)


# =============================================================================
# Provider Name Validation (Security)
# =============================================================================


def _load_provider_names() -> list[str]:
    """从 config/providers.list 加载可用的 provider 名称列表（白名单）

    Returns:
        Provider 名称列表，如 ['deepseek', 'moonshot', 'ollama']
    """
    providers_path = ROOT_DIR / "config" / "providers.list"
    providers: list[str] = []

    if not providers_path.exists():
        return providers

    try:
        with open(providers_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                # Format: provider_name|env_file|description
                parts = line.split("|")
                if parts:
                    provider_name = parts[0].strip()
                    if provider_name:
                        providers.append(provider_name)
    except Exception:
        pass

    return providers


# =============================================================================
# API Endpoints - Multi-Provider
# =============================================================================


@app.post(
    "/api/v1/multi-run",
    response_model=MultiRunResponse,
    summary="多 Provider 并行调用",
    description="并行调用多个 Provider，适用于 benchmark 和对比测试场景。Provider 配置从服务端受信任配置加载。",
    tags=["runs"],
)
async def multi_run(
    request: MultiRunRequest, _: None = Depends(verify_api_key)
) -> MultiRunResponse:
    """多 Provider 并行调用

    安全说明：Provider 名称必须在 config/providers.list 白名单中，
    配置从服务端的 config/provider.{name}.env 文件加载，
    防止 SSRF 和凭证泄露攻击。

    这是同步操作，会阻塞直到所有 Provider 调用完成。
    """
    import asyncio
    from functools import partial

    # 加载可用 provider 列表（用于白名单校验）
    available = _load_provider_names()

    # 构建安全的 provider 配置列表
    provider_configs: list[dict[str, str]] = []
    for name in request.providers:
        # 白名单校验
        if name not in available:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown provider: {name}. Available providers: {available}",
            )

        # 从受信任的服务端配置加载
        provider_env = ROOT_DIR / "config" / f"provider.{name}.env"
        if provider_env.exists():
            config = load_provider_config(ROOT_DIR, provider_env)
        else:
            # 使用默认配置，覆盖 provider name
            config = load_provider_config(ROOT_DIR)
            config["HWP_PROVIDER_NAME"] = name

        provider_configs.append(config)

    # Build runner config for multi-provider
    runner_config = RunnerConfig(
        root_dir=ROOT_DIR,
        agent_max_retries=3,
        agent_timeout_sec=30,
    )

    # Run in thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(
        None,
        partial(
            run_multi_provider,
            request.input_text,
            provider_configs,
            runner_config,
            request.max_workers,
        ),
    )

    return MultiRunResponse(results=results)


# =============================================================================
# API Endpoints - Configuration
# =============================================================================


@app.get(
    "/api/v1/config/controller",
    summary="获取控制器配置",
    description="返回当前加载的控制器配置，包括模式、阈值等。",
    tags=["config"],
)
async def get_controller_config(_: None = Depends(verify_api_key)) -> dict[str, Any]:
    """获取控制器配置"""
    return load_controller_config()


@app.get(
    "/api/v1/providers",
    response_model=ProvidersResponse,
    summary="列出可用 Provider",
    description="从 config/providers.list 读取可用的 Provider 列表。",
    tags=["config"],
)
async def list_providers(_: None = Depends(verify_api_key)) -> ProvidersResponse:
    """列出可用的 Provider"""
    providers_path = ROOT_DIR / "config" / "providers.list"
    providers: list[str] = []

    if not providers_path.exists():
        return ProvidersResponse(providers=providers)

    try:
        with open(providers_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                # Format: provider_name|env_file|description
                parts = line.split("|")
                if parts:
                    provider_name = parts[0].strip()
                    if provider_name:
                        providers.append(provider_name)
    except Exception:
        pass

    return ProvidersResponse(providers=providers)


# =============================================================================
# API Endpoints - Summary
# =============================================================================


@app.post(
    "/api/v1/pause-summary",
    response_model=PauseSummaryResponse,
    tags=["summary"],
    summary="暂停总结",
    description="接收探索树结构化上下文，调用 LLM 生成暂停时的总结报告",
)
async def pause_summary(
    request: PauseSummaryRequest,
    _: None = Depends(verify_api_key),
) -> PauseSummaryResponse:
    """暂停总结端点

    接收探索树结构化上下文，调用 LLM 生成暂停时的总结报告。
    """
    import asyncio

    request_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        # 白名单校验 provider_name（如果指定）
        if request.provider_name:
            available = _load_provider_names()
            if request.provider_name not in available:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown provider: {request.provider_name}. Available providers: {available}",
                )

        # 加载 provider 配置
        provider_config = load_provider_config(ROOT_DIR)

        # 应用请求覆盖
        if request.provider_type:
            provider_config["HWP_PROVIDER_TYPE"] = request.provider_type
        if request.provider_name:
            provider_config["HWP_PROVIDER_NAME"] = request.provider_name
        if request.temperature is not None:
            provider_config["HWP_LLM_TEMPERATURE"] = str(request.temperature)

        # 构建 RunnerConfig（仅用于重试和超时配置）
        runner_config = RunnerConfig(
            root_dir=ROOT_DIR,
            agent_max_retries=request.max_retries,
            agent_timeout_sec=request.timeout_sec,
        )

        # 构建发送给 LLM 的消息
        system_prompt = request.system_prompt or _PAUSE_SUMMARY_SYSTEM_PROMPT
        user_message = (
            f"{system_prompt}\n\n"
            f"## Exploration Context\n\n"
            f"```json\n{json.dumps(request.context, ensure_ascii=False, indent=2)}\n```"
        )

        # 在线程池中执行同步的 LLM 调用（避免阻塞事件循环）
        loop = asyncio.get_event_loop()
        result_text = await loop.run_in_executor(
            _executor,
            lambda: invoke_provider_with_retry(
                message=user_message,
                session_id=request_id,
                round_num=1,
                runner_config=runner_config,
                provider_config=provider_config,
            ),
        )

        duration_ms = int((time.time() - start_time) * 1000)
        provider_used = provider_config.get("HWP_PROVIDER_NAME", "unknown")

        # 尝试解析为 JSON
        try:
            summary = json.loads(result_text)
            return PauseSummaryResponse(
                request_id=request_id,
                status="success",
                summary=summary,
                duration_ms=duration_ms,
                provider_used=provider_used,
            )
        except (json.JSONDecodeError, TypeError):
            # JSON 解析失败，返回原始文本
            return PauseSummaryResponse(
                request_id=request_id,
                status="success",
                summary=None,
                raw_text=result_text,
                duration_ms=duration_ms,
                provider_used=provider_used,
            )

    except HTTPException:
        # 重新抛出 HTTPException（如白名单校验失败）
        raise
    except Exception as exc:
        duration_ms = int((time.time() - start_time) * 1000)
        raise HTTPException(
            status_code=502,
            detail={
                "request_id": request_id,
                "status": "error",
                "error_message": str(exc),
                "duration_ms": duration_ms,
            },
        )


# =============================================================================
# API Endpoints - Health
# =============================================================================


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="健康检查",
    description="检查服务是否正常运行（无需认证）。",
    tags=["system"],
)
async def health_check() -> HealthResponse:
    """健康检查端点"""
    return HealthResponse(status="ok", version=HWP_VERSION)


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("HWP_HOST", "0.0.0.0")
    port = int(os.environ.get("HWP_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
