# HWP Stability Status

Last updated: 2026-03-31

## Current Status

HWP is currently in a "stable for mainline development" state.

The protocol/runtime path is functioning end to end:

- Python-side protocol materialization is enforcing key defaults
- fixture and log verification are aligned with current protocol behavior
- replay execution is stable
- live provider execution has been verified on the real adapter + runner path
- runner observability now includes dry-run validation, chain timeout, per-round timing, and per-chain timing summaries

## What Is Stable

- Protocol field normalization in `hwp_protocol/transform.py`
- Continuity / blind spot / semantic-group verification flow
- Replay runner execution through `runs/run_sequential.sh`
- Legacy compatibility entrypoints:
  - `hwp_server.py`
  - `hwp_cli.sh`
- Provider preflight validation via:
  - `bash runs/run_sequential.sh --dry-run`
- Timing visibility via:
  - `logs/run.log`
  - `python3 runs/report_timing.py logs/run.log reports/timing_summary.md 10`

## What Still Needs Observation

- Live provider latency in later rounds of longer chains
- Provider-to-provider stability differences
- Higher-concurrency execution behavior

These are currently performance/stability observation items, not known protocol-correctness failures.

## Recommended Default Workflow

1. Validate config before live calls:

```bash
bash runs/run_sequential.sh --dry-run
```

2. Use replay for quick regression checks:

```bash
HWP_ROUND_SLEEP_SEC=0 bash runs/run_sequential.sh --replay-chain logs/chain_hwp_1774895962_11688.jsonl inputs/probe.txt
```

3. Use a chain timeout for live smoke runs:

```bash
HWP_CHAIN_TIMEOUT_SEC=180 HWP_ROUND_SLEEP_SEC=0 bash runs/run_sequential.sh inputs/probe.txt
```

4. Summarize recent timing data:

```bash
python3 runs/report_timing.py logs/run.log reports/timing_summary.md 10
```

## Validation Snapshot

Current local validation baseline:

- `python3 -m unittest` passes
- replay runner path passes
- live provider smoke path has been exercised successfully
- verifier checks pass on generated logs for:
  - blind spot
  - continuity
  - semantic groups

## Operational Read

If the question is whether this version can be used as the current working mainline, the answer is yes.

If the question is whether all live-runtime risk has been eliminated, the answer is no. The main remaining risk is long-chain live latency rather than protocol correctness.
