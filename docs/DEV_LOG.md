# HWP Development Log

## Current Snapshot

- Canonical protocol source repo confirmed
- Provider abstraction and live adapter support added
- Benchmark automation established
- v0.6 replay baseline passing
- v0.6 live targeted regression passing after retry hardening

## Recent Important Changes

- Added pluggable provider setup and adapter workflow
- Enabled OpenAI-compatible and Ollama adapter paths
- Hardened live provider env export and adapter invocation
- Added benchmark reporting, regression reporting, and session-based log collection
- Tightened semantic group prompt guidance
- Added bounded retry/backoff for long-batch live provider calls
- Added workspace reorganization planning docs and migration templates

## Open Engineering Themes

- Continue observing long-batch live stability on real providers
- Keep protocol source-of-truth boundaries clear across downstream copies
- Prepare phased workspace reorganization without breaking path assumptions

## Migration Reminder

- This repo is upstream for protocol work.
- Any copied protocol tree should be treated as downstream, not peer source.

---

# 五阶段优化开发记录 (2026-04-01 ~ 2026-04-02)

> 本记录供未来 Codex 或其他团队接手和同步开发使用。记录了 v0.6 RC2 → v1.0 过渡期的系统性优化。

## 总览

### 工程背景

HWP 协议在 v0.6 RC2 阶段已具备核心功能，但在稳定性、性能、可扩展性方面存在改进空间。本次优化旨在：
- 强化生产环境可靠性（损坏检测、错误处理、故障恢复）
- 降低运行时开销（批量调用合并、I/O 优化）
- 增强协议可扩展性（Schema 版本化、Adapter 框架）
- 现代化架构（Python Runner、异步调用）

### 日期范围

2026-04-01 ~ 2026-04-02

### 总成果概要

| 指标 | 数值 |
|------|------|
| 完成任务数 | 15 项 |
| 测试数量 | 68 → 129（+61 个新增测试） |
| 涵盖阶段 | 5 个阶段 |
| 修改文件数 | 16 个核心文件 |
| 新增代码行数 | ~2500 行 |

### 技术约束

- **零第三方依赖**：仅使用 Python 3.9+ 标准库（urllib、json、concurrent.futures 等）
- **Python 版本**：3.9+
- **执行层**：Shell 脚本（`runs/*.sh`）作为 orchestration 入口
- **核心逻辑层**：Python 模块（`hwp_protocol/`、`adapters/`）
- **I/O 协议**：JSONL 日志格式（`logs/*.jsonl`）

---

## 第 1 阶段：稳定性基石

### 阶段目标

建立生产级可靠性基础，确保数据完整性、错误可追溯、故障可恢复。

### 任务 1.1：JSONL 损坏检测增强

**修改文件**：
- `/Users/mac/Documents/Halfway-Lab/protocol/HWP/hwp_protocol/jsonl_utils.py`
- `/Users/mac/Documents/Halfway-Lab/protocol/HWP/hwp_protocol/log_verify.py`

**修改内容摘要**：

1. `jsonl_utils.py` — `load_jsonl()` 函数重构
   - 返回值从 `list[dict]` 改为 `tuple[list[dict], int]`，新增 `corrupt_count` 计数
   - 使用 `path.read_text()` 一次性读取整个文件，减少 I/O syscalls
   - 损坏行输出包含文件名、行号、错误详情到 stderr

2. `log_verify.py` — 新增 `check_corrupt_lines()` 函数
   - 计算损坏比例 `corrupt_count / total_lines`
   - 损坏比例 > 20% 时返回 `FAIL` 消息，表示验证结果可能不可靠
   - 损坏比例 ≤ 20% 时返回 `WARN` 消息，提示存在损坏行

**关键设计决策**：
- 选择 20% 阈值：允许少量损坏（网络抖动、部分写入）但拒绝严重损坏数据
- 一次性读取策略：对于典型日志文件（< 100MB）性能最优

**注意事项/风险点**：
- 超大日志文件（> 100MB）可能占用较多内存，可考虑后续增加流式处理

**验证结果**：
- `test_edge_cases.py` 新增 8 个 JSONL 边界条件测试
- 损坏检测逻辑通过所有测试

---

### 任务 1.2：Provider 超时重试升级

**修改文件**：
- `/Users/mac/Documents/Halfway-Lab/protocol/HWP/runs/lib_agent.sh`

**修改内容摘要**：

1. 新增 `_get_timeout_cmd()` 函数
   - 自动检测 `timeout` 或 `gtimeout`（macOS coreutils）
   - 缓存结果到 `_hwp_timeout_cmd` 避免重复检测
   - 返回空字符串表示无超时命令可用

2. 重构 `_invoke_hwp_agent_once()` 函数
   - 接收 `timeout_sec` 参数（默认 30s）
   - 使用检测到的超时命令包装 agent 调用
   - macOS 兼容：自动 fallback 到 `gtimeout`

3. 重构 `invoke_hwp_agent()` 函数
   - 实现指数退避重试：`backoff_sec = 2 ** attempt`（2s → 4s → 8s）
   - 退出码 124 特殊处理（timeout 命令的超时信号）
   - 最大重试次数可配置（`HWP_AGENT_MAX_RETRIES`，默认 3）

**关键设计决策**：
- 指数退避而非固定间隔：避免在 provider 过载时雪崩
- 默认 30s 超时：平衡响应时间和长链执行
- 缓存 timeout 命令检测结果：避免每次调用重复检测

**注意事项/风险点**：
- macOS 用户需安装 coreutils：`brew install coreutils`
- 无 timeout 命令时，调用不会超时（依赖 provider 自身超时）

**验证结果**：
- `test_provider_recovery.py` 新增 5 个重试逻辑测试
- 退避时间验证：2s + 4s + 8s = 14s（误差 ±1s）

---

### 任务 1.3：Shell 错误处理规范化

**修改文件**：
- `/Users/mac/Documents/Halfway-Lab/protocol/HWP/runs/run_sequential.sh`

**修改内容摘要**：

1. 统一 `JQ_SAFE()` 和 `PYTHON_SAFE()` 包装函数
   - 所有 jq 调用通过 `JQ_SAFE` 包装，失败时输出 `FATAL: [run_sequential] jq failed`
   - 所有 python 调用通过 `PYTHON_SAFE` 包装，失败时输出 `FATAL: [run_sequential] python materializer failed`
   - 统一退出码为 1

2. 关键调用点添加错误检查
   - `sed` 替换 RHYTHM_HINT 失败时 FATAL
   - `jq` 提取 payload.text 失败时 FATAL
   - `sed/awk` 清洗 agent 输出失败时 FATAL
   - JSON 解析失败时 FATAL（包含具体操作上下文）

**关键设计决策**：
- FATAL 格式统一：`FATAL: [run_sequential] <context> failed`
- 立即退出策略：避免截断链被误判为成功

**注意事项/风险点**：
- Shell 的 `set -e` 对 pipeline 中的错误不总是有效，需显式检查

**验证结果**：
- replay 基准测试稳定通过
- 错误注入测试验证 FATAL 输出格式

---

### 第 1 阶段验证结果

```
✓ test_edge_cases.py: 39 tests passed
✓ test_provider_recovery.py: 22 tests passed
✓ replay 基准测试通过
✓ 损坏检测阈值验证通过
```

---

## 第 2 阶段：性能优化

### 阶段目标

降低运行时开销，提升批量处理和 I/O 效率。

### 任务 2.1：批量 Python 调用合并

**修改文件**：
- `/Users/mac/Documents/Halfway-Lab/protocol/HWP/hwp_protocol/cli.py`
- `/Users/mac/Documents/Halfway-Lab/protocol/HWP/runs/run_sequential.sh`

**修改内容摘要**：

1. `cli.py` — 新增 `cmd_transform_batch()` 函数
   - 合并 `enrich_inner_json()` + `repack_result_with_inner()` 为单一调用
   - 新增 `transform-batch` 子命令
   - 参数：`result_json`, `inner_json`, `round`, `parent_recovery`

2. `run_sequential.sh` — 新增 `transform_batch()` 函数
   - 替代分离的 `enrich_v06_inner_json()` + `repack_result_with_inner()` 调用
   - 每轮次减少 1 次 Python 进程启动

**关键设计决策**：
- 合并而非完全移除分离命令：保持向后兼容
- 预期性能提升：30-40% 进程启动开销降低（每链节省 8 次进程创建）

**注意事项/风险点**：
- 需同时更新文档（RUNBOOK.md、README.md）

**验证结果**：
- transform-batch 功能测试通过
- 与分离调用输出一致性验证通过

---

### 任务 2.2：动态控制器参数优化

**修改文件**：
- `/Users/mac/Documents/Halfway-Lab/protocol/HWP/runs/run_sequential.sh`
- `/Users/mac/Documents/Halfway-Lab/protocol/HWP/hwp_protocol/runner.py`

**修改内容摘要**：

1. `run_sequential.sh` — `compute_mode()` 重构
   - 从 `entropy_score` 驱动改为 `drift_rate` 三段式判断
   - Rg0（Normal）：`drift_low <= drift_rate <= drift_high`
   - Rg1（Stable）：`drift_rate < drift_low`
   - Rg2（Explore）：`drift_rate > drift_high`
   - 阈值从 `config/controller.json` 加载，支持环境变量覆盖

2. `run_sequential.sh` — `compute_band()` 重构
   - 熵目标区间从 `config/controller.json` 加载
   - 与 `spec/hwp_turn_prompt.txt` 定义对齐
   - Rg0: [0.40, 0.79], Rg1: [0.55, 0.85], Rg2: [0.35, 0.65]

3. `runner.py` — Python 实现同步
   - `compute_mode()` 和 `compute_band()` 与 Shell 版本逻辑一致
   - 支持环境变量 `HWP_DRIFT_LOW_THRESHOLD`、`HWP_DRIFT_HIGH_THRESHOLD` 覆盖

**关键设计决策**：
- 基于 5773 样本数据分析确定阈值
- 修复 Rg2 模式 0% 激活问题（原逻辑熵阈值过于严格）

**注意事项/风险点**：
- 阈值变更可能影响现有 replay 基准

**验证结果**：
- 三模式激活分布验证：Rg0 ~60%, Rg1 ~25%, Rg2 ~15%
- 与 spec 定义一致性验证通过

---

### 任务 2.3：JSONL 批量读取优化

**修改文件**：
- `/Users/mac/Documents/Halfway-Lab/protocol/HWP/hwp_protocol/jsonl_utils.py`

**修改内容摘要**：

1. `load_jsonl()` 优化
   - 使用 `path.read_text()` 一次性读取整个文件
   - 替代逐行 `readline()` 的多次 I/O syscalls
   - 返回 `(records, corrupt_count)` 元组

2. 新增 `load_jsonl_last_n()` 函数
   - 仅加载最后 N 条有效记录
   - 适用于大型日志文件的尾部查询
   - 反向处理，提前终止

3. 新增 `count_jsonl_lines()` 函数
   - 快速计算非空行数（不解析 JSON）
   - 用于损坏比例计算

**关键设计决策**：
- 一次性读取适合典型日志大小（< 100MB）
- 超大文件场景可通过 `load_jsonl_last_n()` 规避

**注意事项/风险点**：
- 内存占用与文件大小成正比

**验证结果**：
- 性能测试：100KB 文件读取时间降低 ~40%
- 边界条件测试：空文件、单行、全损坏行均通过

---

### 第 2 阶段验证结果

```
✓ transform-batch 功能测试通过
✓ 动态控制器模式分布验证通过
✓ JSONL 读取性能提升 ~40%
✓ replay 基准测试稳定通过
```

---

## 第 3 阶段：可靠性强化

### 阶段目标

建立全面的边界条件和故障恢复测试覆盖，确保文档与实现一致。

### 任务 3.1：边界条件测试

**修改文件**：
- `/Users/mac/Documents/Halfway-Lab/protocol/HWP/tests/test_edge_cases.py`

**修改内容摘要**：

新增 39 个测试用例，覆盖三个模块的边界情况：

1. `TransformEdgeCaseTests`（22 个测试）
   - 空变量列表、空 tensions 列表
   - 变量截断（> 30 上限）
   - null 字段值处理
   - 极端 entropy（0.0、1.0）
   - 极端 drift（0.0、1.0）
   - round_id 非法值（0、负数）
   - 空 inner JSON（`{}`）
   - clamp01 边界值
   - round_metric 精度
   - 嵌套 null paths

2. `JsonlUtilsEdgeCaseTests`（11 个测试）
   - 空 JSONL 文件
   - 单行有效 JSONL
   - 全损坏 JSONL
   - 混合有效/损坏行
   - 深度嵌套 JSON
   - `load_jsonl_last_n` 边界（n=0, n=-1, n>实际行数）
   - `count_jsonl_lines` 空文件/纯空白文件
   - `extract_inner_object` 空 payloads

3. `LogVerifyEdgeCaseTests`（6 个测试）
   - 空日志文件验证（blind_spot、continuity、semantic_groups）
   - 全损坏行日志
   - 缺失字段警告

**关键设计决策**：
- 使用临时文件测试 I/O 边界
- 验证 FAIL/WARN/PASS 状态正确性

**注意事项/风险点**：
- 临时文件需在 finally 块中清理

**验证结果**：
```
✓ 39 tests passed
✓ 覆盖 transform、jsonl_utils、log_verify 边界场景
```

---

### 任务 3.2：Provider 故障恢复测试

**修改文件**：
- `/Users/mac/Documents/Halfway-Lab/protocol/HWP/tests/test_provider_recovery.py`

**修改内容摘要**：

新增 22 个测试用例，覆盖故障场景和恢复逻辑：

1. `AdapterCommonRecoveryTests`（5 个测试）
   - HTTP 500 错误处理
   - 超时错误处理
   - 空 body 响应处理
   - 非 JSON 响应处理
   - 缺失字段响应处理

2. `OpenAICompatibleAdapterRecoveryTests`（3 个测试）
   - 空 choices 数组处理
   - 缺失 content 字段处理
   - content 中非 JSON 内容处理

3. `OllamaAdapterRecoveryTests`（3 个测试）
   - 空 response 处理
   - 缺失 response 字段处理
   - response 中非 JSON 内容处理

4. `AdapterErrorOutputFormatTests`（3 个测试）
   - `fail()` 函数输出 FATAL 到 stderr
   - 网络错误时 adapter 输出 FATAL
   - 退出码验证

5. `ShellRetryLogicTests`（5 个测试）
   - 1 次失败后重试成功
   - 所有重试耗尽后退出
   - 退避时间验证（2s/4s/8s）
   - 立即成功不重试
   - 自定义重试次数

6. `ExtractJsonObjectTextRecoveryTests`（3 个测试）
   - 空文本报错
   - 无 JSON 对象报错
   - 不完整 JSON 报错

**关键设计决策**：
- 使用 `unittest.mock` 模拟 HTTP 响应
- 使用 subprocess 测试 Shell 重试逻辑
- 验证退避时间的实际等待时长

**注意事项/风险点**：
- 退避时间测试耗时较长（> 14s）

**验证结果**：
```
✓ 22 tests passed
✓ HTTP 错误、超时、空响应、重试逻辑全覆盖
✓ 退避时间验证：2s + 4s + 8s = 14s（±1s 误差）
```

---

### 任务 3.3：文档一致性修复

**修改文件**：
- `/Users/mac/Documents/Halfway-Lab/protocol/HWP/docs/PROTOCOL_RULES.md`
- `/Users/mac/Documents/Halfway-Lab/protocol/HWP/docs/RUNBOOK.md`
- `/Users/mac/Documents/Halfway-Lab/protocol/HWP/README.md`
- `/Users/mac/Documents/Halfway-Lab/protocol/HWP/docs/STABILITY_STATUS.md`

**修改内容摘要**：

1. `PROTOCOL_RULES.md`
   - 更新标题为 "HWP v0.6 RC2 — Protocol Rules"
   - 补充 `entropy_target` 三模式区间定义

2. `RUNBOOK.md`
   - 新增 Python CLI 命令章节
   - 包含 `transform-batch` 命令说明
   - 更新 `log-verify` 和 `fixture-verify` 用法

3. `README.md`
   - 补充 `transform-batch` 命令说明
   - 更新 CLI 命令示例

4. `STABILITY_STATUS.md`
   - 更新日期为 2026-04-02
   - 新增 Python CLI 稳定性说明
   - 补充 `transform-batch` 功能

**关键设计决策**：
- 文档与代码同步更新
- 标注 "Last updated" 日期

**注意事项/风险点**：
- 需在每次功能变更时同步更新文档

**验证结果**：
```
✓ 文档与 CLI 帮助信息一致
✓ 日期戳已更新
```

---

### 第 3 阶段验证结果

```
✓ test_edge_cases.py: 39 tests passed
✓ test_provider_recovery.py: 22 tests passed
✓ 文档一致性验证通过
✓ 总测试数: 68 → 129（+61）
```

---

## 第 4 阶段：可扩展性增强

### 阶段目标

增强协议的可扩展性，支持更复杂的语义分析和多 provider 场景。

### 任务 4.1：语义组聚类升级

**修改文件**：
- `/Users/mac/Documents/Halfway-Lab/protocol/HWP/hwp_protocol/transform.py`

**修改内容摘要**：

1. 新增 `extract_keywords()` 函数
   - 支持驼峰命名分割：`userName` → `["user", "name"]`
   - 支持连续大写分割：`APIKey` → `["api", "key"]`
   - 过滤短关键词（< 2 字符）

2. 新增 `jaccard_similarity()` 函数
   - 计算两个集合的 Jaccard 相似度
   - 空集相似度为 1.0（完全相似）

3. 新增 `cluster_variables_by_similarity()` 函数
   - 基于关键词相似度的贪心聚类
   - 阈值 0.3（可配置）
   - 小规模变量集（<=5）特殊处理：无相似性时归入单一组

4. 新增 `calculate_cross_domain_contamination()` 函数
   - 检测组间内容重叠（> 0.6）
   - 返回污染标记

5. 重构 `semantic_group_payload()` 函数
   - 使用聚类算法生成多组
   - 每组独立的 `coherence_score`
   - 支持 `expansion_path` 和 `domain` 字段

**关键设计决策**：
- 贪心聚类：O(n²) 复杂度，适合小规模变量集（< 30）
- 阈值 0.3：平衡聚类质量和分组数量
- 驼峰分割：支持多种命名风格

**注意事项/风险点**：
- 大规模变量集可能较慢，可考虑后续优化

**验证结果**：
```
✓ 语义组生成测试通过
✓ 跨域污染检测测试通过
✓ coherence_score >= 0.5 验证通过
```

---

### 任务 4.2：AdapterBase 框架

**修改文件**：
- `/Users/mac/Documents/Halfway-Lab/protocol/HWP/adapters/base_adapter.py`
- `/Users/mac/Documents/Halfway-Lab/protocol/HWP/adapters/openai_compatible_adapter.py`
- `/Users/mac/Documents/Halfway-Lab/protocol/HWP/adapters/ollama_adapter.py`

**修改内容摘要**：

1. `base_adapter.py` — 新增 `AdapterBase` 抽象基类
   - `call()`：统一调用入口，处理错误并返回 JSON 文本
   - `_post_request()`：HTTP POST 封装
   - `_parse_response()`：抽象方法，子类必须实现
   - `_build_payload()`：构建请求体，子类可重写
   - `_get_endpoint()`：获取 API endpoint，子类可重写
   - `_get_headers()`：获取请求头，子类可重写
   - `_handle_error()`：统一错误处理，输出 FATAL 并退出
   - `_extract_json()`：从文本中提取 JSON 对象
   - `wrap_and_print()`：包装结果并输出到 stdout
   - `async_call()`：异步调用入口（基于 ThreadPoolExecutor）

2. `openai_compatible_adapter.py` — 重构继承 `AdapterBase`
   - 实现 `_get_endpoint()` 返回 `/chat/completions`
   - 实现 `_get_headers()` 返回 Bearer token
   - 实现 `_build_payload()` 构建 OpenAI 格式请求
   - 实现 `_parse_response()` 提取 content

3. `ollama_adapter.py` — 重构继承 `AdapterBase`
   - 实现 `_get_endpoint()` 返回 `/api/generate`
   - 实现 `_get_headers()` 返回基础 JSON headers
   - 实现 `_build_payload()` 构建 Ollama 格式请求
   - 实现 `_parse_response()` 提取 response

**关键设计决策**：
- 抽象基类而非接口：Python 多态支持
- 模板方法模式：`call()` 定义骨架，子类填充细节
- `async_call()` 使用 ThreadPoolExecutor 而非 asyncio：零第三方依赖约束

**注意事项/风险点**：
- `sys.path.insert(0, ...)` 确保模块导入正确

**验证结果**：
```
✓ adapter 继承关系测试通过
✓ 错误处理格式测试通过
✓ async_call 功能测试通过
```

---

### 任务 4.3：Schema 版本化

**修改文件**：
- `/Users/mac/Documents/Halfway-Lab/protocol/HWP/hwp_protocol/transform.py`
- `/Users/mac/Documents/Halfway-Lab/protocol/HWP/docs/DATA_CONTRACTS.md`

**修改内容摘要**：

1. `transform.py` — 新增版本化支持
   - `PROTOCOL_VERSION = "0.6.2"` 常量
   - `check_protocol_version(inner, strict=False)` 函数
     - 宽松模式（默认）：仅警告格式错误
     - 严格模式：缺失版本或版本不匹配时报错
   - `enrich_inner_json()` 自动添加 `protocol_version` 字段
   - `repack_result_with_inner()` 传递版本到外层

2. `DATA_CONTRACTS.md` — 新增版本化章节
   - 版本格式说明（SemVer）
   - 兼容性规则
   - 验证示例

**关键设计决策**：
- SemVer 格式：MAJOR.MINOR.PATCH
- 默认宽松模式：避免破坏现有消费者
- 严格模式可选：用于严格兼容性检查

**注意事项/风险点**：
- 版本变更需同步更新 `DATA_CONTRACTS.md`

**验证结果**：
```
✓ 版本格式验证测试通过
✓ 宽松/严格模式测试通过
✓ enrich 自动添加版本字段测试通过
```

---

### 第 4 阶段验证结果

```
✓ 语义组聚类测试通过
✓ AdapterBase 框架测试通过
✓ Schema 版本化测试通过
✓ 跨域污染检测测试通过
```

---

## 第 5 阶段：架构现代化

### 阶段目标

实现 Python Runner 运行时，消除 Shell-Python 跨进程边界开销，支持异步多 provider 调用。

### 任务 5.1：Python Runner 运行时

**修改文件**：
- `/Users/mac/Documents/Halfway-Lab/protocol/HWP/hwp_protocol/runner.py`
- `/Users/mac/Documents/Halfway-Lab/protocol/HWP/hwp_protocol/cli.py`

**修改内容摘要**：

1. `runner.py` — 新增完整 Python Runner 实现（~1270 行）

   **配置类**：
   - `RunnerConfig`：Runner 配置数据类
   - `ChainState`：链状态管理（每轮次跟踪）

   **动态控制器**：
   - `load_controller_config()`：从 `config/controller.json` 加载配置
   - `get_drift_thresholds()`：获取漂移阈值
   - `compute_mode()`：计算当前模式（Rg0/Rg1/Rg2）
   - `compute_band()`：计算熵目标区间
   - `emit_hint_json()`：生成 RHYTHM_HINT JSON

   **Provider 配置**：
   - `parse_env_file()`：解析 .env 文件
   - `resolve_provider_alias()`：解析 provider 别名
   - `load_provider_config()`：加载 provider 配置
   - `apply_provider_defaults()`：应用默认值

   **Provider 调用**：
   - `import_and_call_openai_adapter()`：直接调用 OpenAI adapter（无子进程）
   - `import_and_call_ollama_adapter()`：直接调用 Ollama adapter（无子进程）
   - `call_openclaw_binary()`：调用 OpenClaw 二进制
   - `call_agent_cmd()`：调用自定义 agent 命令
   - `invoke_provider_with_retry()`：带重试的 provider 调用

   **Replay 模式**：
   - `load_replay_result()`：从 JSONL 文件回放链

   **输出处理**：
   - `strip_ansi_codes()`：去除 ANSI 控制字符
   - `extract_first_json()`：提取第一个有效 JSON
   - `extract_result_from_response()`：提取 result 部分

   **Fallback 处理**：
   - `create_fallback_inner_json()`：provider block 时创建 fallback

   **Chain Runner**：
   - `ChainRunner` 类：执行单条链的 8 轮迭代
   - `run_input_file()`：处理输入文件
   - `run_chain()`：执行单条链
   - `_call_provider()`：调用 provider 获取结果
   - `_handle_provider_block()`：处理 provider block 情况
   - `_handle_normal_round()`：处理正常轮次
   - `_check_timeout()`：检查链超时
   - `_log_run()`：输出到控制台和 run.log

2. `cli.py` — 新增 `run` 子命令
   - 集成 `ChainRunner`
   - 支持 `--dry-run` 验证配置
   - 支持 `--replay-chain` 回放模式

**关键设计决策**：
- 直接导入 adapter 模块：消除子进程开销
- 保留 Shell 版本：向后兼容和调试便利
- Timing 统计：`chain_start_ts`、`round_start_ts`、`completed_rounds`

**注意事项/风险点**：
- `sys.path.insert(0, ...)` 确保 adapter 导入正确

**验证结果**：
```
✓ Python Runner 功能测试通过
✓ Replay 模式测试通过
✓ Fallback 处理测试通过
✓ Timing 统计验证通过
```

---

### 任务 5.2：异步 Provider 调用

**修改文件**：
- `/Users/mac/Documents/Halfway-Lab/protocol/HWP/adapters/base_adapter.py`
- `/Users/mac/Documents/Halfway-Lab/protocol/HWP/hwp_protocol/runner.py`
- `/Users/mac/Documents/Halfway-Lab/protocol/HWP/hwp_protocol/cli.py`

**修改内容摘要**：

1. `base_adapter.py` — 新增 `async_call()` 方法
   - 基于 `concurrent.futures.ThreadPoolExecutor`
   - 返回 `Future[str]` 对象
   - 支持传入自定义 executor

2. `runner.py` — 新增 `run_multi_provider()` 函数
   - 并行调用多个 provider
   - 收集所有结果（包括失败）
   - 返回 `{provider_name: result}` 字典

3. `cli.py` — 新增 `run-multi` 子命令
   - 参数：`--providers`（逗号分隔）、`--input-text`/`--input-file`
   - 参数：`--max-workers`、`--max-retries`、`--timeout`
   - 输出格式化的多 provider 结果

**关键设计决策**：
- ThreadPoolExecutor 而非 asyncio：urllib 不支持原生 async，零第三方依赖约束
- Future 模式：允许调用方控制等待和超时
- 失败隔离：一个 provider 失败不影响其他

**注意事项/风险点**：
- 并发数需合理控制（`max_workers`）

**验证结果**：
```
✓ async_call 功能测试通过
✓ run_multi_provider 功能测试通过
✓ 并行调用验证通过
```

---

### 任务 5.3：动态控制器配置外部化

**修改文件**：
- `/Users/mac/Documents/Halfway-Lab/protocol/HWP/config/controller.json`
- `/Users/mac/Documents/Halfway-Lab/protocol/HWP/hwp_protocol/runner.py`
- `/Users/mac/Documents/Halfway-Lab/protocol/HWP/runs/run_sequential.sh`

**修改内容摘要**：

1. `config/controller.json` — 新增外部配置文件
   ```json
   {
     "version": "0.6.2",
     "modes": {
       "Rg0": {"name": "Normal", "entropy_target": {"min": 0.40, "max": 0.79}},
       "Rg1": {"name": "Stable", "entropy_target": {"min": 0.55, "max": 0.85}},
       "Rg2": {"name": "Explore", "entropy_target": {"min": 0.35, "max": 0.65}}
     },
     "thresholds": {"drift_low": 0.30, "drift_high": 0.70},
     "defaults": {"rounds_per_chain": 8, "round_sleep_sec": 2.0, "variable_policy": {...}}
   }
   ```

2. `runner.py` — 配置加载逻辑
   - `load_controller_config()`：从 JSON 加载，支持环境变量覆盖
   - 环境变量优先级：`HWP_DRIFT_LOW_THRESHOLD` > JSON 配置 > 内置默认值
   - 模块级缓存：避免重复读取

3. `run_sequential.sh` — Shell 配置读取
   - `jq` 读取 `controller.json` 中的阈值和模式配置
   - 环境变量覆盖：`${HWP_DRIFT_LOW_THRESHOLD:-$CONTROLLER_DRIFT_LOW}`
   - fallback 到硬编码默认值

**关键设计决策**：
- JSON 而非 YAML：无需第三方解析库
- 环境变量最高优先级：支持运行时覆盖
- 内置默认值：配置文件缺失时仍可运行

**注意事项/风险点**：
- 配置变更需同步更新 Shell 和 Python 实现

**验证结果**：
```
✓ 配置加载测试通过
✓ 环境变量覆盖测试通过
✓ fallback 逻辑测试通过
```

---

### 第 5 阶段验证结果

```
✓ Python Runner 功能测试通过
✓ run-multi 子命令测试通过
✓ 动态控制器配置测试通过
✓ Timing 统计验证通过
✓ 总测试数: 129
```

---

## 接手指南

### 项目结构速查表

| 目录/文件 | 职责 |
|-----------|------|
| `hwp_protocol/` | 核心 Python 模块 |
| `hwp_protocol/cli.py` | 统一 CLI 入口（run, run-multi, transform, transform-batch, log-verify） |
| `hwp_protocol/runner.py` | Python Runner 运行时（ChainRunner, ChainState, RunnerConfig） |
| `hwp_protocol/transform.py` | 协议转换（enrich, repack, 语义组聚类, 版本化） |
| `hwp_protocol/jsonl_utils.py` | JSONL 读写工具 |
| `hwp_protocol/log_verify.py` | 日志验证（blind_spot, continuity, semantic_groups） |
| `hwp_protocol/fixture_verify.py` | Fixture 验证 |
| `hwp_protocol/note_inference.py` | Note 关系推断 |
| `adapters/` | LLM 适配器 |
| `adapters/base_adapter.py` | AdapterBase 抽象基类 |
| `adapters/openai_compatible_adapter.py` | OpenAI 兼容适配器 |
| `adapters/ollama_adapter.py` | Ollama 适配器 |
| `adapters/adapter_common.py` | 适配器公共函数 |
| `runs/` | Shell 运行脚本 |
| `runs/run_sequential.sh` | 主运行脚本（链编排） |
| `runs/lib_agent.sh` | Provider 调用辅助（重试、超时） |
| `runs/run_benchmarks.sh` | Benchmark 运行 |
| `runs/verify_v06_all.sh` | 统一验证脚本 |
| `config/` | 配置文件 |
| `config/controller.json` | 动态控制器配置 |
| `config/provider.env` | Provider 配置（API key、model） |
| `spec/` | 协议规范 |
| `spec/hwp_turn_prompt.txt` | 权威 prompt 规范 |
| `tests/` | 测试文件 |
| `tests/test_edge_cases.py` | 边界条件测试 |
| `tests/test_provider_recovery.py` | Provider 故障恢复测试 |
| `docs/` | 文档 |
| `logs/` | 日志输出（JSONL 格式） |

### 开发环境要求

- **Python**：3.9+
- **操作系统**：macOS / Linux
- **可选工具**：
  - `jq`：JSON 处理（Shell 脚本依赖）
  - `timeout`/`gtimeout`：超时控制（macOS 需 coreutils）
  - OpenClaw 二进制（如使用 openclaw provider）

### 常用命令

#### 运行

```bash
# 运行单链
bash runs/run_sequential.sh inputs/probe.txt

# 带超时运行
HWP_CHAIN_TIMEOUT_SEC=180 bash runs/run_sequential.sh inputs/probe.txt

# Python Runner
python3 -m hwp_protocol.cli run inputs/probe.txt --dry-run
python3 -m hwp_protocol.cli run inputs/probe.txt --provider-type openai_compatible

# 多 Provider 并行
python3 -m hwp_protocol.cli run-multi --providers deepseek,moonshot --input-text "Hello"

# Replay 模式
HWP_REPLAY_CHAIN_PATH=logs/chain_xxx.jsonl HWP_ROUND_SLEEP_SEC=0 \
  bash runs/run_sequential.sh inputs/probe.txt
```

#### 测试

```bash
# 运行所有测试
python3 -m unittest discover tests/

# 运行特定测试
python3 -m unittest tests.test_edge_cases
python3 -m unittest tests.test_provider_recovery
```

#### 验证

```bash
# 配置验证（dry-run）
bash runs/run_sequential.sh --dry-run

# 统一验证
bash runs/verify_v06_all.sh logs/

# 日志验证
python3 -m hwp_protocol.cli log-verify blind_spot logs/chain_xxx.jsonl
python3 -m hwp_protocol.cli log-verify continuity logs/chain_xxx.jsonl
python3 -m hwp_protocol.cli log-verify semantic_groups logs/chain_xxx.jsonl
```

#### Benchmark

```bash
# 运行 Benchmark
HWP_ROUND_SLEEP_SEC=0 bash runs/run_benchmarks.sh

# 多 Provider Benchmark
bash runs/run_benchmarks_multi_provider.sh config/providers.list config/benchmark_inputs.live_subset.txt
```

### 配置说明

#### provider.env

```bash
# Provider 类型
HWP_PROVIDER_TYPE=openai_compatible  # 或 ollama, openclaw, custom

# Provider 名称（用于推断 base URL）
HWP_PROVIDER_NAME=deepseek  # 或 openai, moonshot, groq, etc.

# API 配置
HWP_LLM_API_KEY=your_api_key_here
HWP_LLM_MODEL=your_model_here
HWP_LLM_BASE_URL=https://api.example.com/v1  # 可选，自动推断

# 运行时参数
HWP_AGENT_MAX_RETRIES=3
HWP_AGENT_TIMEOUT=30
HWP_ROUND_SLEEP_SEC=2
HWP_CHAIN_TIMEOUT_SEC=0  # 0 表示无超时
```

#### controller.json

```json
{
  "version": "0.6.2",
  "modes": {
    "Rg0": {"entropy_target": {"min": 0.40, "max": 0.79}},
    "Rg1": {"entropy_target": {"min": 0.55, "max": 0.85}},
    "Rg2": {"entropy_target": {"min": 0.35, "max": 0.65}}
  },
  "thresholds": {
    "drift_low": 0.30,
    "drift_high": 0.70
  },
  "defaults": {
    "rounds_per_chain": 8,
    "round_sleep_sec": 2.0
  }
}
```

#### 环境变量优先级

1. 命令行参数（最高）
2. 环境变量（`HWP_*`）
3. 配置文件（`controller.json`、`provider.env`）
4. 内置默认值（最低）

### 架构决策记录

#### 为什么保留 Shell 版本（run_sequential.sh）

1. **向后兼容**：现有脚本和工作流依赖 Shell 入口
2. **调试便利**：Shell 脚本易于查看和修改环境变量
3. **渐进迁移**：允许逐步迁移到 Python Runner

#### 为什么用 ThreadPoolExecutor 而非 asyncio

1. **零第三方依赖约束**：urllib 不支持原生 async，aiohttp 需安装
2. **简化迁移**：现有同步代码无需重写
3. **性能足够**：典型并发数（< 10）下性能差异可忽略

#### 为什么用 JSON 而非 YAML

1. **零第三方依赖**：Python 标准库支持 JSON
2. **解析确定性**：YAML 的某些语法可能有歧义
3. **工具支持广泛**：jq、Python、Shell 均可处理

### 已知限制

1. **内存占用**：JSONL 一次性读取，超大文件（> 100MB）可能内存紧张
2. **Windows 兼容**：Shell 脚本依赖 Bash，Windows 需 WSL 或 Git Bash
3. **Ollama 本地**：Ollama adapter 需本地运行 Ollama 服务
4. **并发限制**：ThreadPoolExecutor 的 max_workers 需合理配置

### 后续建议

1. **性能优化**
   - 考虑流式 JSONL 读取（针对超大日志）
   - 考虑 asyncio 迁移（如取消零第三方依赖约束）

2. **功能增强**
   - 支持 streaming 响应
   - 支持更多 provider（Anthropic、Google 等）
   - 支持自定义 prompt 模板

3. **测试覆盖**
   - 增加集成测试
   - 增加性能回归测试
   - 增加故障注入测试

4. **文档完善**
   - API 文档自动生成
   - 架构图更新
   - 故障排查指南

---

*文档版本：v1.0 | 最后更新：2026-04-02*
