#!/usr/bin/env bash
set -euo pipefail

# 定义输入文件列表（按你想执行的顺序排列）
INPUT_FILES=(
    "$HOME/hwp-tests/inputs/ideology.txt"
    "$HOME/hwp-tests/inputs/sparse.txt"
    "$HOME/hwp-tests/inputs/longchain.txt"
    "$HOME/hwp-tests/inputs/mixed.txt"
)

# 记录开始时间
echo "===== 全自动测试开始于 $(date) =====" > "$HOME/hwp-tests/run.log"

# 依次处理每个文件
for file in "${INPUT_FILES[@]}"; do
    echo "处理文件: $file" | tee -a "$HOME/hwp-tests/run.log"
    if [ ! -f "$file" ]; then
        echo "警告：文件 $file 不存在，跳过" | tee -a "$HOME/hwp-tests/run.log"
        continue
    fi
    # 调用顺序脚本，传入文件路径
    "$HOME/hwp-tests/runs/run_sequential.sh" "$file" >> "$HOME/hwp-tests/run.log" 2>&1
    echo "完成文件: $file" | tee -a "$HOME/hwp-tests/run.log"
done

# 创建完成标志
touch "$HOME/hwp-tests/ALL_DONE"
echo "===== 所有测试完成于 $(date) =====" | tee -a "$HOME/hwp-tests/run.log"
echo "完成标志已创建: ~/hwp-tests/ALL_DONE"
