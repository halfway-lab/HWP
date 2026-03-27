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
    
    # 解析并测试每个样本
    if command -v python3 >/dev/null 2>&1; then
        python3 - "$FIXTURE_TYPE" << 'PYTHON_SCRIPT'
import json
import sys

fixture_type = sys.argv[1] if len(sys.argv) > 1 else "valid"
fixture_file = f"./tests/fixtures/semantic_groups_{fixture_type}.json"

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
        
        semantic_groups = sample_data.get('semantic_groups', [])
        cross_domain_contamination = sample_data.get('cross_domain_contamination', False)
        
        if not semantic_groups:
            errors.append("No semantic_groups found")
        else:
            for idx, group in enumerate(semantic_groups):
                group_id = group.get('group_id')
                group_name = group.get('group_name', '')
                coherence_score = group.get('coherence_score', 0)
                nodes = group.get('nodes', [])
                expansion_path = group.get('expansion_path', [])
                
                # 检查 group_id 有效性
                if group_id is None:
                    errors.append(f"Group[{idx}]: group_id is null")
                elif not isinstance(group_id, str):
                    errors.append(f"Group[{idx}]: group_id is not string: {type(group_id)}")
                
                # 检查 group_id 稳定性（如果存在 previous_group_id）
                previous_id = group.get('previous_group_id')
                if previous_id and group_id != previous_id:
                    errors.append(f"Group[{idx}]: group_id changed from {previous_id} to {group_id}")
                
                # 检查 coherence_score 阈值
                if coherence_score < 0.5:  # 阈值：低于 0.5 视为噪音
                    errors.append(f"Group[{idx}]: coherence_score {coherence_score} below threshold (0.5)")
                
                # 检查 nodes 与 expansion_path 一致性
                node_ids = {n.get('node_id') for n in nodes if isinstance(n, dict)}
                path_ids = set(expansion_path)
                if path_ids and not path_ids.issubset(node_ids):
                    missing = path_ids - node_ids
                    errors.append(f"Group[{idx}]: expansion_path contains unknown nodes: {missing}")
                
                # 检查节点 parent_node 引用（可追踪性）
                # 注意：只在显式标记需要追踪性检查时才验证 parent_node
                # 因为 valid fixtures 中很多节点没有 parent_node 字段
                null_parent_count = 0
                for node_idx, node in enumerate(nodes):
                    if isinstance(node, dict):
                        parent_node = node.get('parent_node')
                        node_id = node.get('node_id', f'Node[{node_idx}]')
                        # 检查 parent_node 引用是否有效（指向组内存在的节点）
                        if parent_node is not None and parent_node not in node_ids:
                            errors.append(f"Group[{idx}].{node_id}: parent_node '{parent_node}' not found in group")
                        # 统计显式设置为 null 的 parent_node
                        if parent_node is None and 'parent_node' in node:
                            null_parent_count += 1
                
                # 如果多个节点显式设置 parent_node=null，视为不可追踪扩展
                if null_parent_count > 1:
                    errors.append(f"Group[{idx}]: {null_parent_count} nodes have parent_node=null (untraceable expansion)")
                
                # 检查 contaminated_domains
                contaminated = group.get('contaminated_domains', [])
                if contaminated:
                    errors.append(f"Group[{idx}]: has contaminated_domains: {contaminated}")
        
        # 检查跨域污染标记
        if cross_domain_contamination:
            errors.append("cross_domain_contamination flag is true")
        
        # 检查 contamination_flag 在节点中
        for group in semantic_groups:
            for node in group.get('nodes', []):
                if isinstance(node, dict) and node.get('contamination_flag'):
                    errors.append(f"Node {node.get('node_id', '?')} has contamination_flag=true")
        
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
    # 检查 semantic_group 相关字段
    if grep -q 'semantic_group' "$FIRST_LOG" 2>/dev/null || \
       grep -q 'group_id' "$FIRST_LOG" 2>/dev/null || \
       grep -q 'group_expansion' "$FIRST_LOG" 2>/dev/null; then
        pass "日志包含语义组相关字段"
    else
        warn "日志中未找到语义组字段（待 V06-003 完成后实现）"
    fi
    
    # 检查语义一致性标记
    if grep -q 'semantic_coherence' "$FIRST_LOG" 2>/dev/null || \
       grep -q 'group_consistency' "$FIRST_LOG" 2>/dev/null; then
        pass "日志包含语义一致性标记"
    else
        warn "日志中未找到语义一致性标记（待 V06-003 完成后实现）"
    fi
else
    warn "无日志文件可供分析"
fi

# ==================== Failure Condition 1 ====================
# 检查语义组标识符断裂（重复或缺失）
info "检查语义组标识符完整性..."
if [ -n "$FIRST_LOG" ] && [ -f "$FIRST_LOG" ]; then
    # 检查是否有 group_id 字段但存在 null 值（标识符断裂迹象）
    NULL_GROUPS=$(grep -o '"group_id":\s*null' "$FIRST_LOG" 2>/dev/null | wc -l)
    if [ "$NULL_GROUPS" -gt 0 ]; then
        fail "检测到 $NULL_GROUPS 处语义组标识符为空（group_id: null）"
    else
        pass "未发现语义组标识符断裂"
    fi
else
    warn "无法检查语义组标识符（无日志文件）"
fi

# ==================== Failure Condition 2 ====================
# 检查跨域污染（不相关的语义组混合）
info "检查跨域污染..."
if [ -n "$FIRST_LOG" ] && [ -f "$FIRST_LOG" ]; then
    # 检查是否有 domain_mismatch 或 cross_domain 标记
    CROSS_DOMAIN=$(grep -c 'domain_mismatch\|cross_domain\|group_contamination' "$FIRST_LOG" 2>/dev/null)
    if [ -z "$CROSS_DOMAIN" ]; then
        CROSS_DOMAIN=0
    fi
    if [ "$CROSS_DOMAIN" -gt 0 ]; then
        fail "检测到 $CROSS_DOMAIN 处跨域污染标记"
    else
        pass "未发现跨域污染标记"
    fi
else
    warn "无法检查跨域污染（无日志文件）"
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
