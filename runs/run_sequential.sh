#!/usr/bin/env bash
set -euo pipefail

# Hard-fail on jq/python errors (avoid truncated chains being treated as success)
JQ_SAFE() {
  jq "$@" || { echo "FATAL: jq failed" >&2; exit 1; }
}

PYTHON_SAFE() {
  python3 "$@" || { echo "FATAL: python materializer failed" >&2; exit 1; }
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/lib_agent.sh"

# ---- args ----
usage() {
  echo "用法: bash runs/run_sequential.sh [--config PATH] [--provider-type TYPE] [--provider-name NAME] [--agent-bin PATH] [--agent-cmd CMD] [--replay-chain PATH] [--dry-run] inputs/probe.txt"
}

parse_hwp_provider_args "$@"
if [ -n "${HWP_SHOW_HELP:-}" ]; then
  usage
  exit 0
fi
if [ -z "${HWP_DRY_RUN:-}" ] && [ "${HWP_INPUT_FILE:-}" = "" ]; then
  usage
  exit 1
fi
INPUT_FILE="$HWP_INPUT_FILE"

ROOT_FROM_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
resolve_hwp_provider_settings "$ROOT_FROM_SCRIPT"
if [ -n "${HWP_DRY_RUN:-}" ]; then
  print_hwp_provider_summary
  validate_hwp_provider_setup
  print_hwp_provider_warnings
  echo "Dry run OK: provider configuration is ready."
  exit 0
fi

if [ -z "${INPUT_FILE}" ]; then
  echo "错误：请指定输入文件路径"
  usage
  exit 1
fi
if [ ! -f "${INPUT_FILE}" ]; then
  echo "错误：输入文件不存在: ${INPUT_FILE}"
  exit 1
fi

LOG_DIR="$ROOT_DIR/logs"
SPEC_PROMPT="$ROOT_DIR/spec/hwp_turn_prompt.txt"

PROMPT_FINGERPRINT="$(grep -m1 '^PROMPT_FINGERPRINT:' "$SPEC_PROMPT" | sed -E 's/^PROMPT_FINGERPRINT:[[:space:]]*//')"
[ -z "${PROMPT_FINGERPRINT:-}" ] && PROMPT_FINGERPRINT="(missing)"

ROUND_SLEEP_SEC="${HWP_ROUND_SLEEP_SEC:-2}"
CHAIN_TIMEOUT_SEC="${HWP_CHAIN_TIMEOUT_SEC:-0}"
ROUNDS_PER_CHAIN=8
if ! awk -v x="$ROUND_SLEEP_SEC" 'BEGIN{exit !(x ~ /^[0-9]+([.][0-9]+)?$/)}'; then
  echo "错误：HWP_ROUND_SLEEP_SEC 必须是非负数字，当前值: $ROUND_SLEEP_SEC"
  exit 1
fi
if ! awk -v x="$CHAIN_TIMEOUT_SEC" 'BEGIN{exit !(x ~ /^[0-9]+([.][0-9]+)?$/)}'; then
  echo "错误：HWP_CHAIN_TIMEOUT_SEC 必须是非负数字，当前值: $CHAIN_TIMEOUT_SEC"
  exit 1
fi
mkdir -p "$LOG_DIR"

now_epoch() {
  python3 - <<'PY'
import time
print(time.time())
PY
}

elapsed_sec() {
  local start_ts="$1"
  local end_ts="${2:-$(now_epoch)}"
  awk -v start="$start_ts" -v end="$end_ts" 'BEGIN{printf "%.2f", (end - start)}'
}

sum_sec() {
  local left="$1"
  local right="$2"
  awk -v left="$left" -v right="$right" 'BEGIN{printf "%.2f", (left + right)}'
}

max_sec() {
  local left="$1"
  local right="$2"
  awk -v left="$left" -v right="$right" 'BEGIN{printf "%.2f", (left > right ? left : right)}'
}

avg_sec() {
  local total="$1"
  local count="$2"
  awk -v total="$total" -v count="$count" 'BEGIN{printf "%.2f", (count > 0 ? total / count : 0)}'
}

timeout_exceeded() {
  local start_ts="$1"
  local timeout_sec="$2"
  local now_ts="${3:-$(now_epoch)}"
  awk -v start="$start_ts" -v timeout="$timeout_sec" -v now="$now_ts" 'BEGIN{exit !(timeout > 0 && (now - start) >= timeout)}'
}

enrich_v06_inner_json() {
  local inner_json="$1"
  local round="$2"
  local parent_recovery_flag="$3"
  PYTHON_SAFE -m hwp_protocol.cli transform enrich "$inner_json" "$round" "$parent_recovery_flag"
}

repack_result_with_inner() {
  local result_json="$1"
  local inner_json="$2"
  PYTHON_SAFE -m hwp_protocol.cli transform repack "$result_json" "$inner_json"
}

load_replay_result_json() {
  local replay_path="$1"
  local round="$2"
  local replay_line

  replay_line="$(sed -n "${round}p" "$replay_path")"
  if [ -z "$replay_line" ]; then
    echo "错误：回放链在第 ${round} 轮缺少数据: $replay_path" >&2
    exit 1
  fi

  printf '%s' "$replay_line" | JQ_SAFE -c '.result // .'
}

# ---- baseline dynamic controller compatibility layer ----
emit_hint_json() {
  # args: mode min max keep_n new_n max_vars
  local mode="$1" mn="$2" mx="$3" keep_n="$4" new_n="$5" max_vars="$6"
  printf '{"mode":"%s","entropy_target":{"min":%s,"max":%s},"variable_policy":{"keep_n":%s,"new_n":%s,"max_vars":%s,"keep_prefix":true}}' \
    "$mode" "$mn" "$mx" "$keep_n" "$new_n" "$max_vars"
}

# Floating compare helpers (return 0 if true)
f_gt() { awk -v a="$1" -v b="$2" 'BEGIN{exit !(a>b)}'; }
f_lt() { awk -v a="$1" -v b="$2" 'BEGIN{exit !(a<b)}'; }

compute_mode() {
  # args: round is_probe prev_entropy prev_drift prev_collapse prev_recovery
  local round="$1" is_probe="$2" pe="$3" pd="$4" pc="$5" pr="$6"

  if [ "$round" -eq 1 ]; then
    echo "Rg0"
    return
  fi

  # Stabilize immediately after collapse/recovery
  if [ "$pc" = "true" ] || [ "$pr" = "true" ]; then
    echo "Rg0"; return
  fi

  # High drift -> slow/stabilize
  if f_gt "$pd" "0.55"; then
    echo "Rg0"; return
  fi

  # Entropy too high -> slow
  if f_gt "$pe" "0.88"; then
    echo "Rg0"; return
  fi

  # Entropy too low -> inject novelty
  if f_lt "$pe" "0.45"; then
    echo "Rg2"; return
  fi

  echo "Rg1"
}

compute_band() {
  # args: mode -> prints "min max"
  local mode="$1"
  case "$mode" in
    Rg0) echo "0.35 0.92" ;;
    Rg1) echo "0.50 0.92" ;;
    Rg2) echo "0.25 0.80" ;;
    *)   echo "0.35 0.92" ;;
  esac
}

# 读取输入文件，每行一条测试链
require_hwp_agent_provider "$HWP_REPLAY_CHAIN_PATH"
while IFS= read -r line || [ -n "$line" ]; do
  [ -z "$line" ] && continue

  session_id="hwp_$(date +%s)_$RANDOM"
  log_file="$LOG_DIR/chain_${session_id}.jsonl"
  chain_start_ts="$(now_epoch)"
  completed_rounds=0
  total_round_sec="0.00"
  max_round_sec="0.00"

  echo "开始链: ${session_id}，输入: ${line}" | tee -a "$LOG_DIR/run.log"
  echo "  PROMPT_FINGERPRINT: $PROMPT_FINGERPRINT" | tee -a "$LOG_DIR/run.log"
  if f_gt "$CHAIN_TIMEOUT_SEC" "0"; then
    echo "  CHAIN_TIMEOUT_SEC: $CHAIN_TIMEOUT_SEC" | tee -a "$LOG_DIR/run.log"
  fi

  # baseline controller state reused by the v0.6 RC2 runner
  base_line="$line"
  # prevent conflicts if user left RHYTHM_HINT in input accidentally
  base_line="$(printf "%s" "$base_line" | sed 's/RHYTHM_HINT=/RHYTHM_HINT_DISABLED=/g')"

  is_probe="0"
  if echo "$base_line" | grep -q 'COLLAPSE_PROBE=1'; then is_probe="1"; fi

  prev_entropy="0.70"
  prev_drift="0.00"
  prev_collapse="false"
  prev_recovery="false"

  parent_vars="[]"
  parent_node="null"
  parent_recovery="false"

  > "$log_file"

  for ((r=1; r<=ROUNDS_PER_CHAIN; r++)); do
    if timeout_exceeded "$chain_start_ts" "$CHAIN_TIMEOUT_SEC"; then
      chain_elapsed="$(elapsed_sec "$chain_start_ts")"
      echo "TIMEOUT: chain ${session_id} exceeded HWP_CHAIN_TIMEOUT_SEC=${CHAIN_TIMEOUT_SEC}s before round ${r} (elapsed=${chain_elapsed}s)" | tee -a "$LOG_DIR/run.log"
      exit 1
    fi

    round_start_ts="$(now_epoch)"
    echo "  链 ${session_id} 第 ${r} 轮" | tee -a "$LOG_DIR/run.log"

    mode="$(compute_mode "$r" "$is_probe" "$prev_entropy" "$prev_drift" "$prev_collapse" "$prev_recovery")"
    read -r et_min et_max < <(compute_band "$mode")
    hint_json="$(emit_hint_json "$mode" "$et_min" "$et_max" "20" "10" "30")"

    # Make input_text start with RHYTHM_HINT=... (prompt rule expects it)
    input_with_hint="RHYTHM_HINT=$hint_json $base_line"
    echo "    [controller] $input_with_hint" | tee -a "$LOG_DIR/run.log"

    msg="$(cat "$SPEC_PROMPT")

Meta:
- round: $r
- parent_node_id: $parent_node
- parent_recovery_applied: $parent_recovery
- parent_variables_json: $parent_vars
- input_text: $input_with_hint

Now run Round $r."

    if [ -n "$HWP_REPLAY_CHAIN_PATH" ]; then
      echo "    [replay] using $HWP_REPLAY_CHAIN_PATH round $r" | tee -a "$LOG_DIR/run.log"
      result_json="$(load_replay_result_json "$HWP_REPLAY_CHAIN_PATH" "$r")"
    else
      # 调用 agent provider（默认兼容 OpenClaw；也可接入自定义模型适配器）
      if ! raw_output=$(invoke_hwp_agent "$msg" "$session_id" "$r" 2>/dev/null); then
        echo "FAIL: agent provider failed at round $r" | tee -a "$LOG_DIR/run.log"
        exit 1
      fi

      # 清洗输出：去掉 ANSI 控制字符，提取第一个 { 开始的有效 JSON
      cleaned_json=$(printf "%s\n" "$raw_output" \
        | sed -r 's/\x1B\[[0-9;]*[mK]//g' \
        | awk 'BEGIN{f=0}{ if(!f){ i=index($0,"{"); if(i){ f=1; print substr($0,i) } } else { print } }')

      if [ -z "$cleaned_json" ]; then
        echo "FAIL: empty response after cleaning at round $r" | tee -a "$LOG_DIR/run.log"
        exit 1
      fi

      # 提取 result 部分（兼容 OpenClaw / 自定义适配器返回的 .result 包装）
      result_json=$(echo "$cleaned_json" | JQ_SAFE -c '.result // .')
    fi

    # 提取 payload.text（应是内层 round JSON）
    txt=$(echo "$result_json" | JQ_SAFE -r '.payloads[0].text // ""')

    # provider block / 非 JSON：写 fallback（并且确保 fallback 自身可被 verify 解析）
    if [[ "$txt" != \{* ]]; then
      echo "  警告：第 $r 轮 payload.text 不是 JSON（可能被内容审查拦截），写入 fallback 并继续" | tee -a "$LOG_DIR/run.log"
      echo "  SNIP: ${txt:0:140}" | tee -a "$LOG_DIR/run.log"

      inner_json=$(JQ_SAFE -nc \
        --arg node "HWP_FALLBACK_R${r}_$(date +%Y%m%dT%H%M%S)" \
        --arg parent "$parent_node" \
        --argjson round "$r" \
        --arg snip "${txt:0:140}" \
        --arg hint "$hint_json" \
        '{
          node_id:$node,
          parent_id:(if $parent == "null" then null else $parent end),
          round:$round,
          questions:[],
          variables:[],
          paths:[],
          tensions:[],
          unfinished:[],
          entropy_score:0,
          novelty_rate:0,
          shared_variable_count:0,
          drift_rate:1,
          collapse_detected:true,
          recovery_applied:true,
          speed_metrics:{mode:"Rg0", unfinished_inherited_count:0, action_taken:["provider_audit_block_fallback"]},
          rhythm:{
            mode:"Rg0",
            entropy_target:{min:0.0,max:1.0},
            variable_policy:{keep_n:0,new_n:0,max_vars:0,keep_prefix:true},
            hint:(($hint|fromjson)),
            hint_applied:true
          },
          provider_block_snip:$snip
        }')

      inner_json="$(enrich_v06_inner_json "$inner_json" "$r" "$parent_recovery")"
      result_json="$(repack_result_with_inner "$result_json" "$inner_json")"
      echo "$result_json" >> "$log_file"

      parent_vars=$(echo "$inner_json" | JQ_SAFE -c '.variables // []')
      parent_node=$(echo "$inner_json" | JQ_SAFE -r '.node_id')
      parent_recovery="true"

      prev_entropy="0.70"
      prev_drift="1.00"
      prev_collapse="true"
      prev_recovery="true"
      round_elapsed="$(elapsed_sec "$round_start_ts")"
      chain_elapsed="$(elapsed_sec "$chain_start_ts")"
      completed_rounds=$((completed_rounds + 1))
      total_round_sec="$(sum_sec "$total_round_sec" "$round_elapsed")"
      max_round_sec="$(max_sec "$max_round_sec" "$round_elapsed")"
      echo "    [timing] round_sec=${round_elapsed} chain_sec=${chain_elapsed}" | tee -a "$LOG_DIR/run.log"

      if timeout_exceeded "$chain_start_ts" "$CHAIN_TIMEOUT_SEC"; then
        echo "TIMEOUT: chain ${session_id} exceeded HWP_CHAIN_TIMEOUT_SEC=${CHAIN_TIMEOUT_SEC}s after round ${r} (elapsed=${chain_elapsed}s)" | tee -a "$LOG_DIR/run.log"
        echo "  [summary] session_id=${session_id} rounds_completed=${completed_rounds} round_avg_sec=$(avg_sec "$total_round_sec" "$completed_rounds") round_max_sec=${max_round_sec} chain_sec=${chain_elapsed}" | tee -a "$LOG_DIR/run.log"
        exit 1
      fi

      sleep "$ROUND_SLEEP_SEC"
      continue
    fi

    # payload.text 已经是 JSON object 文本，直接解析为对象
    inner_json=$(printf "%s" "$txt" | JQ_SAFE -c '.')
    inner_json="$(enrich_v06_inner_json "$inner_json" "$r" "$parent_recovery")"
    result_json="$(repack_result_with_inner "$result_json" "$inner_json")"
    echo "$result_json" >> "$log_file"

    parent_vars=$(echo "$inner_json" | JQ_SAFE -c '.variables // []')
    parent_node=$(echo "$inner_json" | JQ_SAFE -r '.node_id // "null"')
    parent_recovery=$(echo "$inner_json" | JQ_SAFE -r '.recovery_applied // "false"')

    # update controller state for next round
    prev_entropy=$(echo "$inner_json" | JQ_SAFE -r '.entropy_score // 0.70')
    prev_drift=$(echo "$inner_json" | JQ_SAFE -r '.drift_rate // 0.0')
    prev_collapse=$(echo "$inner_json" | JQ_SAFE -r '.collapse_detected // false')
    prev_recovery=$(echo "$inner_json" | JQ_SAFE -r '.recovery_applied // false')
    round_elapsed="$(elapsed_sec "$round_start_ts")"
    chain_elapsed="$(elapsed_sec "$chain_start_ts")"
    completed_rounds=$((completed_rounds + 1))
    total_round_sec="$(sum_sec "$total_round_sec" "$round_elapsed")"
    max_round_sec="$(max_sec "$max_round_sec" "$round_elapsed")"
    echo "    [timing] round_sec=${round_elapsed} chain_sec=${chain_elapsed}" | tee -a "$LOG_DIR/run.log"

    if timeout_exceeded "$chain_start_ts" "$CHAIN_TIMEOUT_SEC"; then
      echo "TIMEOUT: chain ${session_id} exceeded HWP_CHAIN_TIMEOUT_SEC=${CHAIN_TIMEOUT_SEC}s after round ${r} (elapsed=${chain_elapsed}s)" | tee -a "$LOG_DIR/run.log"
      echo "  [summary] session_id=${session_id} rounds_completed=${completed_rounds} round_avg_sec=$(avg_sec "$total_round_sec" "$completed_rounds") round_max_sec=${max_round_sec} chain_sec=${chain_elapsed}" | tee -a "$LOG_DIR/run.log"
      exit 1
    fi

    sleep "$ROUND_SLEEP_SEC"
  done

  chain_elapsed="$(elapsed_sec "$chain_start_ts")"
  round_avg_sec="$(avg_sec "$total_round_sec" "$completed_rounds")"
  echo "  [summary] session_id=${session_id} rounds_completed=${completed_rounds} round_avg_sec=${round_avg_sec} round_max_sec=${max_round_sec} chain_sec=${chain_elapsed}" | tee -a "$LOG_DIR/run.log"
  echo "完成链: $session_id (rounds=${ROUNDS_PER_CHAIN}, elapsed_sec=${chain_elapsed})" | tee -a "$LOG_DIR/run.log"
done < "$INPUT_FILE"

echo "输入文件 $INPUT_FILE 处理完成。" | tee -a "$LOG_DIR/run.log"
