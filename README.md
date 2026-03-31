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

但这并不意味着 HWP 永远拒绝总结。更准确地说，HWP 反对的是**过早终结**，而不是反对一切收束。

在协议运行阶段，HWP 负责持续展开，保留问题、分歧与多条理解路径；当某个具体应用场景需要结束时，上层应用完全可以对这段展开轨迹做后验分析、聚类、筛选与阶段性总结。换句话说，**HWP 负责生成过程的开放性，应用负责在合适时机进行有依据的收束**。

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

**兼容入口说明**：

- 推荐入口仍然是 `bash runs/run_sequential.sh ...` 和 `python3 -m hwp_protocol.cli ...`
- [hwp_cli.sh](/Users/mac/Documents/Halfway-Lab/protocol/HWP/hwp_cli.sh) 与 [hwp_server.py](/Users/mac/Documents/Halfway-Lab/protocol/HWP/hwp_server.py) 仅为 legacy compatibility 保留
- 这两个兼容入口默认以当前仓库根目录为基准；如需显式指定，可设置 `HWP_REPO_PATH=/absolute/path/to/HWP`
- 在真正发起 live 请求前，可先运行 `bash runs/run_sequential.sh --dry-run` 检查 provider 配置与适配器选择
- `python3 hwp_server.py` 现在还提供一个轻量只读 dashboard：
  - `GET /dashboard` 查看最新 benchmark / chain 状态
  - `GET /api/dashboard` 获取同一份 JSON 快照
  - `GET /api/chain/latest` 获取最新链的轮次数据
  - `GET /api/benchmark/latest` 获取最新 benchmark overview
  - `GET /api/multi-provider/latest` 获取最新 multi-provider overview

---

## 安装

确保你的环境中已安装 **Python 3.9+**、`pip`。

如果你想直接跑默认的 live provider 模式，还需要可用的 `openclaw` CLI；如果你想接别的模型，也可以通过自定义 agent 适配脚本接入，不再强制依赖 `openclaw`。

```bash
git clone https://github.com/halfway-lab/HWP.git
cd HWP
pip install -r requirements.txt
```

HWP 现在支持三种 provider 配置方式：

- **命令行参数**：适合临时切换、脚本化调用
- **环境变量**：适合开发者日常使用
- **配置文件**：适合普通用户长期保存配置

优先级如下：

```text
命令行参数 > 环境变量 > 配置文件 > 内置默认值
```

推荐优先使用 `HWP_PROVIDER_TYPE` / `HWP_PROVIDER_NAME`。这样用户不用记适配器文件路径，只需要声明自己在用哪类 provider。

支持的 provider type：

- `openclaw`
- `openai_compatible`
- `ollama`
- `custom`

如果你使用的是兼容 OpenAI API 的平台，通常只需要：

```dotenv
HWP_PROVIDER_TYPE=openai_compatible
HWP_PROVIDER_NAME=openrouter
HWP_LLM_API_KEY=your_api_key_here
HWP_LLM_MODEL=your_model_here
```

很多常见平台已经内置了默认 `base_url` 预设，用户不需要手动填写。

最快的配置方式是直接运行：

```bash
bash runs/setup_provider.sh
```

它会交互式帮你生成 `config/provider.env`，并在结束后提示下一步运行命令与检查项；你还可以选择立即跑一次 `probe` 测试。

如果你想在脚本或自动化里直接生成配置，也可以使用非交互模式：

```bash
bash runs/setup_provider.sh --non-interactive --provider deepseek --api-key YOUR_KEY --model YOUR_MODEL
```

如果你想只把配置内容打印到 stdout，而不直接写文件，也可以：

```bash
bash runs/setup_provider.sh --non-interactive --provider deepseek --api-key YOUR_KEY --model YOUR_MODEL --stdout > config/provider.env
```

### 平台速查

| 平台 | 推荐 provider type | 推荐 provider name | 直接复制的模板 | 你通常需要填写 |
| --- | --- | --- | --- | --- |
| OpenRouter | `openai_compatible` | `openrouter` | `cp config/provider.openrouter.env.example config/provider.env` | `HWP_LLM_API_KEY`、`HWP_LLM_MODEL` |
| DeepSeek | `openai_compatible` | `deepseek` | `cp config/provider.deepseek.env.example config/provider.env` | `HWP_LLM_API_KEY`、`HWP_LLM_MODEL` |
| Moonshot / Kimi | `openai_compatible` | `moonshot` | `cp config/provider.moonshot.env.example config/provider.env` | `HWP_LLM_API_KEY`、`HWP_LLM_MODEL` |
| SiliconFlow | `openai_compatible` | `siliconflow` | `cp config/provider.siliconflow.env.example config/provider.env` | `HWP_LLM_API_KEY`、`HWP_LLM_MODEL` |
| Groq | `openai_compatible` | `groq` | `cp config/provider.groq.env.example config/provider.env` | `HWP_LLM_API_KEY`、`HWP_LLM_MODEL` |
| Ollama | `ollama` | `ollama` | `cp config/provider.ollama.env.example config/provider.env` | `OLLAMA_MODEL` |
| OpenClaw | `openclaw` | `openclaw` | `cp config/provider.openclaw.env.example config/provider.env` | 可选 `HWP_AGENT_BIN` |
| 其他兼容 OpenAI API 的平台 | `openai_compatible` | `custom` | `cp config/provider.openai.env.example config/provider.env` | `HWP_LLM_API_KEY`、`HWP_LLM_MODEL`、`HWP_LLM_BASE_URL` |

如果你只想最快跑起来，优先从这张表里复制对应模板，然后只改必填字段。

也可以直接运行：

```bash
bash runs/setup_provider.sh
```

让脚本替你生成 `config/provider.env`，告诉你接下来怎么跑，并可立即试跑一次 `probe`。

如果你想在脚本里直接生成，也可以这样：

```bash
bash runs/setup_provider.sh --non-interactive --provider openrouter --api-key YOUR_KEY --model YOUR_MODEL
bash runs/setup_provider.sh --non-interactive --provider ollama --model llama3.1
bash runs/setup_provider.sh --non-interactive --provider openclaw
```

或者只输出配置文本：

```bash
bash runs/setup_provider.sh --non-interactive --provider custom --api-key YOUR_KEY --model YOUR_MODEL --base-url https://example.com/v1 --stdout
```

### 方式 1：命令行参数

推荐写法：

```bash
bash runs/run_sequential.sh --provider-type openai_compatible --provider-name openrouter inputs/probe.txt
bash runs/run_sequential.sh --provider-type ollama inputs/probe.txt
bash runs/run_sequential.sh --provider-type openclaw inputs/probe.txt
```

如果 provider name 有内置预设，通常不需要再手动指定 `--agent-cmd` 或 `HWP_LLM_BASE_URL`。

如 `openclaw` 不在默认 PATH 中，可在运行时指定：

```bash
bash runs/run_sequential.sh --agent-bin /path/to/openclaw inputs/probe.txt
```

如果你想改用别的模型，可以传入自定义 agent 命令：

```bash
bash runs/run_sequential.sh --agent-cmd '/path/to/your_adapter.sh' inputs/probe.txt
```

仓库也内置了两个现成适配器：

```bash
bash runs/run_sequential.sh --agent-cmd 'python3 adapters/openai_compatible_adapter.py' inputs/probe.txt
bash runs/run_sequential.sh --agent-cmd 'python3 adapters/ollama_adapter.py' inputs/probe.txt
```

如果你想使用 replay 模式：

```bash
bash runs/run_sequential.sh --replay-chain logs/chain_hwp_1772451330_20939.jsonl inputs/probe.txt
```

也可以通过 `--config` 指定其他配置文件：

```bash
bash runs/run_sequential.sh --config /path/to/provider.env inputs/probe.txt
```

### 方式 2：环境变量

如 `openclaw` 不在默认 PATH 中，可在运行前指定：

```bash
export HWP_AGENT_BIN=/path/to/openclaw
```

更推荐的环境变量写法是：

```bash
export HWP_PROVIDER_TYPE=openai_compatible
export HWP_PROVIDER_NAME=deepseek
```

或者：

```bash
export HWP_PROVIDER_TYPE=ollama
```

如果你想改用别的模型，可以提供一个自定义命令；runner 会把每轮 prompt 通过环境变量传给它：

```bash
export HWP_AGENT_CMD='/path/to/your_adapter.sh'
```

自定义适配器会收到这些环境变量：

- `HWP_AGENT_MESSAGE`: 当前轮完整 prompt
- `HWP_AGENT_SESSION_ID`: 当前链 session id
- `HWP_AGENT_ROUND`: 当前轮次

适配器需要把结果打印到 stdout，输出格式需兼容现有 runner：

```json
{
  "result": {
    "payloads": [
      {
        "text": "{\"node_id\":\"...\",\"round\":1,\"variables\":[],\"paths\":[],\"tensions\":[],\"unfinished\":[],\"entropy_score\":0.7,\"novelty_rate\":0.3,\"shared_variable_count\":0,\"drift_rate\":0.1,\"collapse_detected\":false,\"recovery_applied\":false}"
      }
    ]
  }
}
```

也可以直接输出不带 `result` 包装的同构 JSON，runner 会自动兼容 `.result // .`。

如果当前环境没有 `openclaw`，也可以使用已有链日志做本地回放验收：

```bash
export HWP_REPLAY_CHAIN_PATH=logs/chain_hwp_1772451330_20939.jsonl
bash runs/run_sequential.sh inputs/probe.txt
```

### 方式 3：配置文件

默认配置文件路径为：

```text
config/provider.env
```

仓库里附带了示例文件 [config/provider.env.example](/Users/mac/Documents/Halfway-Lab/protocol/HWP/config/provider.env.example)。你可以按它的格式创建 `config/provider.env`，例如：

```bash
cp config/provider.env.example config/provider.env
```

如果你不想手动编辑，也可以直接运行：

```bash
bash runs/setup_provider.sh
```

然后编辑成以下任意一种：

```dotenv
HWP_AGENT_BIN=/path/to/openclaw
```

```dotenv
HWP_AGENT_CMD=/absolute/path/to/your_adapter.sh
```

如果你想接兼容 OpenAI API 的任意平台，推荐这样写：

```dotenv
HWP_PROVIDER_TYPE=openai_compatible
HWP_PROVIDER_NAME=openrouter
HWP_LLM_API_KEY=your_api_key_here
HWP_LLM_MODEL=your_model_here
```

如果你使用的是内置预设之外的平台，再额外补一行：

```dotenv
HWP_LLM_BASE_URL=https://your-provider.example/v1
```

如果你想直接用仓库内置适配器，也可以复制现成模板：

```bash
cp config/provider.openai.env.example config/provider.env
```

或：

```bash
cp config/provider.openrouter.env.example config/provider.env
cp config/provider.deepseek.env.example config/provider.env
cp config/provider.moonshot.env.example config/provider.env
cp config/provider.siliconflow.env.example config/provider.env
cp config/provider.groq.env.example config/provider.env
```

或：

```bash
cp config/provider.ollama.env.example config/provider.env
```

或：

```bash
cp config/provider.openclaw.env.example config/provider.env
```

内置适配器文件：

- [adapters/openai_compatible_adapter.py](/Users/mac/Documents/Halfway-Lab/protocol/HWP/adapters/openai_compatible_adapter.py)
- [adapters/ollama_adapter.py](/Users/mac/Documents/Halfway-Lab/protocol/HWP/adapters/ollama_adapter.py)

现成 provider 配置模板：

- [config/provider.openrouter.env.example](/Users/mac/Documents/Halfway-Lab/protocol/HWP/config/provider.openrouter.env.example)
- [config/provider.deepseek.env.example](/Users/mac/Documents/Halfway-Lab/protocol/HWP/config/provider.deepseek.env.example)
- [config/provider.moonshot.env.example](/Users/mac/Documents/Halfway-Lab/protocol/HWP/config/provider.moonshot.env.example)
- [config/provider.siliconflow.env.example](/Users/mac/Documents/Halfway-Lab/protocol/HWP/config/provider.siliconflow.env.example)
- [config/provider.groq.env.example](/Users/mac/Documents/Halfway-Lab/protocol/HWP/config/provider.groq.env.example)
- [config/provider.ollama.env.example](/Users/mac/Documents/Halfway-Lab/protocol/HWP/config/provider.ollama.env.example)
- [config/provider.openclaw.env.example](/Users/mac/Documents/Halfway-Lab/protocol/HWP/config/provider.openclaw.env.example)

```dotenv
HWP_REPLAY_CHAIN_PATH=logs/chain_hwp_1772451330_20939.jsonl
```

配置好后，直接运行：

```bash
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

### 内置适配器快速配置

如果你想直接接任意兼容 OpenAI API 的大模型平台：

```bash
cp config/provider.openai.env.example config/provider.env
```

如果你已经知道自己要用哪个平台，也可以直接复制对应模板：

```bash
cp config/provider.openrouter.env.example config/provider.env
cp config/provider.deepseek.env.example config/provider.env
cp config/provider.moonshot.env.example config/provider.env
cp config/provider.siliconflow.env.example config/provider.env
cp config/provider.groq.env.example config/provider.env
```

然后把 `config/provider.env` 里的 `HWP_LLM_API_KEY`、`HWP_LLM_MODEL` 改成你的值；如果不是 OpenAI 官方地址，再额外设置 `HWP_LLM_BASE_URL`：

```bash
bash runs/run_sequential.sh inputs/probe.txt
```

这意味着你不只是能填 OpenAI 的 API key，也可以填任何兼容 OpenAI Chat Completions 接口的平台 key，只要该平台支持：

- `base_url`
- `api_key`
- `model`

例如常见的聚合平台、代理网关或自建兼容服务都可以走这一条。

常见可映射到 `openai_compatible` 的 provider name 示例：

- `openrouter`
- `deepseek`
- `moonshot`
- `kimi`
- `siliconflow`
- `groq`
- `together`
- `fireworks`
- `perplexity`
- `xai`
- `custom`

其中前面的常见平台已经内置默认 `base_url`；只有 `custom` 这类非预设平台，才需要你自己填写 `HWP_LLM_BASE_URL`。

如果你想直接接本地 Ollama：

```bash
cp config/provider.ollama.env.example config/provider.env
```

然后把 `OLLAMA_MODEL` 改成你本地已有模型名，再运行：

```bash
bash runs/run_sequential.sh inputs/probe.txt
```

### Legacy 兼容入口

如果旧脚本或本地工具仍然调用仓库根目录下的 helper，可以继续使用：

```bash
bash hwp_cli.sh "your input text"
python3 hwp_server.py --host 127.0.0.1 --port 8088
```

`hwp_cli.sh` 会执行标准 `runs/run_sequential.sh` runner，再输出最新链路最后一轮的 inner JSON。  
`hwp_server.py` 提供一个最小 HTTP `/run` 包装层，POST `{"text":"..."}` 后返回最后一轮 inner JSON。

如仓库不在当前目录，可先设置：

```bash
export HWP_REPO_PATH=/absolute/path/to/HWP
```

---

## 验证输出
如果你想确认本次运行是否符合 v0.6 RC2 的预期行为，可以运行统一验证脚本：
  ```bash
  bash runs/verify_v06_all.sh logs
  ```

如果你想在真正发起 live 请求前先检查 provider 配置是否解析正确，可以运行：

```bash
bash runs/run_sequential.sh --dry-run
```

如果你想限制单条链的最长运行时间，可以设置：

```bash
HWP_CHAIN_TIMEOUT_SEC=180 bash runs/run_sequential.sh inputs/probe.txt
```

## Benchmark 自动化
如果你想用固定输入集批量跑 benchmark，可以直接运行：

```bash
bash runs/run_benchmarks.sh
```

默认会读取 [benchmark_inputs.txt](/Users/mac/Documents/Halfway-Lab/protocol/HWP/config/benchmark_inputs.txt)，并把结果输出到：

```text
reports/benchmarks/<timestamp>/
```

每次运行会生成：

- `results.tsv`
- `summary.md`
- `overview.md`
- 每个 benchmark 的独立运行日志与 verifier 输出

其中 `overview.md` 会把 benchmark 结果、verifier 结论，以及从 `logs/run.log` 采集到的链级 timing summary 合并到一张总览表里。

单链运行时，`logs/run.log` 现在还会附带：

- 每轮 `round_sec` / `chain_sec`
- 每条链的 `[summary] session_id=... round_avg_sec=... round_max_sec=... chain_sec=...`

如果你想把最近若干条链的 timing 摘要整理成 Markdown，可以运行：

```bash
python3 runs/report_timing.py logs/run.log reports/timing_summary.md 10
```

如果你想在 replay 模式下快速验证整套 benchmark 流程，可以这样运行：

```bash
HWP_REPLAY_CHAIN_PATH=logs/chain_hwp_1772451330_20939.jsonl HWP_ROUND_SLEEP_SEC=0 bash runs/run_benchmarks.sh
```

如果你想横向比较多个 provider，可以运行：

```bash
bash runs/run_benchmarks_multi_provider.sh config/providers.list config/benchmark_inputs.live_subset.txt
```

multi-provider 报告现在会优先读取每个 provider 的 `overview.tsv`，因此不仅能比较 run/verifier 结果，也能汇总链级 timing。

如果你想快速用浏览器看最新状态，也可以启动 legacy dashboard：

```bash
python3 hwp_server.py --host 127.0.0.1 --port 8088
```

然后访问：

```text
http://127.0.0.1:8088/dashboard
```

页面现在支持直接切换指定资源，例如：

```text
http://127.0.0.1:8088/dashboard?chain=chain_hwp_xxx.jsonl&report=20260331T141118&multi_report=multi_20260331T141500
```

如果你想直接消费结构化数据，也可以访问：

```text
http://127.0.0.1:8088/api
http://127.0.0.1:8088/api/dashboard
http://127.0.0.1:8088/api/chain/latest
http://127.0.0.1:8088/api/benchmark/latest
http://127.0.0.1:8088/api/multi-provider/latest
```

其中几个接口支持最小查询参数：

```text
/api/chain/latest?path=logs/chain_hwp_xxx.jsonl
/api/benchmark/latest?report=20260331T141118
/api/multi-provider/latest?report=multi_20260331T141500
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

But that does not mean HWP must reject summarization forever. More precisely, HWP rejects **premature closure**, not all forms of closure.

During protocol execution, HWP is responsible for keeping the process open, preserving questions, divergences, and multiple interpretive paths. When a real application needs to conclude, the application layer can still perform retrospective analysis, clustering, filtering, and stage-level summarization over the expansion trace. In other words, **HWP keeps the generation process open, while the application layer may responsibly close it when the time is right**.

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

Ensure your environment has **Python 3.9+** and `pip` installed.

```bash
git clone https://github.com/halfway-lab/HWP.git
cd HWP
pip install -r requirements.txt
```

HWP now supports three provider configuration modes:

- command-line flags
- environment variables
- config file

Priority order:

```text
CLI args > environment variables > config file > built-in defaults
```

Recommended approach: set `HWP_PROVIDER_TYPE` and optionally `HWP_PROVIDER_NAME`, so users do not need to remember adapter file paths.

Supported provider types:

- `openclaw`
- `openai_compatible`
- `ollama`
- `custom`

For OpenAI-compatible providers, the common happy path is:

```dotenv
HWP_PROVIDER_TYPE=openai_compatible
HWP_PROVIDER_NAME=openrouter
HWP_LLM_API_KEY=your_api_key_here
HWP_LLM_MODEL=your_model_here
```

For many common providers, HWP already supplies a default `base_url` preset.

The fastest setup path is:

```bash
bash runs/setup_provider.sh
```

This will generate `config/provider.env` interactively, print the next command plus a short checklist, and optionally run a `probe` test immediately.

For scripts and CI, you can also use non-interactive mode:

```bash
bash runs/setup_provider.sh --non-interactive --provider deepseek --api-key YOUR_KEY --model YOUR_MODEL
```

If you only want the generated config on stdout instead of writing a file:

```bash
bash runs/setup_provider.sh --non-interactive --provider deepseek --api-key YOUR_KEY --model YOUR_MODEL --stdout > config/provider.env
```

### Provider Quick Reference

| Provider | Recommended type | Recommended name | Template to copy | Usually fill in |
| --- | --- | --- | --- | --- |
| OpenRouter | `openai_compatible` | `openrouter` | `cp config/provider.openrouter.env.example config/provider.env` | `HWP_LLM_API_KEY`, `HWP_LLM_MODEL` |
| DeepSeek | `openai_compatible` | `deepseek` | `cp config/provider.deepseek.env.example config/provider.env` | `HWP_LLM_API_KEY`, `HWP_LLM_MODEL` |
| Moonshot / Kimi | `openai_compatible` | `moonshot` | `cp config/provider.moonshot.env.example config/provider.env` | `HWP_LLM_API_KEY`, `HWP_LLM_MODEL` |
| SiliconFlow | `openai_compatible` | `siliconflow` | `cp config/provider.siliconflow.env.example config/provider.env` | `HWP_LLM_API_KEY`, `HWP_LLM_MODEL` |
| Groq | `openai_compatible` | `groq` | `cp config/provider.groq.env.example config/provider.env` | `HWP_LLM_API_KEY`, `HWP_LLM_MODEL` |
| Ollama | `ollama` | `ollama` | `cp config/provider.ollama.env.example config/provider.env` | `OLLAMA_MODEL` |
| OpenClaw | `openclaw` | `openclaw` | `cp config/provider.openclaw.env.example config/provider.env` | optional `HWP_AGENT_BIN` |
| Other OpenAI-compatible providers | `openai_compatible` | `custom` | `cp config/provider.openai.env.example config/provider.env` | `HWP_LLM_API_KEY`, `HWP_LLM_MODEL`, `HWP_LLM_BASE_URL` |

If you want the fastest path, copy the matching template from this table and edit only the required fields.

You can also run:

```bash
bash runs/setup_provider.sh
```

to generate `config/provider.env` for you, print the next recommended steps, and optionally run a `probe` test.

For automation, you can also do:

```bash
bash runs/setup_provider.sh --non-interactive --provider openrouter --api-key YOUR_KEY --model YOUR_MODEL
bash runs/setup_provider.sh --non-interactive --provider ollama --model llama3.1
bash runs/setup_provider.sh --non-interactive --provider openclaw
```

Or print config text only:

```bash
bash runs/setup_provider.sh --non-interactive --provider custom --api-key YOUR_KEY --model YOUR_MODEL --base-url https://example.com/v1 --stdout
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

### Mode 1: CLI args

Recommended examples:

```bash
bash runs/run_sequential.sh --provider-type openai_compatible --provider-name openrouter inputs/probe.txt
bash runs/run_sequential.sh --provider-type ollama inputs/probe.txt
bash runs/run_sequential.sh --provider-type openclaw inputs/probe.txt
```

If the provider name has a built-in preset, you usually do not need to set `--agent-cmd` or `HWP_LLM_BASE_URL`.

If `openclaw` is not available in your PATH:

```bash
bash runs/run_sequential.sh --agent-bin /path/to/openclaw inputs/probe.txt
```

If you want to use another model instead of OpenClaw:

```bash
bash runs/run_sequential.sh --agent-cmd '/path/to/your_adapter.sh' inputs/probe.txt
```

The repository also includes two ready-made adapters:

```bash
bash runs/run_sequential.sh --agent-cmd 'python3 adapters/openai_compatible_adapter.py' inputs/probe.txt
bash runs/run_sequential.sh --agent-cmd 'python3 adapters/ollama_adapter.py' inputs/probe.txt
```

If you want replay mode:

```bash
bash runs/run_sequential.sh --replay-chain logs/chain_hwp_1772451330_20939.jsonl inputs/probe.txt
```

If you want to point to a specific config file:

```bash
bash runs/run_sequential.sh --config /path/to/provider.env inputs/probe.txt
```

### Mode 2: Environment variables

If `openclaw` is not available in your PATH, set `HWP_AGENT_BIN` before running:

```bash
export HWP_AGENT_BIN=/path/to/openclaw
```

The preferred environment-variable style is:

```bash
export HWP_PROVIDER_TYPE=openai_compatible
export HWP_PROVIDER_NAME=deepseek
```

If you want to use another model instead of OpenClaw, you can provide a custom adapter command:

```bash
export HWP_AGENT_CMD='/path/to/your_adapter.sh'
```

The runner will pass the full round prompt through environment variables:

- `HWP_AGENT_MESSAGE`
- `HWP_AGENT_SESSION_ID`
- `HWP_AGENT_ROUND`

Your adapter should print JSON to stdout in the existing runner-compatible shape:

```json
{
  "result": {
    "payloads": [
      {
        "text": "{\"node_id\":\"...\",\"round\":1,\"variables\":[],\"paths\":[],\"tensions\":[],\"unfinished\":[],\"entropy_score\":0.7,\"novelty_rate\":0.3,\"shared_variable_count\":0,\"drift_rate\":0.1,\"collapse_detected\":false,\"recovery_applied\":false}"
      }
    ]
  }
}
```

For local replay without a live provider, you can also set:

```bash
export HWP_REPLAY_CHAIN_PATH=logs/chain_hwp_1772451330_20939.jsonl
bash runs/run_sequential.sh inputs/probe.txt
```

### Mode 3: Config file

Default config path:

```text
config/provider.env
```

An example is included at [config/provider.env.example](/Users/mac/Documents/Halfway-Lab/protocol/HWP/config/provider.env.example). Create your own config file from it:

```bash
cp config/provider.env.example config/provider.env
```

Then set one of:

```dotenv
HWP_AGENT_BIN=/path/to/openclaw
```

```dotenv
HWP_AGENT_CMD=/absolute/path/to/your_adapter.sh
```

Or copy one of the ready-made examples:

```bash
cp config/provider.openai.env.example config/provider.env
```

```bash
cp config/provider.openrouter.env.example config/provider.env
cp config/provider.deepseek.env.example config/provider.env
cp config/provider.moonshot.env.example config/provider.env
cp config/provider.siliconflow.env.example config/provider.env
cp config/provider.groq.env.example config/provider.env
```

```bash
cp config/provider.ollama.env.example config/provider.env
```

```bash
cp config/provider.openclaw.env.example config/provider.env
```

Built-in adapter files:

- [adapters/openai_compatible_adapter.py](/Users/mac/Documents/Halfway-Lab/protocol/HWP/adapters/openai_compatible_adapter.py)
- [adapters/ollama_adapter.py](/Users/mac/Documents/Halfway-Lab/protocol/HWP/adapters/ollama_adapter.py)

Ready-made provider config templates:

- [config/provider.openrouter.env.example](/Users/mac/Documents/Halfway-Lab/protocol/HWP/config/provider.openrouter.env.example)
- [config/provider.deepseek.env.example](/Users/mac/Documents/Halfway-Lab/protocol/HWP/config/provider.deepseek.env.example)
- [config/provider.moonshot.env.example](/Users/mac/Documents/Halfway-Lab/protocol/HWP/config/provider.moonshot.env.example)
- [config/provider.siliconflow.env.example](/Users/mac/Documents/Halfway-Lab/protocol/HWP/config/provider.siliconflow.env.example)
- [config/provider.groq.env.example](/Users/mac/Documents/Halfway-Lab/protocol/HWP/config/provider.groq.env.example)
- [config/provider.ollama.env.example](/Users/mac/Documents/Halfway-Lab/protocol/HWP/config/provider.ollama.env.example)
- [config/provider.openclaw.env.example](/Users/mac/Documents/Halfway-Lab/protocol/HWP/config/provider.openclaw.env.example)

For the OpenAI-compatible adapter, the preferred generic variables are:

```dotenv
HWP_LLM_API_KEY=your_api_key_here
HWP_LLM_MODEL=your_model_here
HWP_LLM_BASE_URL=https://your-provider.example/v1
```

This is not limited to OpenAI. Any provider that exposes an OpenAI-compatible Chat Completions endpoint can be used. Legacy `OPENAI_*` variable names are still supported for backward compatibility.

Common provider-name examples that can map to `openai_compatible`:

- `openrouter`
- `deepseek`
- `moonshot`
- `kimi`
- `siliconflow`
- `groq`
- `together`
- `fireworks`
- `perplexity`
- `xai`
- `custom`

The common preset names above already have default `base_url` mappings built in. For non-preset providers such as `custom`, set `HWP_LLM_BASE_URL` explicitly.

```dotenv
HWP_REPLAY_CHAIN_PATH=logs/chain_hwp_1772451330_20939.jsonl
```

## Output Verification
To confirm whether a run meets the expected behavior of v0.6 RC2, you can run the unified verification script:

```bash
bash runs/verify_v06_all.sh logs
```

## Benchmark Automation
To run the fixed benchmark set in batch, use:

```bash
bash runs/run_benchmarks.sh
```

By default it reads [benchmark_inputs.txt](/Users/mac/Documents/Halfway-Lab/protocol/HWP/config/benchmark_inputs.txt) and writes results under:

```text
reports/benchmarks/<timestamp>/
```

Each run generates:

- `results.tsv`
- `summary.md`
- per-benchmark run logs and verifier outputs

To validate the whole benchmark flow quickly in replay mode:

```bash
HWP_REPLAY_CHAIN_PATH=logs/chain_hwp_1772451330_20939.jsonl HWP_ROUND_SLEEP_SEC=0 bash runs/run_benchmarks.sh
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
