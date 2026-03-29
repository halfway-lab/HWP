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

echo -e "benchmark\tinput_path\trun_status\trun_exit_code\tlog_count\tstructured\tblind_spot\tcontinuity\tsemantic_groups\treport_dir" > "$RESULTS_TSV"

list_chain_logs() {
  find "$ROOT_DIR/logs" -maxdepth 1 -name 'chain_*.jsonl' -type f 2>/dev/null | sort
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

while IFS= read -r input_path || [ -n "$input_path" ]; do
  [ -z "$input_path" ] && continue
  case "$input_path" in
    \#*) continue ;;
  esac

  benchmark_name="$(basename "$input_path" .txt)"
  bench_dir="$REPORT_DIR/$benchmark_name"
  bench_logs_dir="$bench_dir/logs"
  mkdir -p "$bench_logs_dir"

  before_file="$bench_dir/logs_before.txt"
  after_file="$bench_dir/logs_after.txt"
  new_file="$bench_dir/new_logs.txt"

  list_chain_logs > "$before_file"

  run_status="pass"
  run_exit_code=0
  if (cd "$ROOT_DIR" && bash runs/run_sequential.sh "$input_path" > "$bench_dir/run_output.log" 2>&1); then
    run_exit_code=0
  else
    run_exit_code=$?
    run_status="fail"
  fi

  list_chain_logs > "$after_file"
  comm -13 "$before_file" "$after_file" > "$new_file" || true

  log_count=0
  while IFS= read -r log_path || [ -n "$log_path" ]; do
    [ -z "$log_path" ] && continue
    cp "$log_path" "$bench_logs_dir/"
    log_count=$((log_count + 1))
  done < "$new_file"

  # 结构化验证（第2步新增）
  structured_status="$(run_verifier "verify_structured.sh" "$bench_logs_dir" "$bench_dir/verify_structured.log")"
  
  blind_status="$(run_verifier "verify_v06_blind_spot.sh" "$bench_logs_dir" "$bench_dir/verify_blind_spot.log")"
  continuity_status="$(run_verifier "verify_v06_continuity.sh" "$bench_logs_dir" "$bench_dir/verify_continuity.log")"
  semantic_status="$(run_verifier "verify_v06_semantic_groups.sh" "$bench_logs_dir" "$bench_dir/verify_semantic_groups.log")"

  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$benchmark_name" \
    "$input_path" \
    "$run_status" \
    "$run_exit_code" \
    "$log_count" \
    "$structured_status" \
    "$blind_status" \
    "$continuity_status" \
    "$semantic_status" \
    "$bench_dir" >> "$RESULTS_TSV"

  {
    echo "[$benchmark_name] run_status=$run_status run_exit_code=$run_exit_code logs=$log_count"
    echo "[$benchmark_name] blind_spot=$blind_status continuity=$continuity_status semantic_groups=$semantic_status"
  } | tee -a "$RUN_LOG"
done < "$BENCHMARK_FILE"

python3 "$ROOT_DIR/runs/report_benchmarks.py" "$RESULTS_TSV" "$SUMMARY_MD" > "$REPORT_DIR/summary_path.txt"

# 生成回归报告（第5步新增）
echo ""
echo "Generating regression report..."
python3 "$ROOT_DIR/runs/report_regression.py" "$REPORT_DIR" "$REPORT_DIR/regression.md" 2>/dev/null || echo "Regression report skipped (no baseline)"

echo
echo "Benchmark run completed."
echo "Report directory: $REPORT_DIR"
echo "Summary: $SUMMARY_MD"
echo "Regression: $REPORT_DIR/regression.md"
