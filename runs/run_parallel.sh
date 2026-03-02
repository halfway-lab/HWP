#!/usr/bin/env bash
set -e

# 配置
INPUT_DIR="$HOME/hwp-tests/inputs"
LOG_DIR="$HOME/hwp-tests/logs"
SPEC_PROMPT="$HOME/hwp-tests/spec/hwp_turn_prompt.txt"
ROUNDS_PER_CHAIN=2          # 每条链的轮数
MAX_PARALLEL=1               # 同时运行的链数（根据服务器负载调整）

# 确保目录存在
mkdir -p "$LOG_DIR"

# 读取输入文件列表（假设输入文件每行一个测试主题）
INPUT_FILES=(
  "$INPUT_DIR/day1_inputs.txt"
  # 如果有更多文件，可以继续添加
)

# 清理函数，用于结束所有后台任务
cleanup() {
  echo "收到中断信号，正在清理后台进程..."
  pkill -P $$  # 杀死所有子进程
  exit 1
}
trap cleanup SIGINT SIGTERM

# 运行单条链的函数（参数：会话ID，输入文本，轮数）
run_chain() {
  local session_id="$1"
  local input_text="$2"
  local rounds="$3"
  local log_file="$LOG_DIR/chain_${session_id}.jsonl"

  echo "[$session_id] 开始运行，输入: $input_text"

  # 初始化父节点信息
  local parent_vars="[]"
  local parent_node="null"
  local parent_recovery="false"

  # 清空或创建日志文件
  > "$log_file"

  for ((r=1; r<=rounds; r++)); do
    # 构建消息，包含 meta 信息
    local msg="$(cat "$SPEC_PROMPT")

Meta:
- round: $r
- parent_node_id: $parent_node
- parent_recovery_applied: $parent_recovery
- parent_variables_json: $parent_vars
- input_text: $input_text

Now run Round $r."

    # 调用 OpenClaw，捕获输出（包含日志前缀）
    local raw_output
    raw_output=$(OPENCLAW_LOG_LEVEL=error openclaw agent --message "$msg" --session-id "$session_id" --json 2>/dev/null || true)

    # 清洗输出：去掉 ANSI 控制字符，提取第一个 { 开始的有效 JSON
    local cleaned_json
    cleaned_json=$(printf "%s\n" "$raw_output" \
      | sed -r 's/\x1B\[[0-9;]*[mK]//g' \
      | awk 'BEGIN{f=0}{ if(!f){ i=index($0,"{"); if(i){ f=1; print substr($0,i) } } else { print } }')

    if [ -z "$cleaned_json" ]; then
      echo "[$session_id] 警告：第 $r 轮返回空或无效 JSON，跳过本轮"
      continue
    fi

    # 提取 result 部分（假设真正的内容在 .result）
    local result_json
    result_json=$(echo "$cleaned_json" | jq -c '.result // .')

    # 保存到日志
    echo "$result_json" >> "$log_file"

    # 提取下一轮需要的字段
    parent_vars=$(echo "$result_json" | jq -c '.variables // []')
    parent_node=$(echo "$result_json" | jq -r '.node_id // "null"')
    parent_recovery=$(echo "$result_json" | jq -r '.recovery_applied // "false"')

    # 轻微节流，避免 API 限流
    sleep 2
  done

  echo "[$session_id] 完成，日志已保存到 $log_file"
}

# 并发控制：使用队列并行执行
for input_file in "${INPUT_FILES[@]}"; do
  if [ ! -f "$input_file" ]; then
    echo "警告：输入文件 $input_file 不存在，跳过"
    continue
  fi

  # 按行读取文件中的每个测试主题
  while IFS= read -r line || [ -n "$line" ]; do
    # 跳过空行
    [ -z "$line" ] && continue

    # 生成唯一的会话 ID（基于时间和随机数）
    session_id="hwp_$(date +%s)_$RANDOM"

    # 后台运行
    run_chain "$session_id" "$line" "$ROUNDS_PER_CHAIN" &

    # 限制并发数
    while [ $(jobs -p | wc -l) -ge $MAX_PARALLEL ]; do
      sleep 2
    done
  done < "$input_file"
done

# 等待所有后台任务完成
wait
echo "所有测试链已完成。日志文件在 $LOG_DIR"
