HWP Metric Expansion Plan v1.0

Phase 1 — Hardening Instrumentation Layer

Version: 1.0
Status: Engineering Active

1. Design Philosophy

Metric 扩展目标：

可检测 Failure Taxonomy 所定义的所有 CRITICAL 类失败

不引入计算不可控的复杂指标

不依赖外部模型推理

可在本地 test harness 中计算

2. 当前已有指标

你目前已有：

entropy_score

branching_factor

basic repetition check

collapse probe / natural runs

这是基础。

但不够覆盖 Failure Taxonomy。

3. Phase 1 必须新增的 5 个核心指标

只加 5 个。

不多不少。

M1 — Dominance Index (Refined)
Purpose

检测 F2 类失败

定义
dominance_index = max(variable_weight) / total_weight

补充：

同时记录 top2_gap

若 top2_gap > 0.30 → dominance drift 预警

M2 — Variable Injection Rate
Purpose

检测 F3.1 / F5.2

定义
injection_rate = new_variables / total_variables

区间：

< 0.15 → starvation

0.45 → explosion

必须按 round 计算。

M3 — Semantic Repetition Score
Purpose

检测 F3.2 Recursive Looping

定义

计算：

当前 round questions

与上一轮 questions 的 embedding cosine similarity 平均值

repetition_score = mean(similarity)

阈值：

0.75 → looping risk

0.85 → CRITICAL

注意：
只比较相邻两轮，不做全历史。

M4 — Interrogative Density
Purpose

检测 F4 Soft Convergence Drift

定义
interrogative_density = question_count / total_sentences

如果低于 0.70：

说明开始向回答倾斜。

M5 — Structural Depth Stability
Purpose

检测 F3.3 Flattening

定义

记录：

depth_variance across rounds

如果：

depth 连续 2 轮下降

branching_factor < 2

→ flattening risk

4. 新增指标与 Failure 映射表
Failure	主要指标
F1 Entropy	entropy_score
F2 Dominance	dominance_index
F3.1 Freeze	injection_rate
F3.2 Looping	repetition_score
F3.3 Flattening	depth_stability
F4 Closure	interrogative_density
F5 Explosion	injection_rate

现在 Failure Taxonomy 可完全被检测。

5. 不做的指标（故意不加）

Phase 1 不加：

复杂图结构评分

长期语义网络一致性

全局 coherence score

自回归稳定度

原因：

Phase 1 是 Hardening，不是优化。

6. 实施优先顺序

必须按顺序实现：

dominance_index

injection_rate

repetition_score

interrogative_density

depth_stability

前三个优先。

7. 数据记录升级

日志结构必须扩展为：

{
  entropy_score,
  dominance_index,
  injection_rate,
  repetition_score,
  interrogative_density,
  branching_factor,
  depth_level,
  failure_code (optional)
}

否则统计无法进行。

8. 工程警告

不要：

调整阈值直到“测试通过”

在加指标同时改协议

一次性重构生成逻辑

Phase 1 是：

Instrument → Observe → Adjust Threshold

不是：

Redesign System
