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
    
    # 解析并测试每个样本
    # 使用 Python 解析 JSON（更可靠）
    if command -v python3 >/dev/null 2>&1; then
        python3 - "$FIXTURE_TYPE" << 'PYTHON_SCRIPT'
import json
import sys

fixture_type = sys.argv[1] if len(sys.argv) > 1 else "valid"
fixture_file = f"./tests/fixtures/blind_spot_{fixture_type}.json"

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
        
        print(f"[{i}/{total}] {name}")
        
        # 验证逻辑
        errors = []
        
        # 检查字段存在性
        if 'blind_spot_score' not in sample_data:
            errors.append("Missing blind_spot_score")
        if 'blind_spot_signals' not in sample_data:
            errors.append("Missing blind_spot_signals")
        if 'blind_spot_reason' not in sample_data:
            errors.append("Missing blind_spot_reason")
        
        # 检查 score 范围
        score = sample_data.get('blind_spot_score')
        if score is not None:
            if not isinstance(score, (int, float)):
                errors.append(f"blind_spot_score is not numeric: {type(score)}")
            elif score < 0.0 or score > 1.0:
                errors.append(f"blind_spot_score out of range: {score}")
        
        # 检查 signals 类型
        signals = sample_data.get('blind_spot_signals')
        if signals is not None and not isinstance(signals, list):
            errors.append(f"blind_spot_signals is not array: {type(signals)}")
        if signals is None and 'blind_spot_signals' in sample_data:
            errors.append("blind_spot_signals is null (should be array)")
        
        # 检查 signal 内部结构
        if isinstance(signals, list):
            valid_types = {"information_gap", "logic_break", "assumption_conflict", "boundary_blindspot"}
            valid_severities = {"low", "medium", "high", "critical"}
            for idx, signal in enumerate(signals):
                if isinstance(signal, dict):
                    sig_type = signal.get('type', '')
                    if sig_type and sig_type not in valid_types:
                        errors.append(f"Signal[{idx}]: invalid type '{sig_type}'")
                    severity = signal.get('severity', '')
                    if severity and severity not in valid_severities:
                        errors.append(f"Signal[{idx}]: invalid severity '{severity}'")
        
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
    if grep -q '"blind_spot_signals"' "$FIRST_LOG" 2>/dev/null; then
        pass "日志包含 blind_spot_signals 字段"
        
        # 检查是否为数组类型
        ARRAY_CHECK=$(grep -o '"blind_spot_signals":\s*\[' "$FIRST_LOG" 2>/dev/null | head -1)
        if [ -n "$ARRAY_CHECK" ]; then
            pass "blind_spot_signals 为数组类型"
        else
            warn "blind_spot_signals 可能不是数组类型"
        fi
    else
        warn "日志中未找到 blind_spot_signals 字段（字段为 OPTIONAL）"
    fi
else
    warn "无法检查 blind_spot_signals（无日志文件）"
fi

# ==================== Success Condition 4 ====================
# 检查 blind_spot_score 字段存在且在 0.0-1.0 范围内
info "检查 blind_spot_score 字段..."
if [ -n "$FIRST_LOG" ] && [ -f "$FIRST_LOG" ]; then
    if grep -q '"blind_spot_score"' "$FIRST_LOG" 2>/dev/null; then
        pass "日志包含 blind_spot_score 字段"
        
        # 提取并验证范围
        SCORE_VALUES=$(grep -o '"blind_spot_score":\s*[0-9.]*' "$FIRST_LOG" 2>/dev/null | sed 's/.*://' | tr -d ' ')
        if [ -n "$SCORE_VALUES" ]; then
            for score in $SCORE_VALUES; do
                # 使用 awk 进行浮点数比较
                VALID_RANGE=$(echo "$score" | awk '{if ($1 >= 0.0 && $1 <= 1.0) print 1; else print 0}')
                if [ "$VALID_RANGE" = "1" ]; then
                    pass "blind_spot_score=$score 在有效范围 [0.0, 1.0] 内"
                else
                    fail "blind_spot_score=$score 超出有效范围 [0.0, 1.0]"
                fi
            done
        fi
    else
        warn "日志中未找到 blind_spot_score 字段（字段为 OPTIONAL）"
    fi
else
    warn "无法检查 blind_spot_score（无日志文件）"
fi

# ==================== Success Condition 5 ====================
# 检查 blind_spot_reason 字段存在
info "检查 blind_spot_reason 字段..."
if [ -n "$FIRST_LOG" ] && [ -f "$FIRST_LOG" ]; then
    if grep -q '"blind_spot_reason"' "$FIRST_LOG" 2>/dev/null; then
        pass "日志包含 blind_spot_reason 字段"
        
        # 检查是否为字符串类型
        STRING_CHECK=$(grep -o '"blind_spot_reason":\s*"' "$FIRST_LOG" 2>/dev/null | head -1)
        if [ -n "$STRING_CHECK" ]; then
            pass "blind_spot_reason 为字符串类型"
        else
            warn "blind_spot_reason 可能不是字符串类型"
        fi
    else
        warn "日志中未找到 blind_spot_reason 字段（字段为 OPTIONAL）"
    fi
else
    warn "无法检查 blind_spot_reason（无日志文件）"
fi

# ==================== Failure Condition 1 ====================
# 检查 blind_spot_score 是否超出范围
info "检查 blind_spot_score 范围有效性..."
if [ -n "$FIRST_LOG" ] && [ -f "$FIRST_LOG" ]; then
    # 查找超出范围的值
    INVALID_SCORES=$(grep -o '"blind_spot_score":\s*[0-9.]*' "$FIRST_LOG" 2>/dev/null | sed 's/.*://' | tr -d ' ' | awk '{if ($1 < 0.0 || $1 > 1.0) print $1}')
    if [ -n "$INVALID_SCORES" ]; then
        for invalid in $INVALID_SCORES; do
            fail "检测到无效的 blind_spot_score: $invalid（必须在 0.0-1.0 范围内）"
        done
    else
        pass "未发现超出范围的 blind_spot_score"
    fi
else
    warn "无法检查范围（无日志文件）"
fi

# ==================== Failure Condition 2 ====================
# 检查字段类型错误
info "检查字段类型一致性..."
if [ -n "$FIRST_LOG" ] && [ -f "$FIRST_LOG" ]; then
    # 检查 blind_spot_signals 是否为 null（类型错误）
    NULL_SIGNALS=$(grep -c '"blind_spot_signals":\s*null' "$FIRST_LOG" 2>/dev/null)
    if [ -n "$NULL_SIGNALS" ] && [ "$NULL_SIGNALS" -gt 0 ]; then
        fail "检测到 $NULL_SIGNALS 处 blind_spot_signals 为 null（应为数组）"
    else
        pass "blind_spot_signals 类型正确（非 null）"
    fi
    
    # 检查 blind_spot_score 是否为字符串（类型错误）
    STRING_SCORE=$(grep -c '"blind_spot_score":\s*"' "$FIRST_LOG" 2>/dev/null)
    if [ -n "$STRING_SCORE" ] && [ "$STRING_SCORE" -gt 0 ]; then
        fail "检测到 $STRING_SCORE 处 blind_spot_score 为字符串（应为数值）"
    else
        pass "blind_spot_score 类型正确（数值型）"
    fi
else
    warn "无法检查字段类型（无日志文件）"
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
