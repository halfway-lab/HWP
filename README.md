# HWP (Half Way Protocol)

**HWP**（Half Way Protocol）是一个基于动态控制器的非收敛型认知生成协议。  
（简单说：这是一个让AI**不给出最终答案，而是不断提出新问题**的协议。）

通过 `RHYTHM_HINT` 引导生成进程，在多轮交互中动态调整输出的多样性与稳定性，让思考始终保持在“未完成”的探索状态。

---

## 项目理念

**我们相信，AI最大的价值不是提供答案，而是让思考得以延续。**

大多数AI工具都在追求“终结”——更快的总结、更精准的答案、更高效的完成任务。但我们发现，当思考被“总结”取代，当可能性被“答案”关闭，人也就停止了真正的展开。

***Half Way 是一个反潮流的尝试。***

它不是又一个“总结/答案工具”，而是一套关于 **“如何保持未完成”** 的思考协议。它不输出结论，只生成可继续的问题、提供多种理解路径、保留那些被主流工具抛弃的“未完成方向”。

我们不输出答案。我们只扩展可能性。

核心表达只有一句话：**在路上，可以慢，不要停。**

---

## 技术核心

HWP 协议的核心是 **动态控制器** 与 `RHYTHM_HINT` 机制。它通过以下方式实现“非收敛型生成”：

- **动态控制**：每轮生成后根据熵、漂移等变量实时调整，确保过程既稳定又富有探索性。
- **基于反馈的生成**：`RHYTHM_HINT` 携带上一轮的输出特征，引导下一轮生成的方向。
- **灵活的输入/输出**：支持 JSON、纯文本等多种格式，易于集成到不同应用场景中。

**v0.6 RC2 / 当前代码结构补充**：

- `runs/*.sh` 保留为 runner / verifier 入口与 orchestration 层
- `hwp_protocol/cli.py` 提供统一 Python CLI 入口
- `hwp_protocol/transform.py` 承担 v0.6 字段 materialization 与 inner/outer JSON repack
- `hwp_protocol/fixture_verify.py` 承担 fixture 规则校验
- `hwp_protocol/log_verify.py` 承担 JSONL 日志结构化验证
- shell 入口通过 `python3 -m hwp_protocol...` 调用协议核心模块，避免路径依赖
- `tests/test_protocol_core.py` 提供协议核心的最小单元测试覆盖

这意味着当前仓库已经从“Shell 承担大部分协议逻辑”逐步过渡为“Shell 负责入口，Python 负责协议核心”。

---

## 安装

确保你的环境中已安装 **Python 3.8+**、`pip`，以及可用的 `openclaw` CLI。

```bash
git clone https://github.com/halfway-lab/HWP.git
cd HWP
pip install -r requirements.txt
```

如 `openclaw` 不在默认 PATH 中，可在运行前指定：

```bash
export HWP_AGENT_BIN=/path/to/openclaw
```

如果当前环境没有 `openclaw`，也可以使用已有链日志做本地回放验收：

```bash
export HWP_REPLAY_CHAIN_PATH=logs/chain_hwp_1772451330_20939.jsonl
bash runs/run_sequential.sh inputs/probe.txt
```

---

## 快速体验
HWP 附带了两组测试输入，你可以立即体验协议的运行效果：
  ```bash
  # 运行 probe 测试（用于验证基础控制机制）
  bash runs/run_sequential.sh inputs/probe.txt

  # 运行 natural 测试（模拟自然语言输入）
  bash runs/run_sequential.sh inputs/natural.txt
  ```
运行后，生成的“未完成方向”会以 JSONL 格式保存在 logs/ 目录下（例如 chain_probe.jsonl）。

---

## 验证输出
如果你想确认本次运行是否符合 v0.6 RC2 的预期行为，可以运行统一验证脚本：
  ```bash
  bash runs/verify_v06_all.sh logs
  ```

如果你想直接使用统一 Python CLI，也可以：
  ```bash
  python3 -m hwp_protocol.cli fixture-verify blind_spot valid
  python3 -m hwp_protocol.cli log-verify continuity logs/chain_hwp_xxx.jsonl
  ```

如果你想单独检查某一维，也可以运行：
  ```bash
  bash runs/verify_v06_blind_spot.sh logs
  bash runs/verify_v06_continuity.sh logs
  bash runs/verify_v06_semantic_groups.sh logs
  ```
验证脚本会检查生成结果的结构、关键字段是否存在，以及与预期模式的匹配度。

---

**当前主页状态**：仓库当前主线为 **HWP v0.6 RC2**，聚焦 runner output materialization、replay 验收、以及 `hwp_protocol/` 协议核心收口。  
历史版本仍保留在 release notes 中，但主页说明与推荐命令已对齐当前 RC2 工作流。


---

## English Version

# HWP (Half Way Protocol)

**HWP** (Half Way Protocol) is a non-convergent cognitive generation protocol based on a dynamic controller.  
(In short: it's a protocol that enables AI to **keep asking new questions instead of providing final answers**.)

It uses `RHYTHM_HINT` to guide the generation process, dynamically adjusting the diversity and stability of outputs across multiple rounds of interaction, keeping thought in a perpetual state of "unfinished" exploration.

---

## Project Philosophy

**We believe that the greatest value of AI is not to provide answers, but to sustain thinking.**

Most AI tools pursue "finality" — faster summaries, more precise answers, more efficient task completion. But we've noticed that when thinking is replaced by "summaries" and possibilities are closed off by "answers", human exploration comes to a halt.

***Half Way is an attempt to go against this current.***

It is not another "summary/answer tool", but a thinking protocol about **"how to stay unfinished"**. It does not output conclusions; it only generates questions that can be continued, offers multiple paths of understanding, and preserves the "unfinished directions" discarded by mainstream tools.

We don't output answers. We only expand possibilities.

The core message is simple: **On the way, slow is fine, just don't stop.**

---

## Technical Core

The core of the HWP protocol is the **dynamic controller** and the `RHYTHM_HINT` mechanism. It achieves "non-convergent generation" through:

- **Dynamic Control**: Real-time adjustments based on entropy, drift, and other variables after each round, ensuring both stability and explorability.
- **Feedback-Based Generation**: `RHYTHM_HINT` carries characteristics from the previous output to guide the next generation.
- **Flexible I/O**: Supports multiple formats like JSON and plain text, making it easy to integrate into different application scenarios.

**v0.6 RC2 / Current code structure update**:

- `runs/*.sh` remains the runner and verifier entry layer
- `hwp_protocol/cli.py` provides a unified Python CLI entrypoint
- `hwp_protocol/transform.py` handles v0.6 field materialization and inner/outer JSON repacking
- `hwp_protocol/fixture_verify.py` handles fixture-level rule validation
- `hwp_protocol/log_verify.py` handles structured JSONL log verification
- shell entrypoints invoke protocol-core modules via `python3 -m hwp_protocol...`, avoiding fragile path assumptions
- `tests/test_protocol_core.py` provides a minimal unit-test layer for protocol-core behavior

This means the repository is now moving from "Shell carries most protocol logic" toward "Shell orchestrates, Python implements protocol core".

---

## Installation

Ensure your environment has **Python 3.8+** and `pip` installed.

```bash
git clone https://github.com/halfway-lab/HWP.git
cd HWP
pip install -r requirements.txt
```

## Quick Start
HWP comes with two sets of test inputs for you to immediately experience the protocol:

```bash
# Run probe test (to verify basic control mechanisms)
bash runs/run_sequential.sh inputs/probe.txt

# Run natural test (simulating natural language input)
bash runs/run_sequential.sh inputs/natural.txt
```
After running, the generated "unfinished directions" will be saved in the logs/ directory as JSONL files (e.g., chain_probe.jsonl).

If `openclaw` is not available in your PATH, set `HWP_AGENT_BIN` before running:

```bash
export HWP_AGENT_BIN=/path/to/openclaw
```

For local replay without a live provider, you can also set:

```bash
export HWP_REPLAY_CHAIN_PATH=logs/chain_hwp_1772451330_20939.jsonl
bash runs/run_sequential.sh inputs/probe.txt
```

## Output Verification
To confirm whether a run meets the expected behavior of v0.6 RC2, you can run the unified verification script:

```bash
bash runs/verify_v06_all.sh logs
```

If you want to use the unified Python CLI directly, you can also run:

```bash
python3 -m hwp_protocol.cli fixture-verify blind_spot valid
python3 -m hwp_protocol.cli log-verify continuity logs/chain_hwp_xxx.jsonl
```

To inspect each verification dimension separately:

```bash
bash runs/verify_v06_blind_spot.sh logs
bash runs/verify_v06_continuity.sh logs
bash runs/verify_v06_semantic_groups.sh logs
```
The verification scripts check the structure of generated results, the presence of key fields, and their alignment with expected patterns.

**Current homepage state**: the repository currently tracks **HWP v0.6 RC2**, focusing on runner output materialization, replay-based acceptance, and protocol-core consolidation under `hwp_protocol/`.  
Historical releases are still preserved in the release notes, but the homepage guidance and recommended commands now align with the RC2 workflow.
