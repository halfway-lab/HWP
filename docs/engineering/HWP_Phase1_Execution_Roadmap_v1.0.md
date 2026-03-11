HWP Phase 1 Execution Roadmap v1.0

Hardening Test Harness — Execution & Freeze Workflow

Version: 1.0
Status: Engineering Active
Applies to: v0.6.x line (baseline v0.6)

0. Phase 1 的一句话目标

把 HWP 从“能跑”推进到：

可观测、可回归、可稳定复现 的协议系统。

1. Roles & Working Mode
你（Owner / PM）

决定 Freeze / Release 节点

组织测试批次与结果归档

不负责代码实现（你已明确）

我（Engineering Lead by guidance）

给出改动清单、实现路径、验收标准

每次改动必须对应：Failure code → Fix strategy → Regression

现实限制

你可以跑脚本、上传日志

我负责“怎么改、改哪里、改完怎么验收”的工程方案（你照做或让能写代码的人照做）

2. Branch & Version Discipline
Baseline

v0.6 = frozen baseline

baseline 永远不改（只读）

Working

新建 hardening 分支（建议命名）：

hardening/phase1

每个 patch 用小步提交：

patch-001-metrics-dominance

patch-002-metrics-injection

…

标签策略

每个可跑且通过当前矩阵的状态打 tag：

v0.6-rc1

v0.6-rc2

3. Execution Pipeline（每次改动必须走）

不允许跳步。

Step A — Run Baseline Snapshot

对 v0.6 跑完整 test matrix（一次性）

产出：baseline_report.json

Step B — Implement One Patch

一次只做一类改动（例如“加 dominance_index”）

禁止同时调阈值 + 改 prompt + 改结构

Step C — Run Full Matrix

跑所有测试类（见 Test Spec）

产出：run_report.json

Step D — Diff vs Baseline

输出：

每个指标均值/方差变化

CRITICAL/MAJOR 失败次数变化

若出现新 CRITICAL → 回滚 patch

Step E — Promote / Reject

通过：进入下一个 patch

不通过：先做 Failure 分类，再决定是阈值调节还是规则修补

4. Test Matrix — Run Quotas（硬性配额）

你 Phase 1 必须跑到这些数量，才有统计意义：

4.1 Collapse Probe

N = 50 runs

Seeds：固定 10 个 seed 循环（保证可复现）

4.2 Natural Topic

N = 50 runs

Topics：至少 5 个主题轮换（避免单主题过拟合）

4.3 Entropy Boundary

Low pressure：N = 20

High pressure：N = 20

4.4 Dominance Stress

N = 30

4.5 Multi-Round Continuity (≥5 rounds)

N = 30 chains

总计：约 180 次运行（分批完成，见第 6 节）

5. Acceptance Gate（阶段闸门）

每一轮 patch 合并前必须满足：

Gate 1 — No New Critical

新 patch 不得引入 baseline 未出现的 CRITICAL failure

Gate 2 — Critical Rate Threshold

CRITICAL failures ≤ 2%（例如 180 次里 ≤ 3 次）

且不得集中在同一 failure subtype（否则说明结构性问题）

Gate 3 — Stability Band

entropy_score 的方差不得爆炸：

std(entropy_score) ≤ 0.15

dominance_index 均值不得上升超过：

+0.05

6. Batch Plan（你实际怎么跑）

把 180 次拆成 6 个批次，便于你上传与我诊断：

Batch 1：Collapse 20 + Natural 20

Batch 2：Collapse 30 + Natural 30（完成 50/50）

Batch 3：Entropy Low 20

Batch 4：Entropy High 20

Batch 5：Dominance 30

Batch 6：Continuity 30（5 rounds）

每个 Batch 输出一个压缩包 + 一个 summary。

7. Reporting Format（你发给我的“标准件”）

你每次给我结果，只要三样东西：

summary.md（自动/手写都行）
包含：

commit hash / tag

本批次测试类型 + 数量

failure 计数（按 Failure code 分组）

关键指标均值/方差

reports/*.json（机器可读）

每次 run 的指标快照

logs/chain_*.jsonl（原始链）

8. Freeze-Period Allowed Fixes（硬规则）

Phase 1 允许：

阈值微调（entropy bounds、dominance threshold）

变量保留/注入参数调节（keep_n/new_n/max_vars）

日志字段扩展

closure 检测规则加强（仅检测，不改生成原则）

Phase 1 禁止：

改“核心协议原则”（No Closure / No Single Dominance）

改链结构范式（树→图 / 新记忆机制）

引入复杂新模块（评分器、外部 reranker 等）

9. Phase 1 “完成”判定（最终出口）

Phase 1 只有在同时满足以下条件才算结束：

30 consecutive chains 无 CRITICAL

CRITICAL 总率 ≤ 2%

MAJOR 总率 ≤ 8% 且不呈上升趋势

continuity test 通过率 ≥ 90%

diff vs baseline：整体稳定性提升或持平（不得更差）

满足后，发布：

v0.6

并冻结为下一阶段 baseline
