#!/usr/bin/env python3
"""HWP Python Runner - 链编排运行时

将 runs/run_sequential.sh 的核心链编排逻辑转为 Python 实现，
消除 Shell-Python 跨进程边界开销。

零第三方依赖，仅使用 Python 3.9+ 标准库。
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import random
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# Import transform functions directly (no subprocess)
from hwp_protocol.transform import enrich_inner_json, repack_result_with_inner


# =============================================================================
# Configuration Classes
# =============================================================================

@dataclass
class RunnerConfig:
    """Runner 配置数据类"""

    root_dir: Path
    rounds_per_chain: int = 8
    round_sleep_sec: float = 2.0
    chain_timeout_sec: float = 0.0
    replay_chain_path: Optional[Path] = None
    provider_type: str = ""
    provider_name: str = ""
    agent_cmd: str = ""
    agent_bin: str = "openclaw"
    agent_max_retries: int = 3
    agent_timeout_sec: int = 30
    dry_run: bool = False


@dataclass
class ChainState:
    """链状态管理 - 每轮次的状态跟踪"""

    prev_entropy: float = 0.70
    prev_drift: float = 0.00
    prev_collapse: bool = False
    prev_recovery: bool = False
    parent_vars: list = field(default_factory=list)
    parent_node: Optional[str] = None
    parent_recovery: bool = False
    is_probe: bool = False


# =============================================================================
# Dynamic Controller
# =============================================================================

# Built-in default configuration (used when config file not found)
_CONTROLLER_DEFAULTS = {
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
        "variable_policy": {"keep_n": 20, "new_n": 10, "max_vars": 30},
    },
}

# Module-level cached config
_controller_config: Optional[dict[str, Any]] = None


def load_controller_config(config_path: Optional[Path] = None) -> dict[str, Any]:
    """Load controller configuration from JSON file.

    Args:
        config_path: Optional path to config file. Defaults to config/controller.json.

    Returns:
        Configuration dict with modes, thresholds, and defaults.

    Priority:
        1. Environment variables (HWP_DRIFT_LOW_THRESHOLD, HWP_DRIFT_HIGH_THRESHOLD)
        2. JSON config file (config/controller.json)
        3. Built-in defaults
    """
    global _controller_config

    if _controller_config is not None:
        return _controller_config

    # Start with built-in defaults
    config = dict(_CONTROLLER_DEFAULTS)

    # Determine config file path
    if config_path is None:
        config_path = Path(__file__).resolve().parent.parent / "config" / "controller.json"

    # Load from file if exists
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                file_config = json.load(f)
                # Merge file config into defaults
                if "modes" in file_config:
                    config["modes"] = file_config["modes"]
                if "thresholds" in file_config:
                    config["thresholds"].update(file_config["thresholds"])
                if "defaults" in file_config:
                    config["defaults"].update(file_config["defaults"])
                if "version" in file_config:
                    config["version"] = file_config["version"]
        except (json.JSONDecodeError, OSError):
            pass  # Use defaults on error

    # Environment variable overrides for thresholds
    env_drift_low = os.environ.get("HWP_DRIFT_LOW_THRESHOLD", "").strip()
    env_drift_high = os.environ.get("HWP_DRIFT_HIGH_THRESHOLD", "").strip()

    if env_drift_low:
        try:
            config["thresholds"]["drift_low"] = float(env_drift_low)
        except ValueError:
            pass

    if env_drift_high:
        try:
            config["thresholds"]["drift_high"] = float(env_drift_high)
        except ValueError:
            pass

    _controller_config = config
    return config


def get_drift_thresholds() -> tuple[float, float]:
    """Get drift thresholds from config.

    Returns:
        Tuple of (drift_low, drift_high)
    """
    config = load_controller_config()
    thresholds = config.get("thresholds", {})
    drift_low = thresholds.get("drift_low", 0.30)
    drift_high = thresholds.get("drift_high", 0.70)
    return drift_low, drift_high


def compute_mode(
    round_num: int,
    is_probe: bool,
    prev_entropy: float,
    prev_drift: float,
    prev_collapse: bool,
    prev_recovery: bool,
) -> str:
    """计算当前轮次的模式 (Rg0/Rg1/Rg2)

    SPEC-COMPLIANT (per hwp_turn_prompt.txt line 162-168):
    - Rg0 = Normal mode (drift_low <= drift_rate <= drift_high)
    - Rg1 = Stable mode (drift_rate < drift_low)
    - Rg2 = Explore mode (drift_rate > drift_high)

    Thresholds are loaded from config/controller.json and can be overridden
    via HWP_DRIFT_LOW_THRESHOLD and HWP_DRIFT_HIGH_THRESHOLD environment variables.
    """
    if round_num == 1:
        return "Rg0"

    # Stabilize immediately after collapse/recovery
    if prev_collapse or prev_recovery:
        return "Rg0"

    # Get thresholds from config
    drift_low, drift_high = get_drift_thresholds()

    # Stable mode: low drift rate (< drift_low)
    if prev_drift < drift_low:
        return "Rg1"

    # Explore mode: high drift rate (> drift_high)
    if prev_drift > drift_high:
        return "Rg2"

    # Normal mode: medium drift rate (drift_low <= drift <= drift_high)
    return "Rg0"


def compute_band(mode: str) -> tuple[float, float]:
    """计算熵目标区间 (min, max)

    Entropy target bands loaded from config/controller.json.
    Falls back to defaults if mode not found.
    """
    config = load_controller_config()
    modes = config.get("modes", {})

    if mode in modes:
        mode_config = modes[mode]
        entropy_target = mode_config.get("entropy_target", {})
        min_val = entropy_target.get("min", 0.40)
        max_val = entropy_target.get("max", 0.79)
        return (min_val, max_val)

    # Default to Rg0 band
    return (0.40, 0.79)


def emit_hint_json(
    mode: str, min_val: float, max_val: float, keep_n: int, new_n: int, max_vars: int
) -> dict[str, Any]:
    """生成 RHYTHM_HINT JSON 对象"""
    return {
        "mode": mode,
        "entropy_target": {"min": min_val, "max": max_val},
        "variable_policy": {
            "keep_n": keep_n,
            "new_n": new_n,
            "max_vars": max_vars,
            "keep_prefix": True,
        },
    }


# =============================================================================
# Provider Configuration Loading
# =============================================================================

def parse_env_file(config_path: Path) -> dict[str, str]:
    """解析简单的 KEY=VALUE 格式 .env 文件（不用 dotenv）"""
    env_vars: dict[str, str] = {}
    if not config_path.exists():
        return env_vars

    with open(config_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue

            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()

            # Remove quotes if present
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]

            if key:
                env_vars[key] = value

    return env_vars


def resolve_provider_alias(provider_type: str, provider_name: str) -> str:
    """解析 provider 别名到标准类型"""
    normalized_type = (provider_type or "").lower()
    normalized_name = (provider_name or "").lower()

    if not normalized_type:
        return ""

    if normalized_type in ("openclaw", "claw"):
        return "openclaw"
    if normalized_type == "ollama":
        return "ollama"
    if normalized_type in ("openai", "openai_compatible", "compatible", "llm_api", "api"):
        return "openai_compatible"
    if normalized_type == "custom":
        return "custom"

    # Check provider name for known types
    if normalized_name in (
        "openrouter",
        "deepseek",
        "moonshot",
        "kimi",
        "siliconflow",
        "together",
        "fireworks",
        "groq",
        "perplexity",
        "xai",
        "azure_openai",
    ):
        return "openai_compatible"
    if normalized_name == "ollama":
        return "ollama"
    if normalized_name == "openclaw":
        return "openclaw"

    return normalized_type


def load_provider_config(root_dir: Path, cli_config: Optional[Path] = None) -> dict[str, str]:
    """加载 provider 配置，优先级：环境变量 > .env 文件"""
    config: dict[str, str] = {}

    # Load from .env file first (lowest priority)
    config_path = cli_config or root_dir / "config" / "provider.env"
    file_config = parse_env_file(config_path)
    config.update(file_config)

    # Override with environment variables
    env_mappings = {
        "HWP_PROVIDER_TYPE": "HWP_PROVIDER_TYPE",
        "HWP_PROVIDER_NAME": "HWP_PROVIDER_NAME",
        "HWP_LLM_MODEL": "HWP_LLM_MODEL",
        "HWP_LLM_API_KEY": "HWP_LLM_API_KEY",
        "HWP_LLM_BASE_URL": "HWP_LLM_BASE_URL",
        "HWP_AGENT_BIN": "HWP_AGENT_BIN",
        "HWP_AGENT_CMD": "HWP_AGENT_CMD",
        "HWP_REPLAY_CHAIN_PATH": "HWP_REPLAY_CHAIN_PATH",
        "HWP_AGENT_MAX_RETRIES": "HWP_AGENT_MAX_RETRIES",
        "HWP_AGENT_TIMEOUT": "HWP_AGENT_TIMEOUT",
        "HWP_ROUND_SLEEP_SEC": "HWP_ROUND_SLEEP_SEC",
        "HWP_CHAIN_TIMEOUT_SEC": "HWP_CHAIN_TIMEOUT_SEC",
        "OLLAMA_MODEL": "OLLAMA_MODEL",
        "OLLAMA_BASE_URL": "OLLAMA_BASE_URL",
        # Fallback env vars
        "OPENAI_API_KEY": "OPENAI_API_KEY",
        "OPENAI_MODEL": "OPENAI_MODEL",
        "OPENAI_BASE_URL": "OPENAI_BASE_URL",
    }

    for env_key, config_key in env_mappings.items():
        value = os.environ.get(env_key, "").strip()
        if value:
            config[config_key] = value

    return config


def _get_config_value(provider_config: dict[str, str], *keys: str, default: str = "") -> str:
    """从 provider_config 字典查找配置值，再回退到 os.environ

    Args:
        provider_config: provider 配置字典
        *keys: 配置键名列表，按优先级排序
        default: 默认值

    Returns:
        第一个非空配置值，或默认值
    """
    for k in keys:
        # 先从 provider_config 字典查找
        if k in provider_config and provider_config[k].strip():
            return provider_config[k].strip()
        # 再从 os.environ 查找
        v = os.environ.get(k, "").strip()
        if v:
            return v
    return default


def _require_config_value(provider_config: dict[str, str], *keys: str) -> str:
    """从 provider_config 字典查找配置值，缺少时抛出 RuntimeError

    Args:
        provider_config: provider 配置字典
        *keys: 配置键名列表，按优先级排序

    Returns:
        第一个非空配置值

    Raises:
        RuntimeError: 所有键都没有找到非空值
    """
    value = _get_config_value(provider_config, *keys, default="")
    if value:
        return value
    raise RuntimeError(f"missing required configuration: one of {', '.join(keys)}")


def apply_provider_defaults(config: dict[str, str], root_dir: Path) -> dict[str, str]:
    """应用 provider 默认值，设置 agent_cmd"""
    result = dict(config)

    resolved_type = resolve_provider_alias(
        result.get("HWP_PROVIDER_TYPE", ""), result.get("HWP_PROVIDER_NAME", "")
    )

    # Skip if replay mode or agent_cmd already set
    if result.get("HWP_REPLAY_CHAIN_PATH") or result.get("HWP_AGENT_CMD"):
        return result

    if resolved_type == "openai_compatible":
        result[
            "HWP_AGENT_CMD"
        ] = f"python3 {root_dir}/adapters/openai_compatible_adapter.py"
    elif resolved_type == "ollama":
        result["HWP_AGENT_CMD"] = f"python3 {root_dir}/adapters/ollama_adapter.py"
    elif resolved_type == "openclaw":
        if not result.get("HWP_AGENT_BIN"):
            result["HWP_AGENT_BIN"] = "openclaw"

    return result


# =============================================================================
# Provider Adapter Integration
# =============================================================================

def import_and_call_openai_adapter(
    message: str, session_id: str, round_num: int, provider_config: dict[str, str]
) -> str:
    """直接导入并调用 OpenAI 兼容 adapter（避免子进程）

    Args:
        message: 输入消息
        session_id: 会话 ID
        round_num: 轮次号
        provider_config: provider 配置字典（优先于 os.environ）
    """
    # Add adapters directory to path
    adapters_dir = Path(__file__).resolve().parent.parent / "adapters"
    sys.path.insert(0, str(adapters_dir))

    from adapters.openai_compatible_adapter import OpenAICompatibleAdapter

    # 从 provider_config 获取配置，回退到 os.environ
    api_key = _require_config_value(provider_config, "HWP_LLM_API_KEY", "OPENAI_API_KEY")
    model = _require_config_value(provider_config, "HWP_LLM_MODEL", "OPENAI_MODEL")
    provider_name = _get_config_value(provider_config, "HWP_PROVIDER_NAME", default="openai").lower()

    # Resolve base URL
    explicit = _get_config_value(provider_config, "HWP_LLM_BASE_URL", "OPENAI_BASE_URL", default="").rstrip("/")
    if explicit:
        base_url = explicit
    else:
        provider_urls = {
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
        base_url = provider_urls.get(provider_name, "https://api.openai.com/v1")

    temperature = float(_get_config_value(provider_config, "HWP_LLM_TEMPERATURE", "HWP_OPENAI_TEMPERATURE", default="0.7"))
    timeout = int(_get_config_value(provider_config, "HWP_LLM_TIMEOUT_SEC", "HWP_OPENAI_TIMEOUT_SEC", default="120"))

    adapter = OpenAICompatibleAdapter(
        base_url=base_url,
        model=model,
        api_key=api_key,
        timeout=timeout,
        temperature=temperature,
    )

    # Set environment variables expected by adapter
    os.environ["HWP_AGENT_MESSAGE"] = message
    os.environ["HWP_AGENT_SESSION_ID"] = session_id
    os.environ["HWP_AGENT_ROUND"] = str(round_num)

    return adapter.call(message)


def import_and_call_ollama_adapter(
    message: str, session_id: str, round_num: int, provider_config: dict[str, str]
) -> str:
    """直接导入并调用 Ollama adapter（避免子进程）

    Args:
        message: 输入消息
        session_id: 会话 ID
        round_num: 轮次号
        provider_config: provider 配置字典（优先于 os.environ）
    """
    adapters_dir = Path(__file__).resolve().parent.parent / "adapters"
    sys.path.insert(0, str(adapters_dir))

    from adapters.ollama_adapter import OllamaAdapter

    # 从 provider_config 获取配置，回退到 os.environ
    model = _require_config_value(provider_config, "OLLAMA_MODEL")
    base_url = _get_config_value(provider_config, "OLLAMA_BASE_URL", default="http://127.0.0.1:11434").rstrip("/")
    temperature = float(_get_config_value(provider_config, "HWP_OLLAMA_TEMPERATURE", default="0.7"))
    timeout = int(_get_config_value(provider_config, "HWP_OLLAMA_TIMEOUT_SEC", default="120"))

    adapter = OllamaAdapter(
        base_url=base_url,
        model=model,
        timeout=timeout,
        temperature=temperature,
    )

    # Set environment variables expected by adapter
    os.environ["HWP_AGENT_MESSAGE"] = message
    os.environ["HWP_AGENT_SESSION_ID"] = session_id
    os.environ["HWP_AGENT_ROUND"] = str(round_num)

    return adapter.call(message)


def call_openclaw_binary(
    message: str,
    session_id: str,
    round_num: int,
    agent_bin: str,
    timeout_sec: int,
) -> str:
    """通过 subprocess 调用 OpenClaw 二进制"""
    env = os.environ.copy()
    env["OPENCLAW_LOG_LEVEL"] = "error"

    cmd = [agent_bin, "agent", "--message", message, "--session-id", session_id, "--json"]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        env=env,
    )

    if result.returncode != 0:
        raise RuntimeError(f"OpenClaw failed: {result.stderr}")

    return result.stdout


def call_agent_cmd(
    message: str,
    session_id: str,
    round_num: int,
    agent_cmd: str,
    timeout_sec: int,
) -> str:
    """通过 subprocess 调用自定义 agent 命令"""
    env = os.environ.copy()
    env["HWP_AGENT_MESSAGE"] = message
    env["HWP_AGENT_SESSION_ID"] = session_id
    env["HWP_AGENT_ROUND"] = str(round_num)

    result = subprocess.run(
        agent_cmd,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        env=env,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Agent command failed: {result.stderr}")

    return result.stdout


def invoke_provider_with_retry(
    message: str,
    session_id: str,
    round_num: int,
    runner_config: RunnerConfig,
    provider_config: dict[str, str],
) -> str:
    """调用 provider，带重试逻辑（指数退避）"""
    max_retries = runner_config.agent_max_retries
    timeout_sec = runner_config.agent_timeout_sec

    resolved_type = resolve_provider_alias(
        provider_config.get("HWP_PROVIDER_TYPE", ""),
        provider_config.get("HWP_PROVIDER_NAME", ""),
    )

    last_error: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        try:
            if resolved_type == "openai_compatible":
                return import_and_call_openai_adapter(message, session_id, round_num, provider_config)
            elif resolved_type == "ollama":
                return import_and_call_ollama_adapter(message, session_id, round_num, provider_config)
            elif runner_config.agent_cmd:
                return call_agent_cmd(message, session_id, round_num, runner_config.agent_cmd, timeout_sec)
            else:
                return call_openclaw_binary(
                    message, session_id, round_num, runner_config.agent_bin, timeout_sec
                )
        except Exception as exc:
            last_error = exc
            if attempt >= max_retries:
                raise RuntimeError(
                    f"Provider call failed after {max_retries} retries: {exc}"
                ) from exc

            backoff_sec = 2 ** (attempt + 1)
            print(
                f"WARN: Provider call failed (attempt {attempt + 1}/{max_retries}), retrying in {backoff_sec}s...",
                file=sys.stderr,
            )
            time.sleep(backoff_sec)

    raise RuntimeError(f"Provider call failed: {last_error}")


def run_multi_provider(
    input_text: str,
    providers: list[dict[str, str]],
    runner_config: RunnerConfig | None = None,
    max_workers: int | None = None,
) -> dict[str, str]:
    """并行调用多个 provider，收集所有结果

    适用于 benchmark/对比场景，同时向多个 provider 发送相同输入，
    并行获取结果以减少总等待时间。

    Args:
        input_text: 输入文本（prompt）
        providers: provider 配置列表，每个配置是一个字典，包含:
            - HWP_PROVIDER_TYPE: provider 类型 (openai_compatible, ollama, etc.)
            - HWP_PROVIDER_NAME: provider 名称 (deepseek, moonshot, etc.)
            - 以及其他必要的配置项 (API key, model, etc.)
        runner_config: 可选的 RunnerConfig，用于设置重试和超时参数
        max_workers: 最大并行工作线程数，默认为 provider 数量

    Returns:
        字典，格式为 {provider_name: result}，其中 provider_name 从配置中提取
        如果某个 provider 调用失败，对应的值为错误信息字符串 "ERROR: {error_msg}"

    Example:
        providers = [
            {"HWP_PROVIDER_TYPE": "openai_compatible", "HWP_PROVIDER_NAME": "deepseek", ...},
            {"HWP_PROVIDER_TYPE": "openai_compatible", "HWP_PROVIDER_NAME": "moonshot", ...},
        ]
        results = run_multi_provider("Hello", providers)
        # results = {"deepseek": "...", "moonshot": "..."}
    """
    if not providers:
        return {}

    # 使用默认 runner_config 如果未提供
    config = runner_config or RunnerConfig(
        root_dir=Path(__file__).resolve().parent.parent,
        agent_max_retries=3,
        agent_timeout_sec=30,
    )

    # 生成统一的 session_id 用于追踪
    timestamp = int(time.time())
    random_suffix = random.randint(10000, 99999)
    session_id = f"hwp_multi_{timestamp}_{random_suffix}"

    results: dict[str, str] = {}

    def call_single_provider(provider_config: dict[str, str]) -> tuple[str, str]:
        """调用单个 provider，返回 (provider_name, result)"""
        provider_name = provider_config.get("HWP_PROVIDER_NAME", "unknown")
        provider_type = provider_config.get("HWP_PROVIDER_TYPE", "")

        # 如果没有 provider_name，尝试从 type 推断
        if not provider_name or provider_name == "unknown":
            provider_name = provider_type or f"provider_{id(provider_config)}"

        try:
            result = invoke_provider_with_retry(
                message=input_text,
                session_id=session_id,
                round_num=1,  # 多 provider 调用使用 round 1
                runner_config=config,
                provider_config=provider_config,
            )
            return (provider_name, result)
        except Exception as exc:
            return (provider_name, f"ERROR: {exc}")

    # 使用 ThreadPoolExecutor 并行调用
    if max_workers is None:
        max_workers = len(providers)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_provider = {
            executor.submit(call_single_provider, provider_config): provider_config
            for provider_config in providers
        }

        # 收集结果
        for future in concurrent.futures.as_completed(future_to_provider):
            provider_name, result = future.result()
            results[provider_name] = result

    return results


# =============================================================================
# Output Cleaning and JSON Extraction
# =============================================================================

ANSI_ESCAPE_PATTERN = re.compile(r"\x1B\[[0-9;]*[mK]")


def strip_ansi_codes(text: str) -> str:
    """去除 ANSI 控制字符"""
    return ANSI_ESCAPE_PATTERN.sub("", text)


def extract_first_json(text: str) -> str:
    """从文本中提取第一个有效的 JSON 对象"""
    text = text.strip()
    if not text:
        raise ValueError("Empty text")

    # Try to parse the whole text first
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass

    # Find the first '{' and extract from there
    start = text.find("{")
    if start == -1:
        raise ValueError(f"No JSON object found in: {text[:200]}")

    # Use bracket matching to find the end
    depth = 0
    in_string = False
    escape = False

    for idx, char in enumerate(text[start:], start=start):
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
                candidate = text[start : idx + 1]
                try:
                    json.loads(candidate)
                    return candidate
                except json.JSONDecodeError:
                    continue

    raise ValueError(f"Unable to extract valid JSON from: {text[:200]}")


def extract_result_from_response(text: str) -> dict[str, Any]:
    """从 provider 响应中提取 result 部分"""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON response: {exc}") from exc

    # Handle both wrapped and unwrapped formats
    if "result" in data:
        return data["result"]
    return data


# =============================================================================
# Replay Mode
# =============================================================================

def load_replay_result(replay_path: Path, round_num: int) -> dict[str, Any]:
    """从 JSONL 文件读取第 N 行作为第 N 轮结果"""
    with open(replay_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if round_num > len(lines):
        raise ValueError(f"Replay chain missing data at round {round_num}")

    line = lines[round_num - 1].strip()
    if not line:
        raise ValueError(f"Replay chain has empty line at round {round_num}")

    data = json.loads(line)
    # Return result field or the whole object
    return data.get("result", data)


# =============================================================================
# Prompt Building
# =============================================================================

def load_system_prompt(spec_path: Path) -> tuple[str, str]:
    """加载系统提示词并提取指纹"""
    with open(spec_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract fingerprint from first line
    fingerprint = "(missing)"
    for line in content.split("\n")[:5]:
        if line.startswith("PROMPT_FINGERPRINT:"):
            fingerprint = line.split(":", 1)[1].strip()
            break

    return content, fingerprint


def build_prompt(
    system_prompt: str,
    round_num: int,
    parent_node: Optional[str],
    parent_recovery: bool,
    parent_vars: list,
    input_with_hint: str,
) -> str:
    """构建完整的 prompt"""
    parent_node_str = parent_node if parent_node else "null"
    parent_vars_json = json.dumps(parent_vars, ensure_ascii=False)

    return f"""{system_prompt}

Meta:
- round: {round_num}
- parent_node_id: {parent_node_str}
- parent_recovery_applied: {json.dumps(parent_recovery)}
- parent_variables_json: {parent_vars_json}
- input_text: {input_with_hint}

Now run Round {round_num}."""


# =============================================================================
# Provider Block Fallback
# =============================================================================

def create_fallback_inner_json(
    round_num: int,
    parent_node: Optional[str],
    hint_json: dict[str, Any],
    provider_snip: str,
) -> dict[str, Any]:
    """当 payload.text 不是 JSON 时，创建 fallback inner JSON"""
    timestamp = time.strftime("%Y%m%dT%H%M%S")
    node_id = f"HWP_FALLBACK_R{round_num}_{timestamp}"

    return {
        "node_id": node_id,
        "parent_id": parent_node,
        "round": round_num,
        "questions": [],
        "variables": [],
        "paths": [],
        "tensions": [],
        "unfinished": [],
        "entropy_score": 0,
        "novelty_rate": 0,
        "shared_variable_count": 0,
        "drift_rate": 1,
        "collapse_detected": True,
        "recovery_applied": True,
        "speed_metrics": {
            "mode": "Rg0",
            "unfinished_inherited_count": 0,
            "action_taken": ["provider_audit_block_fallback"],
        },
        "rhythm": {
            "mode": "Rg0",
            "entropy_target": {"min": 0.0, "max": 1.0},
            "variable_policy": {"keep_n": 0, "new_n": 0, "max_vars": 0, "keep_prefix": True},
            "hint": hint_json,
            "hint_applied": True,
        },
        "provider_block_snip": provider_snip[:140],
    }


# =============================================================================
# Chain Runner
# =============================================================================

class ChainRunner:
    """链运行器 - 执行单条链的 8 轮迭代"""

    def __init__(self, config: RunnerConfig, provider_config: dict[str, str]):
        self.config = config
        self.provider_config = provider_config
        self.log_dir = config.root_dir / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Load system prompt
        spec_path = config.root_dir / "spec" / "hwp_turn_prompt.txt"
        self.system_prompt, self.prompt_fingerprint = load_system_prompt(spec_path)

    def run_input_file(self, input_file: Path) -> None:
        """处理输入文件，每行一条测试链"""
        with open(input_file, "r", encoding="utf-8") as f:
            lines = [line.rstrip("\n") for line in f]

        for line in lines:
            if not line.strip():
                continue
            self.run_chain(line)

    def run_chain(self, base_line: str) -> None:
        """执行单条链（8轮）"""
        # Generate session ID
        timestamp = int(time.time())
        random_suffix = random.randint(10000, 99999)
        session_id = f"hwp_{timestamp}_{random_suffix}"
        log_file = self.log_dir / f"chain_{session_id}.jsonl"

        # Initialize state
        state = ChainState()
        state.is_probe = "COLLAPSE_PROBE=1" in base_line

        # Sanitize input: replace RHYTHM_HINT to prevent conflicts
        base_line = base_line.replace("RHYTHM_HINT=", "RHYTHM_HINT_DISABLED=")

        # Timing stats
        chain_start_ts = time.perf_counter()
        completed_rounds = 0
        total_round_sec = 0.0
        max_round_sec = 0.0

        # Log chain start
        self._log_run(f"开始链: {session_id}，输入: {base_line}")
        self._log_run(f"  PROMPT_FINGERPRINT: {self.prompt_fingerprint}")
        if self.config.chain_timeout_sec > 0:
            self._log_run(f"  CHAIN_TIMEOUT_SEC: {self.config.chain_timeout_sec}")

        # Create/clear log file
        log_file.write_text("", encoding="utf-8")

        for round_num in range(1, self.config.rounds_per_chain + 1):
            # Check timeout before round
            if self._check_timeout(chain_start_ts):
                chain_elapsed = time.perf_counter() - chain_start_ts
                self._log_run(
                    f"TIMEOUT: chain {session_id} exceeded HWP_CHAIN_TIMEOUT_SEC="
                    f"{self.config.chain_timeout_sec}s before round {round_num} "
                    f"(elapsed={chain_elapsed:.2f}s)"
                )
                raise TimeoutError(f"Chain timeout before round {round_num}")

            round_start_ts = time.perf_counter()
            self._log_run(f"  链 {session_id} 第 {round_num} 轮")

            # Compute controller state
            mode = compute_mode(
                round_num,
                state.is_probe,
                state.prev_entropy,
                state.prev_drift,
                state.prev_collapse,
                state.prev_recovery,
            )
            et_min, et_max = compute_band(mode)
            hint_json = emit_hint_json(mode, et_min, et_max, 20, 10, 30)

            # Build input with hint
            input_with_hint = f"RHYTHM_HINT={json.dumps(hint_json, separators=(',', ':'))} {base_line}"
            self._log_run(f"    [controller] {input_with_hint}")

            # Build prompt
            prompt = build_prompt(
                self.system_prompt,
                round_num,
                state.parent_node,
                state.parent_recovery,
                state.parent_vars,
                input_with_hint,
            )

            # Get result (replay or live)
            if self.config.replay_chain_path:
                self._log_run(f"    [replay] using {self.config.replay_chain_path} round {round_num}")
                result_json = load_replay_result(self.config.replay_chain_path, round_num)
            else:
                result_json = self._call_provider(prompt, session_id, round_num)

            # Extract payload.text
            inner_text = self._extract_payload_text(result_json)

            # Handle provider block (non-JSON payload)
            if not inner_text or not inner_text.strip().startswith("{"):
                self._handle_provider_block(
                    round_num, session_id, log_file, result_json, hint_json, state, inner_text
                )
            else:
                self._handle_normal_round(
                    round_num, session_id, log_file, result_json, inner_text, state
                )

            # Update timing stats
            round_elapsed = time.perf_counter() - round_start_ts
            chain_elapsed = time.perf_counter() - chain_start_ts
            completed_rounds += 1
            total_round_sec += round_elapsed
            max_round_sec = max(max_round_sec, round_elapsed)

            self._log_run(f"    [timing] round_sec={round_elapsed:.2f} chain_sec={chain_elapsed:.2f}")

            # Check timeout after round
            if self._check_timeout(chain_start_ts):
                avg_sec = total_round_sec / completed_rounds if completed_rounds > 0 else 0
                self._log_run(
                    f"TIMEOUT: chain {session_id} exceeded HWP_CHAIN_TIMEOUT_SEC="
                    f"{self.config.chain_timeout_sec}s after round {round_num} "
                    f"(elapsed={chain_elapsed:.2f}s)"
                )
                self._log_run(
                    f"  [summary] session_id={session_id} rounds_completed={completed_rounds} "
                    f"round_avg_sec={avg_sec:.2f} round_max_sec={max_round_sec:.2f} "
                    f"chain_sec={chain_elapsed:.2f}"
                )
                raise TimeoutError(f"Chain timeout after round {round_num}")

            # Sleep between rounds
            if round_num < self.config.rounds_per_chain:
                time.sleep(self.config.round_sleep_sec)

        # Chain summary
        chain_elapsed = time.perf_counter() - chain_start_ts
        avg_sec = total_round_sec / completed_rounds if completed_rounds > 0 else 0
        self._log_run(
            f"  [summary] session_id={session_id} rounds_completed={completed_rounds} "
            f"round_avg_sec={avg_sec:.2f} round_max_sec={max_round_sec:.2f} "
            f"chain_sec={chain_elapsed:.2f}"
        )
        self._log_run(
            f"完成链: {session_id} (rounds={self.config.rounds_per_chain}, elapsed_sec={chain_elapsed:.2f})"
        )

    def _call_provider(self, prompt: str, session_id: str, round_num: int) -> dict[str, Any]:
        """调用 provider 获取结果"""
        raw_output = invoke_provider_with_retry(
            prompt, session_id, round_num, self.config, self.provider_config
        )

        # Clean output
        cleaned = strip_ansi_codes(raw_output)
        cleaned = extract_first_json(cleaned)

        if not cleaned:
            raise ValueError(f"Empty response after cleaning at round {round_num}")

        return extract_result_from_response(cleaned)

    def _extract_payload_text(self, result_json: dict[str, Any]) -> str:
        """从 result JSON 中提取 payload.text"""
        payloads = result_json.get("payloads", [])
        if payloads and isinstance(payloads, list):
            first_payload = payloads[0]
            if isinstance(first_payload, dict):
                return first_payload.get("text", "")
        return ""

    def _handle_provider_block(
        self,
        round_num: int,
        session_id: str,
        log_file: Path,
        result_json: dict[str, Any],
        hint_json: dict[str, Any],
        state: ChainState,
        provider_text: str,
    ) -> None:
        """处理 provider block 情况（payload.text 不是 JSON）"""
        snip = (provider_text or "")[:140]
        self._log_run(f"  警告：第 {round_num} 轮 payload.text 不是 JSON（可能被内容审查拦截），写入 fallback 并继续")
        self._log_run(f"  SNIP: {snip}")

        # Create fallback inner JSON
        inner = create_fallback_inner_json(round_num, state.parent_node, hint_json, snip)

        # Transform and save
        enriched = enrich_inner_json(inner, round_num, state.parent_recovery)
        repacked = repack_result_with_inner(result_json, enriched)

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(repacked, ensure_ascii=False, separators=(",", ":")) + "\n")

        # Update state for next round
        state.parent_vars = enriched.get("variables", [])
        state.parent_node = enriched.get("node_id")
        state.parent_recovery = True
        state.prev_entropy = 0.70
        state.prev_drift = 1.00
        state.prev_collapse = True
        state.prev_recovery = True

    def _handle_normal_round(
        self,
        round_num: int,
        session_id: str,
        log_file: Path,
        result_json: dict[str, Any],
        inner_text: str,
        state: ChainState,
    ) -> None:
        """处理正常轮次"""
        # Parse inner JSON
        try:
            inner = json.loads(inner_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid inner JSON at round {round_num}: {exc}") from exc

        # Transform
        enriched = enrich_inner_json(inner, round_num, state.parent_recovery)
        repacked = repack_result_with_inner(result_json, enriched)

        # Save to log
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(repacked, ensure_ascii=False, separators=(",", ":")) + "\n")

        # Update state for next round
        state.parent_vars = enriched.get("variables", [])
        state.parent_node = enriched.get("node_id")
        state.parent_recovery = enriched.get("recovery_applied", False)
        state.prev_entropy = enriched.get("entropy_score", 0.70)
        state.prev_drift = enriched.get("drift_rate", 0.0)
        state.prev_collapse = enriched.get("collapse_detected", False)
        state.prev_recovery = enriched.get("recovery_applied", False)

    def _check_timeout(self, chain_start_ts: float) -> bool:
        """检查链是否超时"""
        if self.config.chain_timeout_sec <= 0:
            return False
        elapsed = time.perf_counter() - chain_start_ts
        return elapsed >= self.config.chain_timeout_sec

    def _log_run(self, message: str) -> None:
        """输出到控制台和 run.log"""
        print(message)
        run_log = self.log_dir / "run.log"
        with open(run_log, "a", encoding="utf-8") as f:
            f.write(message + "\n")


# =============================================================================
# CLI Entry Point
# =============================================================================


def build_runner_parser() -> argparse.ArgumentParser:
    """构建 runner 子命令的 argument parser"""
    parser = argparse.ArgumentParser(
        prog="python3 -m hwp_protocol.runner",
        description="HWP Python Runner - 链编排运行时",
    )

    parser.add_argument("input_file", type=Path, help="输入文件路径（每行一条测试链）")
    parser.add_argument(
        "--replay-chain",
        type=Path,
        dest="replay_chain",
        help="从 JSONL 文件回放链",
    )
    parser.add_argument(
        "--provider-type",
        dest="provider_type",
        help="Provider 类型 (openai_compatible, ollama, openclaw, custom)",
    )
    parser.add_argument(
        "--provider-name",
        dest="provider_name",
        help="Provider 名称 (openrouter, deepseek, moonshot, etc.)",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=8,
        help="每链轮次数（默认：8）",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        dest="sleep_sec",
        default=2.0,
        help="轮次间休眠秒数（默认：2.0）",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        dest="timeout_sec",
        default=0.0,
        help="链超时秒数，0 表示无超时（默认：0.0）",
    )
    parser.add_argument(
        "--config",
        type=Path,
        dest="config_path",
        help="Provider 配置文件路径",
    )
    parser.add_argument(
        "--agent-bin",
        dest="agent_bin",
        help="Agent 二进制路径（用于 openclaw）",
    )
    parser.add_argument(
        "--agent-cmd",
        dest="agent_cmd",
        help="Agent 命令（用于 custom provider）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="仅验证配置，不执行",
    )

    return parser


def cmd_run(args: argparse.Namespace) -> int:
    """run 子命令入口"""
    root_dir = Path(__file__).resolve().parent.parent

    # Load provider configuration
    provider_config = load_provider_config(root_dir, args.config_path)

    # Apply CLI overrides
    if args.provider_type:
        provider_config["HWP_PROVIDER_TYPE"] = args.provider_type
    if args.provider_name:
        provider_config["HWP_PROVIDER_NAME"] = args.provider_name
    if args.agent_bin:
        provider_config["HWP_AGENT_BIN"] = args.agent_bin
    if args.agent_cmd:
        provider_config["HWP_AGENT_CMD"] = args.agent_cmd
    if args.replay_chain:
        provider_config["HWP_REPLAY_CHAIN_PATH"] = str(args.replay_chain)

    # Apply defaults
    provider_config = apply_provider_defaults(provider_config, root_dir)

    # Build runner config
    runner_config = RunnerConfig(
        root_dir=root_dir,
        rounds_per_chain=args.rounds,
        round_sleep_sec=args.sleep_sec,
        chain_timeout_sec=args.timeout_sec,
        replay_chain_path=args.replay_chain,
        provider_type=provider_config.get("HWP_PROVIDER_TYPE", ""),
        provider_name=provider_config.get("HWP_PROVIDER_NAME", ""),
        agent_cmd=provider_config.get("HWP_AGENT_CMD", ""),
        agent_bin=provider_config.get("HWP_AGENT_BIN", "openclaw"),
        agent_max_retries=int(provider_config.get("HWP_AGENT_MAX_RETRIES", "3")),
        agent_timeout_sec=int(provider_config.get("HWP_AGENT_TIMEOUT", "30")),
        dry_run=args.dry_run,
    )

    # Validate input file
    if not args.input_file.exists():
        print(f"错误：输入文件不存在: {args.input_file}", file=sys.stderr)
        return 1

    # Dry run: just validate and print summary
    if args.dry_run:
        print("HWP Python Runner (dry-run)")
        print(f"  config: {args.config_path or root_dir / 'config' / 'provider.env'}")
        print(f"  provider_type: {runner_config.provider_type or '(unset)'}")
        print(f"  provider_name: {runner_config.provider_name or '(unset)'}")
        resolved = resolve_provider_alias(
            runner_config.provider_type, runner_config.provider_name
        )
        print(f"  resolved_type: {resolved or '(unset)'}")
        print(f"  replay_chain: {runner_config.replay_chain_path or '(none)'}")
        if runner_config.replay_chain_path:
            print("  active_transport: replay_chain")
        elif runner_config.agent_cmd:
            print("  active_transport: agent_cmd")
            print(f"  agent_cmd: {runner_config.agent_cmd}")
        else:
            print("  active_transport: agent_bin")
            print(f"  agent_bin: {runner_config.agent_bin}")
        print("Dry run OK: provider configuration is ready.")
        return 0

    # Run chains
    runner = ChainRunner(runner_config, provider_config)

    try:
        runner.run_input_file(args.input_file)
        print(f"输入文件 {args.input_file} 处理完成。")
        return 0
    except TimeoutError as exc:
        print(f"TIMEOUT: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 1


def main() -> int:
    """Main entry point for runner module"""
    parser = build_runner_parser()
    args = parser.parse_args()
    return cmd_run(args)


if __name__ == "__main__":
    raise SystemExit(main())
