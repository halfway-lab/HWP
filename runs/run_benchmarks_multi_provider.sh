#!/usr/bin/env bash
#
# HWP 多 Provider Benchmark 对比脚本 - 第3步
#
# 用途：同一组 benchmark 输入，自动在多个 provider 上执行并对比结果
#
# 执行方式：
#   ./runs/run_benchmarks_multi_provider.sh
#   ./runs/run_benchmarks_multi_provider.sh /path/to/custom_providers.list
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

PROVIDERS_FILE="${1:-$ROOT_DIR/config/providers.list}"
BENCHMARK_FILE="${2:-$ROOT_DIR/config/benchmark_inputs.txt}"
REPORT_ROOT="${HWP_BENCHMARK_REPORT_ROOT:-$ROOT_DIR/reports/benchmarks}"
MULTI_REPORT_DIR="$REPORT_ROOT/multi_$(date +%Y%m%dT%H%M%S)"

mkdir -p "$MULTI_REPORT_DIR"

echo "========================================"
echo "HWP Multi-Provider Benchmark"
echo "========================================"
echo "Providers: $PROVIDERS_FILE"
echo "Benchmarks: $BENCHMARK_FILE"
echo "Report: $MULTI_REPORT_DIR"
echo "========================================"
echo

if [ ! -f "$PROVIDERS_FILE" ]; then
    echo "错误：providers 清单不存在: $PROVIDERS_FILE" >&2
    exit 1
fi

if [ ! -f "$BENCHMARK_FILE" ]; then
    echo "错误：benchmark 清单不存在: $BENCHMARK_FILE" >&2
    exit 1
fi

# 存储所有 provider 的结果
declare -A PROVIDER_REPORTS

# 遍历每个 provider
while IFS='|' read -r provider_name env_file description || [ -n "$provider_name" ]; do
    # 跳过注释和空行
    [[ "$provider_name" =~ ^#.*$ ]] && continue
    [ -z "$provider_name" ] && continue
    
    echo "----------------------------------------"
    echo "Provider: $provider_name"
    echo "Description: $description"
    echo "----------------------------------------"
    
    # 检查 env 文件是否存在
    env_path="$ROOT_DIR/config/$env_file"
    if [ ! -f "$env_path" ]; then
        echo "警告：env 文件不存在: $env_path，跳过" >&2
        continue
    fi
    
    # 临时设置 provider
    export HWP_PROVIDER_TYPE="$provider_name"
    export HWP_PROVIDER_NAME="$provider_name"
    
    # 运行 benchmark
    provider_report_dir="$MULTI_REPORT_DIR/$provider_name"
    mkdir -p "$provider_report_dir"
    
    echo "Running benchmark for $provider_name..."
    
    if bash "$ROOT_DIR/runs/run_benchmarks.sh" "$BENCHMARK_FILE" > "$provider_report_dir/benchmark.log" 2>&1; then
        echo "✓ $provider_name completed"
        
        # 找到最新的报告目录
        latest_report=$(find "$REPORT_ROOT" -maxdepth 1 -type d -name '20*' | sort | tail -1)
        if [ -n "$latest_report" ]; then
            # 创建符号链接或复制关键文件
            cp "$latest_report/results.tsv" "$provider_report_dir/" 2>/dev/null || true
            cp "$latest_report/summary.md" "$provider_report_dir/" 2>/dev/null || true
            PROVIDER_REPORTS["$provider_name"]="$provider_report_dir"
        fi
    else
        echo "✗ $provider_name failed"
        PROVIDER_REPORTS["$provider_name"]="FAILED"
    fi
    
    echo
done < "$PROVIDERS_FILE"

# 生成跨 provider 对比报告
echo "========================================"
echo "Generating Cross-Provider Comparison"
echo "========================================"

python3 "$ROOT_DIR/runs/report_multi_provider.py" "$MULTI_REPORT_DIR" "$MULTI_REPORT_DIR/comparison.md"

echo
echo "========================================"
echo "Multi-Provider Benchmark Complete"
echo "========================================"
echo "Report directory: $MULTI_REPORT_DIR"
echo "Comparison: $MULTI_REPORT_DIR/comparison.md"
echo
echo "Provider Results:"
for provider in "${!PROVIDER_REPORTS[@]}"; do
    status="${PROVIDER_REPORTS[$provider]}"
    if [ "$status" = "FAILED" ]; then
        echo "  ✗ $provider: FAILED"
    else
        echo "  ✓ $provider: $status"
    fi
done
