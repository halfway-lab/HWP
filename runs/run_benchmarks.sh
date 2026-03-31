#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BENCHMARK_FILE="${1:-$ROOT_DIR/config/benchmark_inputs.txt}"
REPORT_ROOT="${HWP_BENCHMARK_REPORT_ROOT:-$ROOT_DIR/reports/benchmarks}"
TIMESTAMP="$(date +%Y%m%dT%H%M%S)"
REPORT_DIR="$REPORT_ROOT/$TIMESTAMP"
RESULTS_TSV="$REPORT_DIR/results.tsv"
SUMMARY_MD="$REPORT_DIR/summary.md"
OVERVIEW_MD="$REPORT_DIR/overview.md"
OVERVIEW_TSV="$REPORT_DIR/overview.tsv"
RUN_LOG="$REPORT_DIR/run.log"
PROVIDER_TYPE="${HWP_PROVIDER_TYPE:-}"
PROVIDER_NAME="${HWP_PROVIDER_NAME:-}"

mkdir -p "$REPORT_DIR"

if [ ! -f "$BENCHMARK_FILE" ]; then
  echo "错误：benchmark 清单不存在: $BENCHMARK_FILE" >&2
  exit 1
fi

if [ -z "$PROVIDER_TYPE" ] && [ -f "$ROOT_DIR/config/provider.env" ]; then
  PROVIDER_TYPE="$(grep -m1 '^HWP_PROVIDER_TYPE=' "$ROOT_DIR/config/provider.env" | cut -d= -f2- || true)"
fi
if [ -z "$PROVIDER_NAME" ] && [ -f "$ROOT_DIR/config/provider.env" ]; then
  PROVIDER_NAME="$(grep -m1 '^HWP_PROVIDER_NAME=' "$ROOT_DIR/config/provider.env" | cut -d= -f2- || true)"
fi

{
  echo "benchmark_file=$BENCHMARK_FILE"
  echo "provider_type=${PROVIDER_TYPE:-unknown}"
  echo "provider_name=${PROVIDER_NAME:-unknown}"
  echo "report_dir=$REPORT_DIR"
  echo "started_at=$TIMESTAMP"
} > "$REPORT_DIR/context.txt"

echo -e "benchmark\tinput_path\tprovider_type\tprovider_name\trun_status\trun_exit_code\tduration_sec\tfailure_reason\tlog_count\tstructured\tstructured_reason\tblind_spot\tblind_spot_reason\tcontinuity\tcontinuity_reason\tsemantic_groups\tsemantic_groups_reason\treport_dir" > "$RESULTS_TSV"

list_chain_logs() {
  find "$ROOT_DIR/logs" -maxdepth 1 -name 'chain_*.jsonl' -type f 2>/dev/null | sort
}

extract_session_ids() {
  local run_output_path="$1"
  if [ ! -f "$run_output_path" ]; then
    return 0
  fi
  grep '^开始链:' "$run_output_path" | sed -E 's/^开始链: ([^，,]+).*/\1/' | sort -u
}

run_verifier() {
  local script_name="$1"
  local logs_dir="$2"
  local out_path="$3"

  if [ ! -d "$logs_dir" ] || [ -z "$(find "$logs_dir" -maxdepth 1 -name '*.jsonl' -type f -print -quit 2>/dev/null)" ]; then
    printf 'skipped'
    return
  fi

  if bash "$ROOT_DIR/runs/$script_name" "$logs_dir" > "$out_path" 2>&1; then
    printf 'pass'
  else
    printf 'fail'
  fi
}

extract_verifier_reason() {
  local verifier_status="$1"
  local log_path="$2"

  if [ "$verifier_status" != "fail" ] || [ ! -f "$log_path" ]; then
    printf ''
    return
  fi

  grep -m1 '\[FAIL\]' "$log_path" \
    | sed -E 's/\x1B\[[0-9;]*[mK]//g' \
    | sed -E 's/^.*\[FAIL\][[:space:]]*//' \
    || true
}

extract_failure_reason() {
  local run_output_path="$1"
  if [ ! -f "$run_output_path" ]; then
    printf 'unknown'
    return
  fi

  if grep -q 'FAIL: agent provider failed' "$run_output_path"; then
    printf 'agent_provider_failed'
  elif grep -q 'FAIL: empty response after cleaning' "$run_output_path"; then
    printf 'empty_response_after_cleaning'
  elif grep -q 'payload.text 不是 JSON' "$run_output_path"; then
    printf 'payload_not_json'
  elif grep -q '错误：未找到 agent 命令' "$run_output_path"; then
    printf 'agent_command_missing'
  else
    printf 'unknown'
  fi
}

while IFS= read -r input_path || [ -n "$input_path" ]; do
  [ -z "$input_path" ] && continue
  case "$input_path" in
    \#*) continue ;;
  esac

  benchmark_name="$(basename "$input_path" .txt)"
  bench_dir="$REPORT_DIR/$benchmark_name"
  bench_logs_dir="$bench_dir/logs"
  mkdir -p "$bench_logs_dir"

  run_status="pass"
  run_exit_code=0
  failure_reason=""
  start_time="$(date +%s)"
  if (cd "$ROOT_DIR" && bash runs/run_sequential.sh "$input_path" > "$bench_dir/run_output.log" 2>&1); then
    run_exit_code=0
  else
    run_exit_code=$?
    run_status="fail"
    failure_reason="$(extract_failure_reason "$bench_dir/run_output.log")"
  fi
  end_time="$(date +%s)"
  duration_sec=$((end_time - start_time))
  session_file="$bench_dir/session_ids.txt"
  extract_session_ids "$bench_dir/run_output.log" > "$session_file"
  log_count=0
  while IFS= read -r session_id || [ -n "$session_id" ]; do
    [ -z "$session_id" ] && continue
    log_path="$ROOT_DIR/logs/chain_${session_id}.jsonl"
    if [ -f "$log_path" ]; then
      cp "$log_path" "$bench_logs_dir/"
      log_count=$((log_count + 1))
    fi
  done < "$session_file"

  # 结构化验证（第2步新增）
  structured_status="$(run_verifier "verify_structured.sh" "$bench_logs_dir" "$bench_dir/verify_structured.log")"
  structured_reason="$(extract_verifier_reason "$structured_status" "$bench_dir/verify_structured.log")"
  
  blind_status="$(run_verifier "verify_v06_blind_spot.sh" "$bench_logs_dir" "$bench_dir/verify_blind_spot.log")"
  blind_reason="$(extract_verifier_reason "$blind_status" "$bench_dir/verify_blind_spot.log")"
  continuity_status="$(run_verifier "verify_v06_continuity.sh" "$bench_logs_dir" "$bench_dir/verify_continuity.log")"
  continuity_reason="$(extract_verifier_reason "$continuity_status" "$bench_dir/verify_continuity.log")"
  semantic_status="$(run_verifier "verify_v06_semantic_groups.sh" "$bench_logs_dir" "$bench_dir/verify_semantic_groups.log")"
  semantic_reason="$(extract_verifier_reason "$semantic_status" "$bench_dir/verify_semantic_groups.log")"

  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$benchmark_name" \
    "$input_path" \
    "${PROVIDER_TYPE:-unknown}" \
    "${PROVIDER_NAME:-unknown}" \
    "$run_status" \
    "$run_exit_code" \
    "$duration_sec" \
    "${failure_reason:-}" \
    "$log_count" \
    "$structured_status" \
    "${structured_reason:-}" \
    "$blind_status" \
    "${blind_reason:-}" \
    "$continuity_status" \
    "${continuity_reason:-}" \
    "$semantic_status" \
    "${semantic_reason:-}" \
    "$bench_dir" >> "$RESULTS_TSV"

  {
    echo "[$benchmark_name] run_status=$run_status run_exit_code=$run_exit_code duration_sec=$duration_sec logs=$log_count"
    echo "[$benchmark_name] structured=$structured_status blind_spot=$blind_status continuity=$continuity_status semantic_groups=$semantic_status"
  } | tee -a "$RUN_LOG"
done < "$BENCHMARK_FILE"

python3 "$ROOT_DIR/runs/report_benchmarks.py" "$RESULTS_TSV" "$SUMMARY_MD" > "$REPORT_DIR/summary_path.txt"
python3 "$ROOT_DIR/runs/report_benchmark_overview.py" \
  "$RESULTS_TSV" \
  "$REPORT_DIR/context.txt" \
  "$ROOT_DIR/logs/run.log" \
  "$OVERVIEW_MD" \
  "$OVERVIEW_TSV" > "$REPORT_DIR/overview_path.txt"

# 生成回归报告（第5步新增）
echo ""
echo "Generating regression report..."
python3 "$ROOT_DIR/runs/report_regression.py" "$REPORT_DIR" "$REPORT_DIR/regression.md" 2>/dev/null || echo "Regression report skipped (no baseline)"

echo
echo "Benchmark run completed."
echo "Report directory: $REPORT_DIR"
echo "Summary: $SUMMARY_MD"
echo "Overview: $OVERVIEW_MD"
echo "Regression: $REPORT_DIR/regression.md"
