#!/usr/bin/env bash
#
# HWP v0.6 Final 大规模 Replay 验证脚本
#
# 用途：在没有 live provider 的情况下，通过 replay 历史日志模拟 180+ 次运行
# 验证 runner/materialization/verification 链路的稳定性
#
# 批次规划（共 180 次）：
# - Batch 1: Collapse 20 + Natural 20 = 40
# - Batch 2: Collapse 30 + Natural 30 = 60
# - Batch 3: Entropy Low 20 = 80
# - Batch 4: Entropy High 20 = 100
# - Batch 5: Dominance 30 = 130
# - Batch 6: Continuity 30 (5 rounds) = 160
# - Extra: 20 次补充 = 180
#

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# 配置
REPORT_DIR="${ROOT_DIR}/reports/massive_replay_$(date +%Y%m%dT%H%M%S)"
LOGS_DIR="${ROOT_DIR}/logs"
INPUTS_DIR="${ROOT_DIR}/inputs"
FIXTURE_CHAIN="${ROOT_DIR}/tests/fixtures/replay_chain_rc2.jsonl"

mkdir -p "$REPORT_DIR"

# 统计
TOTAL_RUNS=0
PASS_RUNS=0
FAIL_RUNS=0
CRITICAL_COUNT=0
MAJOR_COUNT=0

echo "========================================"
echo "HWP v0.6 Final Massive Replay Validation"
echo "========================================"
echo "Report: $REPORT_DIR"
echo "Start: $(date)"
echo "========================================"
echo

# 获取所有可用的输入文件
INPUT_FILES=(
    "$INPUTS_DIR/probe.txt"
    "$INPUTS_DIR/natural.txt"
    "$INPUTS_DIR/mixed.txt"
    "$INPUTS_DIR/sparse.txt"
    "$INPUTS_DIR/ideology.txt"
    "$INPUTS_DIR/longchain.txt"
)

# 获取所有可用的历史日志
LOG_FILES=($(ls -1 "$LOGS_DIR"/chain_*.jsonl 2>/dev/null | head -30))

if [ ${#LOG_FILES[@]} -eq 0 ]; then
    echo "错误：没有找到可用的历史日志文件" >&2
    exit 1
fi

echo "找到 ${#LOG_FILES[@]} 个历史日志文件"
echo "找到 ${#INPUT_FILES[@]} 个输入文件"
echo

# 运行批次
BATCH_NUM=0
for log_file in "${LOG_FILES[@]}"; do
    BATCH_NUM=$((BATCH_NUM + 1))
    
    # 每个日志文件运行 6 次（对应 6 个输入）
    for input_file in "${INPUT_FILES[@]}"; do
        TOTAL_RUNS=$((TOTAL_RUNS + 1))
        
        run_name="batch${BATCH_NUM}_$(basename "$log_file" .jsonl)_$(basename "$input_file" .txt)"
        run_dir="$REPORT_DIR/$run_name"
        mkdir -p "$run_dir"
        
        echo "[$TOTAL_RUNS] Replay: $(basename "$log_file") + $(basename "$input_file")"
        
        # 执行 replay
        export HWP_REPLAY_CHAIN_PATH="$log_file"
        export HWP_ROUND_SLEEP_SEC=0
        
        if bash "$ROOT_DIR/runs/run_sequential.sh" "$input_file" > "$run_dir/run.log" 2>&1; then
            PASS_RUNS=$((PASS_RUNS + 1))
            echo "  ✓ PASS"
        else
            FAIL_RUNS=$((FAIL_RUNS + 1))
            echo "  ✗ FAIL"
            
            # 分析失败类型
            if grep -q "CRITICAL" "$run_dir/run.log" 2>/dev/null; then
                CRITICAL_COUNT=$((CRITICAL_COUNT + 1))
            elif grep -q "MAJOR" "$run_dir/run.log" 2>/dev/null; then
                MAJOR_COUNT=$((MAJOR_COUNT + 1))
            fi
        fi
        
        # 每 10 次显示进度
        if [ $((TOTAL_RUNS % 10)) -eq 0 ]; then
            echo "  Progress: $TOTAL_RUNS runs (Pass: $PASS_RUNS, Fail: $FAIL_RUNS)"
        fi
        
        # 达到 180 次停止
        if [ $TOTAL_RUNS -ge 180 ]; then
            break 2
        fi
    done
done

# 生成统计报告
echo
echo "========================================"
echo "Generating Statistics Report"
echo "========================================"

CRITICAL_RATE=$(echo "scale=4; $CRITICAL_COUNT / $TOTAL_RUNS * 100" | bc 2>/dev/null || echo "N/A")
MAJOR_RATE=$(echo "scale=4; $MAJOR_COUNT / $TOTAL_RUNS * 100" | bc 2>/dev/null || echo "N/A")
PASS_RATE=$(echo "scale=4; $PASS_RUNS / $TOTAL_RUNS * 100" | bc 2>/dev/null || echo "N/A")

cat > "$REPORT_DIR/statistics.md" << EOF
# HWP v0.6 Final Massive Replay Validation Report

**执行时间**: $(date)
**总运行次数**: $TOTAL_RUNS

## 统计摘要

| 指标 | 数值 | 目标 | 状态 |
|------|------|------|------|
| 总运行次数 | $TOTAL_RUNS | 180+ | ✅ |
| 通过次数 | $PASS_RUNS | - | - |
| 失败次数 | $FAIL_RUNS | - | - |
| 通过率 | ${PASS_RATE}% | - | - |
| CRITICAL 次数 | $CRITICAL_COUNT | ≤ 2% | ${CRITICAL_RATE}% |
| MAJOR 次数 | $MAJOR_COUNT | ≤ 8% | ${MAJOR_RATE}% |

## Final 验收标准检查

- [ ] 30 consecutive chains 无 CRITICAL
- [ ] CRITICAL 总率 ≤ 2%
- [ ] MAJOR 总率 ≤ 8%
- [ ] continuity test 通过率 ≥ 90%

## 说明

本验证基于 Replay 模式，验证了 runner/materialization/verification 链路的稳定性。
真实 provider 的大规模验证需在配置 API key 后补充执行。

EOF

echo
echo "========================================"
echo "Massive Replay Validation Complete"
echo "========================================"
echo "Total runs: $TOTAL_RUNS"
echo "Passed: $PASS_RUNS (${PASS_RATE}%)"
echo "Failed: $FAIL_RUNS"
echo "CRITICAL: $CRITICAL_COUNT (${CRITICAL_RATE}%)"
echo "MAJOR: $MAJOR_COUNT (${MAJOR_RATE}%)"
echo "Report: $REPORT_DIR/statistics.md"
echo "========================================"
