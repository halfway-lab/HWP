#!/usr/bin/env bash
set -euo pipefail

# Hard-fail on jq errors (avoid truncated chains being treated as success)
JQ_SAFE() {
  jq "$@" || { echo "FATAL: jq failed" >&2; exit 1; }
}

# ---- args ----
INPUT_FILE="${1:-}"
if [ -z "${INPUT_FILE}" ]; then
  echo "错误：请指定输入文件路径"
  echo "用法: bash runs/run_sequential.sh inputs/probe.txt"
  exit 1
fi
if [ ! -f "${INPUT_FILE}" ]; then
  echo "错误：输入文件不存在: ${INPUT_FILE}"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$ROOT_DIR/logs"
SPEC_PROMPT="$ROOT_DIR/spec/hwp_turn_prompt.txt"

PROMPT_FINGERPRINT="$(grep -m1 '^PROMPT_FINGERPRINT:' "$SPEC_PROMPT" | sed -E 's/^PROMPT_FINGERPRINT:[[:space:]]*//')"
[ -z "${PROMPT_FINGERPRINT:-}" ] && PROMPT_FINGERPRINT="(missing)"

ROUNDS_PER_CHAIN="${HWP_ROUNDS_PER_CHAIN:-8}"
ROUND_SLEEP_SEC="${HWP_ROUND_SLEEP_SEC:-2}"

if ! [[ "$ROUNDS_PER_CHAIN" =~ ^[0-9]+$ ]] || [ "$ROUNDS_PER_CHAIN" -lt 1 ]; then
  echo "错误：HWP_ROUNDS_PER_CHAIN 必须是正整数，当前值: $ROUNDS_PER_CHAIN"
  exit 1
fi
mkdir -p "$LOG_DIR"

# ---- v0.6 dynamic controller ----
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
    if [ "$is_probe" = "1" ]; then echo "Rg1"; else echo "Rg0"; fi
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
while IFS= read -r line || [ -n "$line" ]; do
  [ -z "$line" ] && continue

  session_id="hwp_$(date +%s)_$RANDOM"
  log_file="$LOG_DIR/chain_${session_id}.jsonl"

  echo "开始链: $session_id，输入: $line" | tee -a "$LOG_DIR/run.log"
  echo "  PROMPT_FINGERPRINT: $PROMPT_FINGERPRINT" | tee -a "$LOG_DIR/run.log"

  # v0.6 controller state
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
    echo "  链 $session_id 第 $r 轮" | tee -a "$LOG_DIR/run.log"

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

    # 调用 OpenClaw（失败就直接 fail，不要吞掉）
    if ! raw_output=$(OPENCLAW_LOG_LEVEL=error openclaw agent --message "$msg" --session-id "$session_id" --json 2>/dev/null); then
      echo "FAIL: openclaw agent failed at round $r" | tee -a "$LOG_DIR/run.log"
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

    # 提取 result 部分（OpenClaw 返回 JSON 结构可能包含 .result）
    result_json=$(echo "$cleaned_json" | JQ_SAFE -c '.result // .')

    # 保存本轮完整输出到日志
    echo "$result_json" >> "$log_file"

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

      parent_vars="[]"
      parent_node=$(echo "$inner_json" | JQ_SAFE -r '.node_id')
      parent_recovery="true"

      prev_entropy="0.70"
      prev_drift="1.00"
      prev_collapse="true"
      prev_recovery="true"

      sleep "$ROUND_SLEEP_SEC"
      continue
    fi

    # payload.text 已经是 JSON object 文本，直接解析为对象
    inner_json=$(printf "%s" "$txt" | JQ_SAFE -c '.')

    parent_vars=$(echo "$inner_json" | JQ_SAFE -c '.variables // []')
    parent_node=$(echo "$inner_json" | JQ_SAFE -r '.node_id // "null"')
    parent_recovery=$(echo "$inner_json" | JQ_SAFE -r '.recovery_applied // "false"')

    # update controller state for next round
    prev_entropy=$(echo "$inner_json" | JQ_SAFE -r '.entropy_score // 0.70')
    prev_drift=$(echo "$inner_json" | JQ_SAFE -r '.drift_rate // 0.0')
    prev_collapse=$(echo "$inner_json" | JQ_SAFE -r '.collapse_detected // false')
    prev_recovery=$(echo "$inner_json" | JQ_SAFE -r '.recovery_applied // false')

    sleep "$ROUND_SLEEP_SEC"
  done

  echo "完成链: $session_id" | tee -a "$LOG_DIR/run.log"
done < "$INPUT_FILE"

echo "输入文件 $INPUT_FILE 处理完成。" | tee -a "$LOG_DIR/run.log"
