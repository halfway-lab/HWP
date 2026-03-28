#!/bin/bash
#
# HWP v0.6 Cross-Round Continuity Verification Script
#
# 用途：验证 HWP 多轮生成过程中的上下文连续性和状态一致性
#
# 执行方式：
#   ./runs/verify_v06_continuity.sh
#   ./runs/verify_v06_continuity.sh /path/to/logs
#   ./runs/verify_v06_continuity.sh --fixture [valid|invalid]
#
# Fixture 接线说明：
# - valid fixtures: 应通过测试（shared_variable_count 合理，drift_rate 正常，parent_id 正确）
# - invalid fixtures: 应失败测试（shared variables 断裂、tensions 丢失、parent 缺失）
# - 接收方式: --fixture 参数触发 fixture 模式
#

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 默认日志目录
LOGS_DIR="${1:-./logs}"
SCRIPT_NAME="$(basename "$0")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Fixture 模式检测
FIXTURE_MODE=false
FIXTURE_TYPE=""
if [ "$1" = "--fixture" ]; then
    FIXTURE_MODE=true
    FIXTURE_TYPE="${2:-all}"
    LOGS_DIR="./logs"  # fixture 模式下忽略日志目录参数
fi

# 计数器
PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

# 禁用退出 on error，我们将手动处理
set +e

# 输出函数
pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    PASS_COUNT=$((PASS_COUNT + 1))
}

fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    FAIL_COUNT=$((FAIL_COUNT + 1))
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    WARN_COUNT=$((WARN_COUNT + 1))
}

info() {
    echo -e "[INFO] $1"
}

consume_log_results() {
    local suite="$1"
    local log_path="$2"
    local line status message
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        status="${line%%|*}"
        message="${line#*|}"
        case "$status" in
            PASS) pass "$message" ;;
            WARN) warn "$message" ;;
            FAIL) fail "$message" ;;
        esac
    done < <(python3 -m hwp_protocol.cli log-verify "$suite" "$log_path")
}

# 标题
echo "========================================"
echo "HWP v0.6 Cross-Round Continuity Verify"
echo "========================================"
echo ""

# ==================== Fixture 测试模式 ====================
if [ "$FIXTURE_MODE" = true ]; then
    echo "[MODE] Fixture Testing - Type: $FIXTURE_TYPE"
    echo ""
    
    FIXTURE_FILE="./tests/fixtures/continuity_${FIXTURE_TYPE}.json"
    if [ ! -f "$FIXTURE_FILE" ]; then
        fail "Fixture file not found: $FIXTURE_FILE"
        exit 1
    fi
    
    pass "Loading fixture: $FIXTURE_FILE"
    echo ""
    
    if command -v python3 >/dev/null 2>&1; then
        python3 -m hwp_protocol.cli fixture-verify continuity "$FIXTURE_TYPE"
        exit $?
    else
        fail "Python3 not available for fixture testing"
        exit 1
    fi
fi

# 检查日志目录
info "检查日志目录: $LOGS_DIR"
if [ ! -d "$LOGS_DIR" ]; then
    fail "日志目录不存在: $LOGS_DIR"
    echo ""
    echo "验证结果: FAILED"
    exit 1
fi
pass "日志目录存在"

# 检查日志文件
info "检查日志文件..."
LOG_FILES=$(find "$LOGS_DIR" -name "*.jsonl" -type f 2>/dev/null | head -5)
if [ -z "$LOG_FILES" ]; then
    warn "未找到 .jsonl 日志文件"
else
    pass "找到日志文件"
    info "日志文件示例: $(echo "$LOG_FILES" | head -1)"
fi

# 检查状态连续性
echo ""
info "检查状态连续性..."

# 检查 chain 日志中的 round 连续性
FIRST_LOG=$(find "$LOGS_DIR" -name "*.jsonl" -type f | head -1)
if [ -n "$FIRST_LOG" ] && [ -f "$FIRST_LOG" ]; then
    consume_log_results continuity "$FIRST_LOG"
else
    warn "无日志文件可供分析"
fi

# 检查文档存在性
echo ""
info "检查相关文档..."

if [ -f "./docs/v0.6-plan.md" ]; then
    pass "v0.6-plan.md 存在"
else
    warn "v0.6-plan.md 不存在"
fi

if [ -f "./docs/v0.6-tests.md" ]; then
    pass "v0.6-tests.md 存在"
else
    warn "v0.6-tests.md 不存在"
fi

# 总结
echo ""
echo "========================================"
echo "验证总结"
echo "========================================"
echo -e "通过: ${GREEN}$PASS_COUNT${NC}"
echo -e "失败: ${RED}$FAIL_COUNT${NC}"
echo -e "警告: ${YELLOW}$WARN_COUNT${NC}"
echo ""

# 判断总体结果
if [ $FAIL_COUNT -eq 0 ]; then
    if [ $WARN_COUNT -eq 0 ]; then
        echo -e "总体结果: ${GREEN}PASS${NC}"
        exit 0
    else
        echo -e "总体结果: ${YELLOW}PASS_WITH_WARNINGS${NC}"
        exit 0
    fi
else
    echo -e "总体结果: ${RED}FAIL${NC}"
    exit 1
fi
