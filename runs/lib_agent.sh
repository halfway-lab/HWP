#!/usr/bin/env bash

# Shared agent invocation helpers for HWP runners.
# Default mode keeps backward compatibility with the OpenClaw CLI.

HWP_AGENT_BIN="${HWP_AGENT_BIN:-}"
HWP_AGENT_CMD="${HWP_AGENT_CMD:-}"
HWP_REPLAY_CHAIN_PATH="${HWP_REPLAY_CHAIN_PATH:-}"
HWP_PROVIDER_CONFIG="${HWP_PROVIDER_CONFIG:-}"
HWP_PROVIDER_TYPE="${HWP_PROVIDER_TYPE:-}"
HWP_PROVIDER_NAME="${HWP_PROVIDER_NAME:-}"

_hwp_cli_agent_bin=""
_hwp_cli_agent_cmd=""
_hwp_cli_replay_chain_path=""
_hwp_cli_provider_config=""
_hwp_cli_provider_type=""
_hwp_cli_provider_name=""
HWP_SHOW_HELP=""

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
        [ -n "$HWP_PROVIDER_TYPE" ] || HWP_PROVIDER_TYPE="$value"
        ;;
      HWP_PROVIDER_NAME)
        [ -n "$HWP_PROVIDER_NAME" ] || HWP_PROVIDER_NAME="$value"
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
  fi
  if [ -n "$_hwp_cli_provider_name" ]; then
    HWP_PROVIDER_NAME="$_hwp_cli_provider_name"
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

invoke_hwp_agent() {
  local msg="$1"
  local session_id="$2"
  local round_num="${3:-}"

  if [ -n "$HWP_AGENT_CMD" ]; then
    HWP_AGENT_MESSAGE="$msg" \
    HWP_AGENT_SESSION_ID="$session_id" \
    HWP_AGENT_ROUND="$round_num" \
    /bin/sh -c "$HWP_AGENT_CMD"
    return
  fi

  OPENCLAW_LOG_LEVEL=error "$HWP_AGENT_BIN" agent --message "$msg" --session-id "$session_id" --json
}
