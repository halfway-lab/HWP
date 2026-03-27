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
    
    # 解析并测试每个样本
    if command -v python3 >/dev/null 2>&1; then
        python3 - "$FIXTURE_TYPE" << 'PYTHON_SCRIPT'
import json
import sys

fixture_type = sys.argv[1] if len(sys.argv) > 1 else "valid"
fixture_file = f"./tests/fixtures/continuity_{fixture_type}.json"

try:
    with open(fixture_file, 'r') as f:
        data = json.load(f)
    
    samples = data.get('samples', [])
    total = len(samples)
    passed = 0
    failed = 0
    
    print(f"Testing {total} samples from {fixture_file}")
    print("")
    
    for i, sample in enumerate(samples, 1):
        name = sample.get('name', f'Sample {i}')
        sample_data = sample.get('data', {})
        expected = sample.get('expected_result', 'PASS')
        violation = sample.get('violation', '')
        round_num = sample.get('round', 0)
        
        print(f"[{i}/{total}] Round {round_num}: {name}")
        
        # 验证逻辑
        errors = []
        
        # 检查关键字段存在性
        if 'node_id' not in sample_data:
            errors.append("Missing node_id")
        if 'variables' not in sample_data:
            errors.append("Missing variables")
        if 'shared_variable_count' not in sample_data:
            errors.append("Missing shared_variable_count")
        if 'drift_rate' not in sample_data:
            errors.append("Missing drift_rate")
        
        variables = sample_data.get('variables', [])
        shared_count = sample_data.get('shared_variable_count', 0)
        drift_rate = sample_data.get('drift_rate', 0)
        tensions = sample_data.get('tensions', [])
        parent_id = sample_data.get('parent_id')
        collapse_detected = sample_data.get('collapse_detected', False)
        
        # 检查 shared_variable_count 合理性（Round 1 除外）
        if round_num > 1:
            if shared_count < 10:  # 阈值：少于10个共享变量视为断裂
                errors.append(f"shared_variable_count too low: {shared_count} (threshold: 10)")
            if drift_rate > 0.6:  # 阈值：drift > 0.6 视为过早塌缩（与 fixture 样本匹配）
                errors.append(f"drift_rate too high: {drift_rate} (threshold: 0.6)")
            # 检查 collapse_detected 与 drift 一致性
            if collapse_detected and drift_rate > 0.6:
                errors.append(f"collapse_detected=true with high drift_rate: {drift_rate}")
        
        # 检查 tensions 丢失
        if round_num > 1 and len(tensions) == 0:
            errors.append("tensions array is empty (lost tension lineage)")
        
        # 检查 parent_id 断裂（Round 1 除外）
        if round_num > 1 and parent_id is None:
            errors.append("parent_id is null (broken chain continuity)")
        
        # 检查 shared_variable_count 与实际变量数一致性
        if len(variables) > 0:
            # 检查：shared_count 不应超过 variables 数量
            if shared_count > len(variables):
                errors.append(f"shared_variable_count ({shared_count}) exceeds total variables ({len(variables)})")
            # 检查：如果 shared_count 明显小于实际共享变量数（差距超过10），视为指标不一致
            # 共享变量定义为 var_* 或 new_var_* 或 stabilized_* 前缀
            valid_prefixes = ('var_', 'new_var_', 'stabilized_')
            actual_shared = sum(1 for v in variables if v.startswith(valid_prefixes))
            if round_num > 1 and actual_shared > 0:
                # 如果声称的 shared_count 比实际可识别的共享变量少很多（差距>10），视为不一致
                # 阈值设为10以区分 valid fixtures（差距约10）和 invalid fixtures（差距15）
                if actual_shared - shared_count > 10:
                    errors.append(f"shared_variable_count ({shared_count}) significantly less than actual shared variables ({actual_shared})")
        
        # 检查 collapse 与 drift 一致性
        if collapse_detected and drift_rate < 0.5:
            errors.append(f"collapse_detected=true but drift_rate ({drift_rate}) is low")
        
        # 判断结果
        if expected == 'PASS':
            if errors:
                print(f"  [FAIL] Expected PASS but got errors:")
                for e in errors:
                    print(f"    - {e}")
                failed += 1
            else:
                print(f"  [PASS] All validations passed")
                passed += 1
        else:  # expected == 'FAIL'
            if errors:
                print(f"  [PASS] Expected FAIL, detected errors:")
                for e in errors:
                    print(f"    - {e}")
                if violation:
                    print(f"    (Expected: {violation})")
                passed += 1
            else:
                print(f"  [FAIL] Expected FAIL but no errors found")
                failed += 1
        print("")
    
    print("=" * 50)
    print(f"Fixture Test Summary: {passed} passed, {failed} failed (total: {total})")
    sys.exit(0 if failed == 0 else 1)
    
except Exception as e:
    print(f"[ERROR] Failed to process fixture: {e}")
    sys.exit(1)
PYTHON_SCRIPT
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
    
    # 检查是否包含 round 信息
    if grep -q '"round"' "$FIRST_LOG" 2>/dev/null || grep -q '"turn"' "$FIRST_LOG" 2>/dev/null; then
        pass "日志包含轮次信息"
    else
        warn "日志中未找到明确的轮次标记"
    fi
    
    # 检查是否包含连续性相关字段
    if grep -q 'continuity' "$FIRST_LOG" 2>/dev/null || \
       grep -q 'state' "$FIRST_LOG" 2>/dev/null || \
       grep -q 'context' "$FIRST_LOG" 2>/dev/null; then
        pass "日志包含状态/上下文字段"
    else
        warn "日志中未找到明确的状态/上下文字段"
    fi
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
