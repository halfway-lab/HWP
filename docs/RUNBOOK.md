# HWP Runbook

## Install

```bash
pip install -r requirements.txt
```

## Configure Provider

Recommended:

```bash
bash runs/setup_provider.sh
```

Or generate config non-interactively:

```bash
bash runs/setup_provider.sh --non-interactive --provider deepseek --api-key YOUR_KEY --model YOUR_MODEL
```

## Run a Single Chain

```bash
bash runs/run_sequential.sh inputs/probe.txt
HWP_CHAIN_TIMEOUT_SEC=180 bash runs/run_sequential.sh inputs/probe.txt
```

## Open The Lightweight Dashboard

```bash
python3 hwp_server.py --host 127.0.0.1 --port 8088
```

Then open:

```text
http://127.0.0.1:8088/dashboard
```

You can also point the page at a specific chain / report:

```text
http://127.0.0.1:8088/dashboard?chain=chain_hwp_xxx.jsonl&report=20260331T141118&multi_report=multi_20260331T141500
```

JSON snapshot:

```text
http://127.0.0.1:8088/api/dashboard
```

Other JSON endpoints:

```text
http://127.0.0.1:8088/api
http://127.0.0.1:8088/api/chain/latest
http://127.0.0.1:8088/api/benchmark/latest
http://127.0.0.1:8088/api/multi-provider/latest
```

Optional query params:

```text
/api/chain/latest?path=logs/chain_hwp_xxx.jsonl
/api/benchmark/latest?report=20260331T141118
/api/multi-provider/latest?report=multi_20260331T141500
```

## Validate Provider Setup Without Network

```bash
bash runs/run_sequential.sh --dry-run
bash runs/run_sequential.sh --dry-run --config /path/to/provider.env
```

## Run Replay Benchmark Baseline

```bash
HWP_REPLAY_CHAIN_PATH=logs/chain_hwp_1772451330_20939.jsonl HWP_ROUND_SLEEP_SEC=0 bash runs/run_benchmarks.sh
```

## Run Live Benchmarks

```bash
HWP_ROUND_SLEEP_SEC=0 bash runs/run_benchmarks.sh
```

## Run Multi-Provider Benchmarks

```bash
bash runs/run_benchmarks_multi_provider.sh config/providers.list config/benchmark_inputs.live_subset.txt
```

输出目录会包含 `comparison.md` 与 `failures.md`，并优先基于各 provider 的 `overview.tsv` 生成横向对比。

## Read Benchmark Overview

每次 benchmark 运行后，可直接查看：

```bash
sed -n '1,120p' reports/benchmarks/<timestamp>/overview.md
```

## Run Unified v0.6 Verification

```bash
bash runs/verify_v06_all.sh <logs_dir>
```

## Common Outputs

- Logs:
  - `logs/`
- Benchmark reports:
  - `reports/benchmarks/<timestamp>/`

## Summarize Recent Chain Timing

```bash
python3 runs/report_timing.py logs/run.log reports/timing_summary.md 10
```

## Local-Only Sensitive Files

- `config/provider.env`

Do not commit live secrets or local provider credentials.
