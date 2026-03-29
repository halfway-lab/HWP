#!/usr/bin/env bash
#
# HWP 结构化验证脚本 - 第2步最小可行版本
#
# 用途：自动验证日志文件的 JSON 结构和协议约束
#
# 执行方式：
#   ./runs/verify_structured.sh [logs_dir]
#   ./runs/verify_structured.sh reports/benchmarks/20260329T155924/probe/logs
#

set +e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

LOGS_DIR="${1:-./logs}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

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

# 检查 JSON 是否可解析
check_json_parse() {
    local file="$1"
    local line_num="$2"
    local content="$3"
    
    if echo "$content" | python3 -c "import json,sys; json.load(sys.stdin)" 2>/dev/null; then
        return 0
    else
        fail "Line $line_num: JSON parse failed"
        return 1
    fi
}

# 检查必填字段
check_required_fields() {
    local content="$1"
    local line_num="$2"
    
    python3 - "$content" << 'PYTHON_SCRIPT'
import json
import sys

content = sys.argv[1]
try:
    data = json.loads(content)
    
    # 检查顶层结构
    if "payloads" not in data:
        print("MISSING: payloads")
        sys.exit(1)
    
    payloads = data.get("payloads", [])
    if not payloads or not isinstance(payloads, list):
        print("INVALID: payloads must be non-empty array")
        sys.exit(1)
    
    # 获取 text 字段中的 JSON
    text_content = payloads[0].get("text", "{}")
    inner = json.loads(text_content)
    
    # 必填字段列表
    required = [
        "node_id", "parent_id", "round", "questions", 
        "variables", "paths", "tensions", "unfinished",
        "entropy_score", "novelty_rate", "shared_variable_count", "drift_rate",
        "collapse_detected", "recovery_applied", "speed_metrics"
    ]
    
    missing = []
    for field in required:
        if field not in inner:
            missing.append(field)
    
    if missing:
        print(f"MISSING_FIELDS: {','.join(missing)}")
        sys.exit(1)
    
    print("OK")
    sys.exit(0)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
PYTHON_SCRIPT
}

# 检查协议约束
check_protocol_constraints() {
    local content="$1"
    local line_num="$2"
    
    python3 - "$content" << 'PYTHON_SCRIPT'
import json
import sys

content = sys.argv[1]
errors = []
warnings = []

try:
    data = json.loads(content)
    text_content = data.get("payloads", [{}])[0].get("text", "{}")
    inner = json.loads(text_content)
    
    # 1. questions 数量检查 (3-5)
    questions = inner.get("questions", [])
    if not (3 <= len(questions) <= 5):
        errors.append(f"questions count {len(questions)} not in [3,5]")
    
    # 2. variables 数量检查 (15-30)
    variables = inner.get("variables", [])
    if not (15 <= len(variables) <= 30):
        errors.append(f"variables count {len(variables)} not in [15,30]")
    
    # 3. paths 数量检查 (>=3)
    paths = inner.get("paths", [])
    if len(paths) < 3:
        errors.append(f"paths count {len(paths)} < 3")
    
    # 4. tensions 数量检查 (1-3) - 实际输出可能为3
    tensions = inner.get("tensions", [])
    if not (1 <= len(tensions) <= 3):
        errors.append(f"tensions count {len(tensions)} not in [1,3]")
    
    # 5. unfinished 数量检查 (>=3)
    unfinished = inner.get("unfinished", [])
    if len(unfinished) < 3:
        errors.append(f"unfinished count {len(unfinished)} < 3")
    
    # 6. entropy_score 范围检查 [0,1]
    entropy = inner.get("entropy_score")
    if entropy is not None and not (0 <= entropy <= 1):
        errors.append(f"entropy_score {entropy} not in [0,1]")
    
    # 7. drift_rate 范围检查 [0,1]
    drift = inner.get("drift_rate")
    if drift is not None and not (0 <= drift <= 1):
        errors.append(f"drift_rate {drift} not in [0,1]")
    
    # 8. v0.6 字段检查（如果有）
    if "blind_spot_signals" in inner:
        signals = inner.get("blind_spot_signals", [])
        score = inner.get("blind_spot_score")
        if score is not None and not (0 <= score <= 1):
            errors.append(f"blind_spot_score {score} not in [0,1]")
    
    if errors:
        print(f"ERRORS: {'; '.join(errors)}")
        sys.exit(1)
    
    if warnings:
        print(f"WARNINGS: {'; '.join(warnings)}")
        sys.exit(2)
    
    print("OK")
    sys.exit(0)
    
except Exception as e:
    print(f"EXCEPTION: {e}")
    sys.exit(1)
PYTHON_SCRIPT
}

# 主验证流程
echo "========================================"
echo "HWP Structured Verification"
echo "Logs: $LOGS_DIR"
echo "========================================"
echo

if [ ! -d "$LOGS_DIR" ]; then
    fail "Logs directory not found: $LOGS_DIR"
    exit 1
fi

LOG_FILES=$(find "$LOGS_DIR" -maxdepth 1 -name "*.jsonl" -type f 2>/dev/null | sort)

if [ -z "$LOG_FILES" ]; then
    fail "No .jsonl files found in $LOGS_DIR"
    exit 1
fi

TOTAL_LINES=0
for LOG_FILE in $LOG_FILES; do
    echo "Checking: $(basename "$LOG_FILE")"
    
    LINE_NUM=0
    while IFS= read -r line || [ -n "$line" ]; do
        LINE_NUM=$((LINE_NUM + 1))
        TOTAL_LINES=$((TOTAL_LINES + 1))
        
        # 1. JSON 可解析性
        if ! check_json_parse "$LOG_FILE" "$LINE_NUM" "$line"; then
            continue
        fi
        
        # 2. 必填字段检查
        REQUIRED_RESULT=$(check_required_fields "$line" "$LINE_NUM")
        if [ "$REQUIRED_RESULT" != "OK" ]; then
            if [[ "$REQUIRED_RESULT" == MISSING* ]]; then
                fail "Line $LINE_NUM: $REQUIRED_RESULT"
                continue
            fi
        fi
        
        # 3. 协议约束检查
        CONSTRAINT_RESULT=$(check_protocol_constraints "$line" "$LINE_NUM")
        CONSTRAINT_EXIT=$?
        
        if [ $CONSTRAINT_EXIT -eq 0 ]; then
            pass "Line $LINE_NUM: All constraints satisfied"
        elif [ $CONSTRAINT_EXIT -eq 2 ]; then
            warn "Line $LINE_NUM: $CONSTRAINT_RESULT"
        else
            fail "Line $LINE_NUM: $CONSTRAINT_RESULT"
        fi
        
    done < "$LOG_FILE"
done

echo
echo "========================================"
echo "Summary"
echo "========================================"
echo "Total lines checked: $TOTAL_LINES"
echo -e "${GREEN}PASS: $PASS_COUNT${NC}"
echo -e "${RED}FAIL: $FAIL_COUNT${NC}"
echo -e "${YELLOW}WARN: $WARN_COUNT${NC}"

if [ $FAIL_COUNT -eq 0 ]; then
    echo
    echo -e "${GREEN}All structured checks passed!${NC}"
    exit 0
else
    echo
    echo -e "${RED}Some checks failed.${NC}"
    exit 1
fi
