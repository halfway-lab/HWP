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
```

## Run Replay Benchmark Baseline

```bash
HWP_REPLAY_CHAIN_PATH=logs/chain_hwp_1772451330_20939.jsonl HWP_ROUND_SLEEP_SEC=0 bash runs/run_benchmarks.sh
```

## Run Live Benchmarks

```bash
HWP_ROUND_SLEEP_SEC=0 bash runs/run_benchmarks.sh
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

## Local-Only Sensitive Files

- `config/provider.env`

Do not commit live secrets or local provider credentials.
