#!/bin/bash
#
# HWP v0.6 Blind Spot Detector Verification Script
#
# 用途：验证 blind spot detection 字段在日志中的正确性
#
# 执行方式：
#   ./runs/verify_v06_blind_spot.sh
#   ./runs/verify_v06_blind_spot.sh /path/to/logs
#   ./runs/verify_v06_blind_spot.sh --fixture [valid|invalid]
#
# Fixture 接线说明：
# - valid fixtures: 应通过测试（blind_spot_score 在 [0.0,1.0]，字段类型正确）
# - invalid fixtures: 应失败测试（score 越界、类型错误、字段缺失）
# - 接收方式: --fixture 参数触发 fixture 模式
#

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 默认日志目录
LOGS_DIR="${1:-./logs}"
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
echo "HWP v0.6 Blind Spot Detector Verify"
echo "========================================"
echo ""

# ==================== Fixture 测试模式 ====================
if [ "$FIXTURE_MODE" = true ]; then
    echo "[MODE] Fixture Testing - Type: $FIXTURE_TYPE"
    echo ""
    
    FIXTURE_FILE="./tests/fixtures/blind_spot_${FIXTURE_TYPE}.json"
    if [ ! -f "$FIXTURE_FILE" ]; then
        fail "Fixture file not found: $FIXTURE_FILE"
        exit 1
    fi
    
    pass "Loading fixture: $FIXTURE_FILE"
    echo ""
    
    if command -v python3 >/dev/null 2>&1; then
        python3 -m hwp_protocol.cli fixture-verify blind_spot "$FIXTURE_TYPE"
        exit $?
    else
        fail "Python3 not available for fixture testing"
        exit 1
    fi
fi

# ==================== Success Condition 1 ====================
# 日志目录存在且可访问
info "检查日志目录可访问性..."
if [ -d "$LOGS_DIR" ]; then
    pass "日志目录存在且可访问: $LOGS_DIR"
else
    fail "日志目录不存在: $LOGS_DIR"
    echo ""
    echo "========================================"
    echo "验证总结"
    echo "========================================"
    echo -e "通过: ${GREEN}$PASS_COUNT${NC}"
    echo -e "失败: ${RED}$FAIL_COUNT${NC}"
    echo -e "警告: ${YELLOW}$WARN_COUNT${NC}"
    echo ""
    echo -e "总体结果: ${RED}FAIL${NC}"
    exit 1
fi

# ==================== Success Condition 2 ====================
# 找到包含 blind spot 字段的日志文件
info "检查 blind spot 相关日志文件..."
FIRST_LOG=$(find "$LOGS_DIR" -name "*.jsonl" -type f | head -1)
if [ -n "$FIRST_LOG" ] && [ -f "$FIRST_LOG" ]; then
    pass "找到日志文件: $(basename "$FIRST_LOG")"
else
    warn "未找到 .jsonl 日志文件"
fi

# ==================== Success Condition 3 ====================
# 检查 blind_spot_signals 字段存在
info "检查 blind_spot_signals 字段..."
if [ -n "$FIRST_LOG" ] && [ -f "$FIRST_LOG" ]; then
    consume_log_results blind_spot "$FIRST_LOG"
else
    warn "无法检查 blind_spot_signals（无日志文件）"
fi

# ==================== 文档检查 ====================
echo ""
info "检查相关文档..."

if [ -f "./docs/v0.6-tests.md" ]; then
    pass "v0.6-tests.md 存在"
    if grep -q 'blind spot' ./docs/v0.6-tests.md 2>/dev/null; then
        pass "v0.6-tests.md 包含 blind spot 测试设计"
    fi
else
    warn "v0.6-tests.md 不存在"
fi

if [ -f "./spec/hwp_turn_prompt.txt" ]; then
    if grep -q 'blind_spot_signals' ./spec/hwp_turn_prompt.txt 2>/dev/null; then
        pass "spec/hwp_turn_prompt.txt 包含 blind spot 字段定义"
    fi
else
    warn "spec/hwp_turn_prompt.txt 不存在"
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
        echo ""
        echo "说明: 警告项可能由于日志中暂未输出 blind spot 字段（过渡期），"
        echo "      或字段为 OPTIONAL 性质。脚本结构已就绪。"
        exit 0
    fi
else
    echo -e "总体结果: ${RED}FAIL${NC}"
    exit 1
fi
