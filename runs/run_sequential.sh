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
HWP_AGENT_BIN="${HWP_AGENT_BIN:-openclaw}"

PROMPT_FINGERPRINT="$(grep -m1 '^PROMPT_FINGERPRINT:' "$SPEC_PROMPT" | sed -E 's/^PROMPT_FINGERPRINT:[[:space:]]*//')"
[ -z "${PROMPT_FINGERPRINT:-}" ] && PROMPT_FINGERPRINT="(missing)"

ROUND_SLEEP_SEC="${HWP_ROUND_SLEEP_SEC:-2}"
ROUNDS_PER_CHAIN=8
if ! awk -v x="$ROUND_SLEEP_SEC" 'BEGIN{exit !(x ~ /^[0-9]+([.][0-9]+)?$/)}'; then
  echo "错误：HWP_ROUND_SLEEP_SEC 必须是非负数字，当前值: $ROUND_SLEEP_SEC"
  exit 1
fi
mkdir -p "$LOG_DIR"

enrich_v06_inner_json() {
  local inner_json="$1"
  local round="$2"
  local parent_recovery_flag="$3"

  local parent_recovery_json="false"
  if [ "$parent_recovery_flag" = "true" ]; then
    parent_recovery_json="true"
  fi

  printf '%s' "$inner_json" | JQ_SAFE -c \
    --arg round_id "round_${round}" \
    --argjson parent_recovery_applied "$parent_recovery_json" '
    def clamp01:
      if . < 0 then 0
      elif . > 1 then 1
      else .
      end;

    def tension_id($idx; $value):
      if ($value | type) == "object" and ($value.id? // "") != "" then $value.id
      elif ($idx + 1) < 10 then "tension_0" + (($idx + 1) | tostring)
      else "tension_" + (($idx + 1) | tostring)
      end;

    def normalize_tensions:
      [(.tensions // []) | to_entries[] |
        {
          id: tension_id(.key; .value),
          description:
            (if (.value | type) == "object"
             then (.value.description // .value.id // ("Tension " + ((.key + 1) | tostring)))
             else (.value | tostring)
             end),
          status:
            (if (.value | type) == "object"
             then (.value.status // "active")
             else "active"
             end)
        }
      ];

    def severity_from_impact($impact):
      if (($impact // "") | ascii_downcase | test("critical|severe|irreversible|fundamental"))
      then "high"
      else "medium"
      end;

    def blind_spot_signals_from_paths:
      [(.paths // [])[]? |
        select((.blind_spot.description? // "") != "") |
        {
          type: "information_gap",
          description: .blind_spot.description,
          severity: severity_from_impact(.blind_spot.impact // "")
        }
      ];

    def blind_spot_score_from_signals($signals):
      if ($signals | length) == 0 then 0
      else ([ $signals[] | if .severity == "high" then 0.30 else 0.18 end ] | add | clamp01)
      end;

    def semantic_group_id($variables):
      if ($variables | length) == 0 then "sg_empty"
      else "sg_" + (($variables[0] | tostring | ascii_downcase | gsub("[^a-z0-9]+"; "_")) | sub("^_+"; "") | sub("_+$"; ""))
      end;

    def semantic_nodes($variables):
      [ $variables | to_entries[] |
        {
          node_id: ("var_node_" + ((.key + 1) | tostring)),
          content: .value,
          similarity_score: (((100 - .key) / 100) | if . < 0.55 then 0.55 else . end),
          parent_node: (if .key == 0 then null else ("var_node_" + (.key | tostring)) end)
        }
      ];

    def semantic_group_payload($variables; $round; $drift; $shared):
      if ($variables | length) == 0 then []
      else
        [
          {
            group_id: semantic_group_id($variables),
            group_name: "Primary Exploration Cluster",
            nodes: semantic_nodes($variables),
            coherence_score: ((1 - ($drift / 2)) | clamp01),
            expansion_path: [range(0; ($variables | length)) | ("var_node_" + (. + 1 | tostring))],
            domain: "exploration",
            group_metadata: {
              created_round: 1,
              last_expanded_round: $round,
              expansion_count: ($round - 1),
              identifier_stable: ($shared >= 10)
            }
          }
        ]
      end;

    normalize_tensions as $normalized_tensions
    | blind_spot_signals_from_paths as $derived_signals
    | .tensions = $normalized_tensions
    | if has("blind_spot_signals") then . else .blind_spot_signals = $derived_signals end
    | if has("blind_spot_score") then . else .blind_spot_score = blind_spot_score_from_signals(.blind_spot_signals) end
    | if has("blind_spot_reason") then .
      else .blind_spot_reason =
        (if (.blind_spot_signals | length) == 0
         then ""
         else ("Detected " + ((.blind_spot_signals | length) | tostring) + " blind spot signals across current exploration paths")
         end)
      end
    | if has("semantic_groups") then .
      else .semantic_groups = semantic_group_payload((.variables // []); (.round // 1); (.drift_rate // 0.35); (.shared_variable_count // 0))
      end
    | if has("group_count") then . else .group_count = (.semantic_groups | length) end
    | if has("cross_domain_contamination") then . else .cross_domain_contamination = false end
    | if has("round_id") then . else .round_id = $round_id end
    | if has("continuity_score") then .
      else .continuity_score =
        (if (.parent_id // null) == null
         then 1
         else ((.shared_variable_count // 0) / ((.variables // []) | length)) | clamp01
         end)
      end
    | if has("state_snapshot") then .
      else .state_snapshot = {
        inherited_variable_count: (.shared_variable_count // 0),
        active_tension_ids: [(.tensions // [])[] | .id],
        parent_recovery_applied: $parent_recovery_applied,
        continuity_notes:
          (if (.parent_id // null) == null
           then ["Initial round establishes baseline state snapshot"]
           else [
             ("Inherited " + ((.shared_variable_count // 0) | tostring) + " variables from parent"),
             ("Maintained " + ((.tensions // []) | length | tostring) + " active tensions into current round")
           ] + (if $parent_recovery_applied then ["Parent round used recovery; stabilization continuity applied"] else [] end)
           end)
      }
      end
    '
}

repack_result_with_inner() {
  local result_json="$1"
  local inner_json="$2"
  printf '%s' "$result_json" | JQ_SAFE -c --arg inner "$inner_json" '
    ($inner | fromjson) as $parsed
    |
    .payloads = (
      if (.payloads // []) | length > 0
      then (.payloads | .[0].text = $inner)
      else [{text: $inner, mediaUrl: null}]
      end
    )
    | .round = ($parsed.round // .round // null)
    | .round_id = ($parsed.round_id // .round_id // null)
    | .blind_spot_signals = ($parsed.blind_spot_signals // [])
    | .blind_spot_score = ($parsed.blind_spot_score // 0)
    | .blind_spot_reason = ($parsed.blind_spot_reason // "")
    | .semantic_groups = ($parsed.semantic_groups // [])
    | .group_count = ($parsed.group_count // 0)
    | .semantic_coherence = (
        if (($parsed.semantic_groups // []) | length) > 0
        then ($parsed.semantic_groups[0].coherence_score // null)
        else null
        end
      )
    | .continuity_score = ($parsed.continuity_score // null)
    | .state_snapshot = ($parsed.state_snapshot // {})
  '
}

require_agent_bin() {
  if ! command -v "$HWP_AGENT_BIN" >/dev/null 2>&1; then
    echo "错误：未找到 agent 命令: $HWP_AGENT_BIN" >&2
    echo "请先安装/配置 OpenClaw，或通过 HWP_AGENT_BIN 指定可执行文件路径。" >&2
    exit 1
  fi
}

# ---- v0.5.3 dynamic controller ----
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
require_agent_bin
while IFS= read -r line || [ -n "$line" ]; do
  [ -z "$line" ] && continue

  session_id="hwp_$(date +%s)_$RANDOM"
  log_file="$LOG_DIR/chain_${session_id}.jsonl"

  echo "开始链: ${session_id}，输入: ${line}" | tee -a "$LOG_DIR/run.log"
  echo "  PROMPT_FINGERPRINT: $PROMPT_FINGERPRINT" | tee -a "$LOG_DIR/run.log"

  # v0.5.3 controller state
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

    # 调用 OpenClaw（失败就直接 fail，不要吞掉）
    if ! raw_output=$(OPENCLAW_LOG_LEVEL=error "$HWP_AGENT_BIN" agent --message "$msg" --session-id "$session_id" --json 2>/dev/null); then
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

    sleep "$ROUND_SLEEP_SEC"
  done

  echo "完成链: $session_id" | tee -a "$LOG_DIR/run.log"
done < "$INPUT_FILE"

echo "输入文件 $INPUT_FILE 处理完成。" | tee -a "$LOG_DIR/run.log"
