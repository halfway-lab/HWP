#!/usr/bin/env bash

# Shared agent invocation helpers for HWP runners.
# Default mode keeps backward compatibility with the OpenClaw CLI.

HWP_AGENT_BIN="${HWP_AGENT_BIN:-}"
HWP_AGENT_CMD="${HWP_AGENT_CMD:-}"
HWP_REPLAY_CHAIN_PATH="${HWP_REPLAY_CHAIN_PATH:-}"
HWP_PROVIDER_CONFIG="${HWP_PROVIDER_CONFIG:-}"
HWP_PROVIDER_TYPE="${HWP_PROVIDER_TYPE:-}"
HWP_PROVIDER_NAME="${HWP_PROVIDER_NAME:-}"
HWP_AGENT_MAX_RETRIES="${HWP_AGENT_MAX_RETRIES:-3}"
HWP_AGENT_TIMEOUT="${HWP_AGENT_TIMEOUT:-30}"

_hwp_cli_agent_bin=""
_hwp_cli_agent_cmd=""
_hwp_cli_replay_chain_path=""
_hwp_cli_provider_config=""
_hwp_cli_provider_type=""
_hwp_cli_provider_name=""
HWP_SHOW_HELP=""
HWP_DRY_RUN=""

resolve_hwp_root_dir() {
  local script_source="${BASH_SOURCE[0]}"
  local script_dir
  script_dir="$(cd "$(dirname "$script_source")" && pwd)"
  cd "$script_dir/.." && pwd
}

default_hwp_provider_config() {
  local root_dir="${1:-$(resolve_hwp_root_dir)}"
  printf '%s/config/provider.env' "$root_dir"
}

parse_hwp_provider_args() {
  HWP_INPUT_FILE=""
  HWP_SHOW_HELP=""
  HWP_DRY_RUN=""
  _hwp_cli_agent_bin=""
  _hwp_cli_agent_cmd=""
  _hwp_cli_replay_chain_path=""
  _hwp_cli_provider_config=""
  _hwp_cli_provider_type=""
  _hwp_cli_provider_name=""
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --provider-type)
        [ "$#" -ge 2 ] || { echo "错误：--provider-type 需要一个参数" >&2; exit 1; }
        _hwp_cli_provider_type="$2"
        shift 2
        ;;
      --provider-name)
        [ "$#" -ge 2 ] || { echo "错误：--provider-name 需要一个参数" >&2; exit 1; }
        _hwp_cli_provider_name="$2"
        shift 2
        ;;
      --agent-bin)
        [ "$#" -ge 2 ] || { echo "错误：--agent-bin 需要一个参数" >&2; exit 1; }
        _hwp_cli_agent_bin="$2"
        shift 2
        ;;
      --agent-cmd)
        [ "$#" -ge 2 ] || { echo "错误：--agent-cmd 需要一个参数" >&2; exit 1; }
        _hwp_cli_agent_cmd="$2"
        shift 2
        ;;
      --replay-chain)
        [ "$#" -ge 2 ] || { echo "错误：--replay-chain 需要一个参数" >&2; exit 1; }
        _hwp_cli_replay_chain_path="$2"
        shift 2
        ;;
      --config)
        [ "$#" -ge 2 ] || { echo "错误：--config 需要一个参数" >&2; exit 1; }
        _hwp_cli_provider_config="$2"
        shift 2
        ;;
      --help|-h)
        HWP_SHOW_HELP="1"
        shift
        ;;
      --dry-run)
        HWP_DRY_RUN="1"
        shift
        ;;
      --*)
        echo "错误：未知参数: $1" >&2
        exit 1
        ;;
      *)
        if [ -n "${HWP_INPUT_FILE:-}" ]; then
          echo "错误：多余的位置参数: $1" >&2
          exit 1
        fi
        HWP_INPUT_FILE="$1"
        shift
        ;;
    esac
  done
}

load_hwp_provider_config() {
  local config_path="$1"
  [ -n "$config_path" ] || return 0
  [ -f "$config_path" ] || return 0

  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      ''|'#'*) continue ;;
    esac

    if [[ "$line" != *=* ]]; then
      continue
    fi

    local key="${line%%=*}"
    local value="${line#*=}"

    key="${key#"${key%%[![:space:]]*}"}"
    key="${key%"${key##*[![:space:]]}"}"
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"

    if [[ "$value" == \"*\" && "$value" == *\" ]]; then
      value="${value:1:${#value}-2}"
    elif [[ "$value" == \'*\' && "$value" == *\' ]]; then
      value="${value:1:${#value}-2}"
    fi

    case "$key" in
      HWP_AGENT_BIN)
        [ -n "$HWP_AGENT_BIN" ] || HWP_AGENT_BIN="$value"
        ;;
      HWP_AGENT_CMD)
        [ -n "$HWP_AGENT_CMD" ] || HWP_AGENT_CMD="$value"
        ;;
      HWP_REPLAY_CHAIN_PATH)
        [ -n "$HWP_REPLAY_CHAIN_PATH" ] || HWP_REPLAY_CHAIN_PATH="$value"
        ;;
      HWP_PROVIDER_CONFIG)
        :
        ;;
      HWP_PROVIDER_TYPE)
        if [ -z "$HWP_PROVIDER_TYPE" ]; then
          HWP_PROVIDER_TYPE="$value"
          export HWP_PROVIDER_TYPE
        fi
        ;;
      HWP_PROVIDER_NAME)
        if [ -z "$HWP_PROVIDER_NAME" ]; then
          HWP_PROVIDER_NAME="$value"
          export HWP_PROVIDER_NAME
        fi
        ;;
      *)
        if [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] && [ -z "${!key:-}" ]; then
          printf -v "$key" '%s' "$value"
          export "$key"
        fi
        ;;
    esac
  done < "$config_path"
}

resolve_hwp_provider_alias() {
  local raw_type="$1"
  local raw_name="$2"
  local normalized_type normalized_name
  normalized_type="$(printf '%s' "$raw_type" | tr '[:upper:]' '[:lower:]')"
  normalized_name="$(printf '%s' "$raw_name" | tr '[:upper:]' '[:lower:]')"

  case "$normalized_type" in
    "" )
      return 0
      ;;
    openclaw|claw)
      printf 'openclaw'
      ;;
    ollama)
      printf 'ollama'
      ;;
    openai|openai_compatible|compatible|llm_api|api)
      printf 'openai_compatible'
      ;;
    custom)
      printf 'custom'
      ;;
    *)
      case "$normalized_name" in
        openrouter|deepseek|moonshot|kimi|siliconflow|together|fireworks|groq|perplexity|xai|azure_openai)
          printf 'openai_compatible'
          ;;
        ollama)
          printf 'ollama'
          ;;
        openclaw)
          printf 'openclaw'
          ;;
        *)
          printf '%s' "$normalized_type"
          ;;
      esac
      ;;
  esac
}

apply_hwp_provider_defaults() {
  local root_dir="$1"
  local resolved_type
  resolved_type="$(resolve_hwp_provider_alias "$HWP_PROVIDER_TYPE" "$HWP_PROVIDER_NAME")"

  if [ -n "$HWP_AGENT_CMD" ] || [ -n "$HWP_REPLAY_CHAIN_PATH" ]; then
    :
  elif [ -n "$resolved_type" ]; then
    case "$resolved_type" in
      openai_compatible)
        HWP_AGENT_CMD="python3 $root_dir/adapters/openai_compatible_adapter.py"
        ;;
      ollama)
        HWP_AGENT_CMD="python3 $root_dir/adapters/ollama_adapter.py"
        ;;
      openclaw)
        HWP_AGENT_BIN="${HWP_AGENT_BIN:-openclaw}"
        ;;
      custom)
        :
        ;;
      *)
        echo "错误：未知 HWP_PROVIDER_TYPE: ${HWP_PROVIDER_TYPE}" >&2
        echo "支持的 provider type: openclaw, openai_compatible, ollama, custom" >&2
        exit 1
        ;;
    esac
  fi
}

resolve_hwp_provider_settings() {
  local root_dir="${1:-$(resolve_hwp_root_dir)}"
  local config_path="${_hwp_cli_provider_config:-${HWP_PROVIDER_CONFIG:-$(default_hwp_provider_config "$root_dir")}}"

  load_hwp_provider_config "$config_path"

  HWP_PROVIDER_CONFIG="$config_path"

  if [ -n "$_hwp_cli_agent_bin" ]; then
    HWP_AGENT_BIN="$_hwp_cli_agent_bin"
  fi
  if [ -n "$_hwp_cli_agent_cmd" ]; then
    HWP_AGENT_CMD="$_hwp_cli_agent_cmd"
  fi
  if [ -n "$_hwp_cli_replay_chain_path" ]; then
    HWP_REPLAY_CHAIN_PATH="$_hwp_cli_replay_chain_path"
  fi
  if [ -n "$_hwp_cli_provider_type" ]; then
    HWP_PROVIDER_TYPE="$_hwp_cli_provider_type"
    export HWP_PROVIDER_TYPE
  fi
  if [ -n "$_hwp_cli_provider_name" ]; then
    HWP_PROVIDER_NAME="$_hwp_cli_provider_name"
    export HWP_PROVIDER_NAME
  fi

  apply_hwp_provider_defaults "$root_dir"

  if [ -z "$HWP_AGENT_BIN" ]; then
    HWP_AGENT_BIN="openclaw"
  fi
}

require_hwp_agent_provider() {
  local replay_chain_path="${1:-$HWP_REPLAY_CHAIN_PATH}"

  if [ -n "$replay_chain_path" ]; then
    if [ ! -f "$replay_chain_path" ]; then
      echo "错误：回放链文件不存在: $replay_chain_path" >&2
      exit 1
    fi
    return
  fi

  if [ -n "$HWP_AGENT_CMD" ]; then
    return
  fi

  if ! command -v "$HWP_AGENT_BIN" >/dev/null 2>&1; then
    echo "错误：未找到 agent 命令: $HWP_AGENT_BIN" >&2
    echo "请先安装/配置 OpenClaw，或设置 HWP_AGENT_CMD 以接入其他模型适配脚本。" >&2
    exit 1
  fi
}

print_hwp_provider_summary() {
  local resolved_type
  resolved_type="$(resolve_hwp_provider_alias "$HWP_PROVIDER_TYPE" "$HWP_PROVIDER_NAME")"

  echo "HWP provider summary:"
  echo "  config: ${HWP_PROVIDER_CONFIG:-"(default/none)"}"
  echo "  provider_type: ${HWP_PROVIDER_TYPE:-"(unset)"}"
  echo "  provider_name: ${HWP_PROVIDER_NAME:-"(unset)"}"
  echo "  resolved_type: ${resolved_type:-"(unset)"}"
  echo "  replay_chain: ${HWP_REPLAY_CHAIN_PATH:-"(none)"}"
  if [ -n "${HWP_REPLAY_CHAIN_PATH:-}" ]; then
    echo "  active_transport: replay_chain"
    echo "  agent_bin: (inactive)"
    echo "  agent_cmd: (inactive)"
  elif [ -n "${HWP_AGENT_CMD:-}" ]; then
    echo "  active_transport: agent_cmd"
    echo "  agent_bin: (inactive)"
    echo "  agent_cmd: ${HWP_AGENT_CMD}"
  else
    echo "  active_transport: agent_bin"
    echo "  agent_bin: ${HWP_AGENT_BIN:-"(unset)"}"
    echo "  agent_cmd: (inactive)"
  fi
}

is_hwp_placeholder_value() {
  local value="${1:-}"
  case "$value" in
    "" )
      return 1
      ;;
    your_*|YOUR_*|*your_api_key_here*|*your_model_here*|*your_local_model_here*|*example.com*|dummy|dummy-* )
      return 0
      ;;
    *YOUR_KEY*|*YOUR_MODEL* )
      return 0
      ;;
    * )
      return 1
      ;;
  esac
}

validate_hwp_provider_setup() {
  local resolved_type provider_name
  resolved_type="$(resolve_hwp_provider_alias "$HWP_PROVIDER_TYPE" "$HWP_PROVIDER_NAME")"
  provider_name="$(printf '%s' "${HWP_PROVIDER_NAME:-}" | tr '[:upper:]' '[:lower:]')"

  if [ -n "$HWP_REPLAY_CHAIN_PATH" ]; then
    if [ ! -f "$HWP_REPLAY_CHAIN_PATH" ]; then
      echo "错误：回放链文件不存在: $HWP_REPLAY_CHAIN_PATH" >&2
      return 1
    fi
    return 0
  fi

  case "$resolved_type" in
    openai_compatible)
      [ -n "${HWP_LLM_API_KEY:-${OPENAI_API_KEY:-}}" ] || { echo "错误：缺少 HWP_LLM_API_KEY（或 OPENAI_API_KEY）" >&2; return 1; }
      [ -n "${HWP_LLM_MODEL:-${OPENAI_MODEL:-}}" ] || { echo "错误：缺少 HWP_LLM_MODEL（或 OPENAI_MODEL）" >&2; return 1; }
      case "$provider_name" in
        ""|openai|openrouter|deepseek|moonshot|kimi|siliconflow|groq|together|fireworks|perplexity|xai)
          ;;
        *)
          [ -n "${HWP_LLM_BASE_URL:-${OPENAI_BASE_URL:-}}" ] || {
            echo "错误：custom/unknown OpenAI-compatible provider 需要显式设置 HWP_LLM_BASE_URL" >&2
            return 1
          }
          ;;
      esac
      ;;
    ollama)
      [ -n "${OLLAMA_MODEL:-}" ] || { echo "错误：缺少 OLLAMA_MODEL" >&2; return 1; }
      ;;
    openclaw)
      if ! command -v "${HWP_AGENT_BIN:-openclaw}" >/dev/null 2>&1; then
        echo "错误：未找到 agent 命令: ${HWP_AGENT_BIN:-openclaw}" >&2
        return 1
      fi
      ;;
    custom)
      [ -n "${HWP_AGENT_CMD:-}" ] || { echo "错误：custom provider 需要设置 HWP_AGENT_CMD" >&2; return 1; }
      ;;
    *)
      if [ -z "${HWP_AGENT_CMD:-}" ] && [ -z "${HWP_REPLAY_CHAIN_PATH:-}" ]; then
        echo "错误：无法解析 provider，请设置 HWP_PROVIDER_TYPE / HWP_PROVIDER_NAME 或 HWP_AGENT_CMD" >&2
        return 1
      fi
      ;;
  esac

  return 0
}

print_hwp_provider_warnings() {
  local warnings=()

  if is_hwp_placeholder_value "${HWP_LLM_API_KEY:-${OPENAI_API_KEY:-}}"; then
    warnings+=("HWP_LLM_API_KEY still looks like a placeholder")
  fi
  if is_hwp_placeholder_value "${HWP_LLM_MODEL:-${OPENAI_MODEL:-}}"; then
    warnings+=("HWP_LLM_MODEL still looks like a placeholder")
  fi
  if is_hwp_placeholder_value "${HWP_LLM_BASE_URL:-${OPENAI_BASE_URL:-}}"; then
    warnings+=("HWP_LLM_BASE_URL still looks like a placeholder")
  fi
  if is_hwp_placeholder_value "${OLLAMA_MODEL:-}"; then
    warnings+=("OLLAMA_MODEL still looks like a placeholder")
  fi

  if [ "${#warnings[@]}" -gt 0 ]; then
    echo "Warnings:"
    local item
    for item in "${warnings[@]}"; do
      echo "  - $item"
    done
  fi
}

_hwp_timeout_cmd=""

_get_timeout_cmd() {
  if [ -n "$_hwp_timeout_cmd" ]; then
    printf '%s' "$_hwp_timeout_cmd"
    return 0
  fi

  if command -v timeout >/dev/null 2>&1; then
    _hwp_timeout_cmd="timeout"
  elif command -v gtimeout >/dev/null 2>&1; then
    _hwp_timeout_cmd="gtimeout"
  else
    _hwp_timeout_cmd=""
  fi
  printf '%s' "$_hwp_timeout_cmd"
}

_invoke_hwp_agent_once() {
  local msg="$1"
  local session_id="$2"
  local round_num="${3:-}"
  local timeout_sec="${4:-30}"
  local timeout_cmd
  timeout_cmd="$(_get_timeout_cmd)"

  if [ -n "$HWP_AGENT_CMD" ]; then
    if [ -n "$timeout_cmd" ]; then
      HWP_AGENT_MESSAGE="$msg" \
      HWP_AGENT_SESSION_ID="$session_id" \
      HWP_AGENT_ROUND="$round_num" \
      "$timeout_cmd" "$timeout_sec" /bin/sh -c "$HWP_AGENT_CMD"
    else
      HWP_AGENT_MESSAGE="$msg" \
      HWP_AGENT_SESSION_ID="$session_id" \
      HWP_AGENT_ROUND="$round_num" \
      /bin/sh -c "$HWP_AGENT_CMD"
    fi
  else
    if [ -n "$timeout_cmd" ]; then
      "$timeout_cmd" "$timeout_sec" "$HWP_AGENT_BIN" agent --message "$msg" --session-id "$session_id" --json 2>/dev/null
    else
      OPENCLAW_LOG_LEVEL=error "$HWP_AGENT_BIN" agent --message "$msg" --session-id "$session_id" --json
    fi
  fi
}

invoke_hwp_agent() {
  local msg="$1"
  local session_id="$2"
  local round_num="${3:-}"
  local max_retries="${HWP_AGENT_MAX_RETRIES:-3}"
  local timeout_sec="${HWP_AGENT_TIMEOUT:-30}"
  local attempt=0
  local exit_code=0

  while :; do
    if _invoke_hwp_agent_once "$msg" "$session_id" "$round_num" "$timeout_sec"; then
      return 0
    fi
    exit_code=$?

    if [ "$exit_code" -eq 124 ]; then
      echo "FATAL: Provider timeout after ${timeout_sec}s (session=${session_id} round=${round_num})" >&2
    fi

    if [ "$attempt" -ge "$max_retries" ]; then
      echo "FATAL: Provider call failed after ${max_retries} retries (session=${session_id} round=${round_num})" >&2
      exit 1
    fi

    attempt=$((attempt + 1))
    local backoff_sec=$((2 ** attempt))
    echo "WARN: Provider call failed (attempt ${attempt}/${max_retries}), retrying in ${backoff_sec}s..." >&2
    sleep "$backoff_sec"
  done
}
