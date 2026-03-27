#!/bin/bash
#
# HWP v0.6 Unified Regression Verification Script
#
# 用途：统一执行所有 v0.6 验证脚本，输出汇总结果
#
# 执行方式：
#   ./runs/verify_v06_all.sh
#   ./runs/verify_v06_all.sh /path/to/logs
#

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认日志目录
LOGS_DIR="${1:-./logs}"

# 计数器
TOTAL_PASS=0
TOTAL_FAIL=0
TOTAL_WARN=0
SCRIPT_COUNT=0

# Fixture 测试汇总
FIXTURE_VALID_PASS=0
FIXTURE_VALID_FAIL=0
FIXTURE_INVALID_PASS=0
FIXTURE_INVALID_FAIL=0

# 禁用退出 on error
set +e

# 输出函数
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

fail() {
    echo -e "${RED}[FAIL]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# 标题
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║     HWP v0.6 Unified Regression Verification Suite         ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Logs directory: $LOGS_DIR"
echo ""

# 检查日志目录
if [ ! -d "$LOGS_DIR" ]; then
    fail "Logs directory not found: $LOGS_DIR"
    exit 1
fi

# 定义验证脚本列表
VERIFIERS=(
    "verify_v06_blind_spot.sh:Blind Spot Detection"
    "verify_v06_continuity.sh:Cross-Round Continuity"
    "verify_v06_semantic_groups.sh:Semantic Group Expansion"
)

# 执行每个验证脚本
for verifier_info in "${VERIFIERS[@]}"; do
    IFS=':' read -r script_name description <<< "$verifier_info"
    SCRIPT_COUNT=$((SCRIPT_COUNT + 1))
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "[$SCRIPT_COUNT/3] Testing: $description"
    echo "Script: $script_name"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    script_path="./runs/$script_name"
    
    # 检查脚本是否存在
    if [ ! -f "$script_path" ]; then
        fail "Script not found: $script_path"
        TOTAL_FAIL=$((TOTAL_FAIL + 1))
        echo ""
        continue
    fi
    
    if [ ! -x "$script_path" ]; then
        warn "Script not executable, attempting to run with bash: $script_path"
        bash "$script_path" "$LOGS_DIR" 2>&1
    else
        "$script_path" "$LOGS_DIR" 2>&1
    fi
    
    EXIT_CODE=$?
    
    echo ""
    if [ $EXIT_CODE -eq 0 ]; then
        pass "$description - PASSED"
        TOTAL_PASS=$((TOTAL_PASS + 1))
    else
        fail "$description - FAILED (exit code: $EXIT_CODE)"
        TOTAL_FAIL=$((TOTAL_FAIL + 1))
    fi
    echo ""
done

# Fixture 测试汇总输出
run_fixture_tests() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║              FIXTURE REGRESSION TESTS                      ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    
    # Blind Spot Fixtures
    echo "[1/3] Blind Spot Detection Fixtures"
    echo "─────────────────────────────────────────"
    echo "  Valid fixtures (should PASS):"
    BS_VALID_OUTPUT=$(./runs/verify_v06_blind_spot.sh --fixture valid 2>&1)
    BS_VALID_EXIT=$?
    if [ $BS_VALID_EXIT -eq 0 ] && echo "$BS_VALID_OUTPUT" | grep -q "Fixture Test Summary:.*0 failed"; then
        pass "  blind_spot_valid.json - All samples passed"
        FIXTURE_VALID_PASS=$((FIXTURE_VALID_PASS + 1))
    else
        fail "  blind_spot_valid.json - Some samples failed"
        FIXTURE_VALID_FAIL=$((FIXTURE_VALID_FAIL + 1))
    fi
    
    echo "  Invalid fixtures (should FAIL):"
    BS_INVALID_OUTPUT=$(./runs/verify_v06_blind_spot.sh --fixture invalid 2>&1)
    BS_INVALID_EXIT=$?
    # Invalid fixtures 应该检测到错误（输出中包含 "Expected FAIL, detected errors"）
    if echo "$BS_INVALID_OUTPUT" | grep -q "Expected FAIL, detected errors" && ! echo "$BS_INVALID_OUTPUT" | grep -q "Expected FAIL but no errors found"; then
        pass "  blind_spot_invalid.json - All samples correctly failed"
        FIXTURE_INVALID_PASS=$((FIXTURE_INVALID_PASS + 1))
    else
        fail "  blind_spot_invalid.json - Expected failures but passed"
        FIXTURE_INVALID_FAIL=$((FIXTURE_INVALID_FAIL + 1))
    fi
    echo ""
    
    # Continuity Fixtures
    echo "[2/3] Cross-Round Continuity Fixtures"
    echo "─────────────────────────────────────────"
    echo "  Valid fixtures (should PASS):"
    CONT_VALID_OUTPUT=$(./runs/verify_v06_continuity.sh --fixture valid 2>&1)
    CONT_VALID_EXIT=$?
    if [ $CONT_VALID_EXIT -eq 0 ] && echo "$CONT_VALID_OUTPUT" | grep -q "Fixture Test Summary:.*0 failed"; then
        pass "  continuity_valid.json - All samples passed"
        FIXTURE_VALID_PASS=$((FIXTURE_VALID_PASS + 1))
    else
        fail "  continuity_valid.json - Some samples failed"
        FIXTURE_VALID_FAIL=$((FIXTURE_VALID_FAIL + 1))
    fi
    
    echo "  Invalid fixtures (should FAIL):"
    CONT_INVALID_OUTPUT=$(./runs/verify_v06_continuity.sh --fixture invalid 2>&1)
    CONT_INVALID_EXIT=$?
    if echo "$CONT_INVALID_OUTPUT" | grep -q "Expected FAIL, detected errors" && ! echo "$CONT_INVALID_OUTPUT" | grep -q "Expected FAIL but no errors found"; then
        pass "  continuity_invalid.json - All samples correctly failed"
        FIXTURE_INVALID_PASS=$((FIXTURE_INVALID_PASS + 1))
    else
        fail "  continuity_invalid.json - Expected failures but passed"
        FIXTURE_INVALID_FAIL=$((FIXTURE_INVALID_FAIL + 1))
    fi
    echo ""
    
    # Semantic Groups Fixtures
    echo "[3/3] Semantic Group Expansion Fixtures"
    echo "─────────────────────────────────────────"
    echo "  Valid fixtures (should PASS):"
    SG_VALID_OUTPUT=$(./runs/verify_v06_semantic_groups.sh --fixture valid 2>&1)
    SG_VALID_EXIT=$?
    if [ $SG_VALID_EXIT -eq 0 ] && echo "$SG_VALID_OUTPUT" | grep -q "Fixture Test Summary:.*0 failed"; then
        pass "  semantic_groups_valid.json - All samples passed"
        FIXTURE_VALID_PASS=$((FIXTURE_VALID_PASS + 1))
    else
        fail "  semantic_groups_valid.json - Some samples failed"
        FIXTURE_VALID_FAIL=$((FIXTURE_VALID_FAIL + 1))
    fi
    
    echo "  Invalid fixtures (should FAIL):"
    SG_INVALID_OUTPUT=$(./runs/verify_v06_semantic_groups.sh --fixture invalid 2>&1)
    SG_INVALID_EXIT=$?
    if echo "$SG_INVALID_OUTPUT" | grep -q "Expected FAIL, detected errors" && ! echo "$SG_INVALID_OUTPUT" | grep -q "Expected FAIL but no errors found"; then
        pass "  semantic_groups_invalid.json - All samples correctly failed"
        FIXTURE_INVALID_PASS=$((FIXTURE_INVALID_PASS + 1))
    else
        fail "  semantic_groups_invalid.json - Expected failures but passed"
        FIXTURE_INVALID_FAIL=$((FIXTURE_INVALID_FAIL + 1))
    fi
    echo ""
}

# 最终汇总
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                   FINAL SUMMARY                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Verification Scripts Run: $SCRIPT_COUNT"
echo ""
echo -e "  ${GREEN}PASSED:${NC}  $TOTAL_PASS"
echo -e "  ${RED}FAILED:${NC}  $TOTAL_FAIL"
echo -e "  ${YELLOW}WARNINGS:${NC} $TOTAL_WARN"
echo ""

# Fixture 测试汇总
run_fixture_tests

echo "╔════════════════════════════════════════════════════════════╗"
echo "║              FIXTURE TEST SUMMARY                          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Valid Fixtures (should PASS):   $FIXTURE_VALID_PASS passed, $FIXTURE_VALID_FAIL failed"
echo "Invalid Fixtures (should FAIL): $FIXTURE_INVALID_PASS passed, $FIXTURE_INVALID_FAIL failed"
echo ""

# 判断总体结果
if [ $TOTAL_FAIL -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║           ALL VERIFICATIONS PASSED ✓                       ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║        SOME VERIFICATIONS FAILED ✗                         ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    exit 1
fi
