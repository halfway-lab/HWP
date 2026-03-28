#!/bin/bash
#
# HWP v0.6 Semantic Group Expansion Verification Script
#
# 用途：验证语义组在扩展过程中保持内部一致性和逻辑连贯性
#
# 执行方式：
#   ./runs/verify_v06_semantic_groups.sh
#   ./runs/verify_v06_semantic_groups.sh /path/to/logs
#   ./runs/verify_v06_semantic_groups.sh --fixture [valid|invalid]
#
# Fixture 接线说明：
# - valid fixtures: 应通过测试（group_id 有效、coherence_score 达标、无跨域污染）
# - invalid fixtures: 应失败测试（group_id 为 null、标识符变更、coherence 过低、跨域污染）
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
echo "HWP v0.6 Semantic Group Expansion Verify"
echo "========================================"
echo ""

# ==================== Fixture 测试模式 ====================
if [ "$FIXTURE_MODE" = true ]; then
    echo "[MODE] Fixture Testing - Type: $FIXTURE_TYPE"
    echo ""
    
    FIXTURE_FILE="./tests/fixtures/semantic_groups_${FIXTURE_TYPE}.json"
    if [ ! -f "$FIXTURE_FILE" ]; then
        fail "Fixture file not found: $FIXTURE_FILE"
        exit 1
    fi
    
    pass "Loading fixture: $FIXTURE_FILE"
    echo ""
    
    if command -v python3 >/dev/null 2>&1; then
        python3 -m hwp_protocol.cli fixture-verify semantic_groups "$FIXTURE_TYPE"
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
# 找到语义组相关日志文件
info "检查语义组相关日志文件..."
LOG_FILES=$(find "$LOGS_DIR" -name "*.jsonl" -type f 2>/dev/null)
if [ -n "$LOG_FILES" ]; then
    pass "找到日志文件"
    FILE_COUNT=$(echo "$LOG_FILES" | wc -l)
    info "日志文件数量: $FILE_COUNT"
else
    warn "未找到 .jsonl 日志文件"
fi

# ==================== Success Condition 3 ====================
# 检查语义组字段存在性（当 spec 实现后）
info "检查语义组字段..."
FIRST_LOG=$(find "$LOGS_DIR" -name "*.jsonl" -type f | head -1)
if [ -n "$FIRST_LOG" ] && [ -f "$FIRST_LOG" ]; then
    consume_log_results semantic_groups "$FIRST_LOG"
else
    warn "无日志文件可供分析"
fi

# ==================== 文档检查 ====================
echo ""
info "检查相关文档..."

if [ -f "./docs/v0.6-tests.md" ]; then
    pass "v0.6-tests.md 存在"
    # 检查文档中是否包含 semantic group 相关内容
    if grep -q 'semantic group' ./docs/v0.6-tests.md 2>/dev/null; then
        pass "v0.6-tests.md 包含 semantic group 测试设计"
    fi
else
    warn "v0.6-tests.md 不存在"
fi

if [ -f "./runs/verify_v06_continuity.sh" ]; then
    pass "verify_v06_continuity.sh 存在（其他 v0.6 验证脚本）"
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
        echo "说明: 警告项多为'待 V06-003 完成后实现'的字段检查，"
        echo "      当前脚本结构已就绪，待协议字段定义后可自动检测。"
        exit 0
    fi
else
    echo -e "总体结果: ${RED}FAIL${NC}"
    exit 1
fi
