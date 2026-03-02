#!/usr/bin/env bash
set -euo pipefail

# 输出路径
OUT="$HOME/hwp-tests/logs/day1_chain1.jsonl"

# 读取基本的 Prompt 模板
PROMPT_BASE="$(cat $HOME/hwp-tests/spec/hwp_turn_prompt.txt)"

# 会话 ID，避免冲突
SESSION_ID="hwp-day1-chain1"

# 初始变量
PARENT_VARS="[]"
PARENT_NODE="null"
PARENT_RECOVERY="false"

# 清空输出文件（如果已经存在）
: > "$OUT"

# 运行 8 轮
for ROUND in $(seq 1 8); do
  # 创建每一轮的消息
  MSG=$(cat <<EOF
$PROMPT_BASE

Meta:
- round: $ROUND
- parent_node_id: $PARENT_NODE
- parent_recovery_applied: $PARENT_RECOVERY
- parent_variables_json: $PARENT_VARS

Now run Round $ROUND.
EOF
)

  RAW=$(OPENCLAW_LOG_LEVEL=error openclaw agent --message "$MSG" --session-id "$SESSION_ID" --json 2>/dev/null || true)

# 1) 去掉 ANSI 控制字符（万一有彩色）
# 2) 从第一個 { 开始截取，剥离前置日志行
JSON_CLEAN=$(printf "%s\n" "$RAW" \
  | sed -r 's/\x1B\[[0-9;]*[mK]//g' \
  | awk 'BEGIN{f=0}{ if(!f){ i=index($0,"{"); if(i){ f=1; print substr($0,i) } } else { print } }')

# 防御：如果清洗后为空，直接报错退出
if [ -z "$JSON_CLEAN" ]; then
  echo "ERROR: openclaw returned empty output after cleaning." >&2
  echo "RAW was:" >&2
  printf "%s\n" "$RAW" >&2
  exit 1
fi

# 现在 JSON_CLEAN 才是纯 JSON，可以给 jq
RESP_JSON=$(echo "$JSON_CLEAN" | jq -c '.result')

  # 追加到日志文件
  echo "$RESP_JSON" >> "$OUT"

  # 用 jq 提取本轮 variables / node_id / recovery_applied 给下一轮
  VARS=$(echo "$RESP_JSON" | jq -c '.variables // []')
  NODE=$(echo "$RESP_JSON" | jq -r '.node_id // "null"')
  REC=$(echo "$RESP_JSON" | jq -r '.recovery_applied // "false"')

  # 设置下一轮的 parent 信息
  PARENT_VARS="$VARS"
  PARENT_NODE="$NODE"
  PARENT_RECOVERY="$REC"

  # 轻微节流，防止打爆接口
  sleep 2
done

echo "DONE. Log saved to: $OUT"
