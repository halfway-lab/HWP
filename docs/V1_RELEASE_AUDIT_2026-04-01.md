# HWP v1.0 Release Audit

Audit date: 2026-04-01

## Scope

This audit records the first release-oriented validation pass executed after the
`v1.0` release plan was added to the repository.

It focuses on:

- unit test baseline
- replay benchmark baseline
- multi-provider smoke behavior
- release-critical failures discovered during the audit
- fixes applied before closing the audit pass

## Validation Matrix

### 1. Unit Test Baseline

Command:

```bash
python3 -m unittest
```

Result:

- PASS
- `Ran 66 tests`

Conclusion:

- current protocol-core, runner, benchmark, dashboard, and contract tests passed on main

### 2. Replay Benchmark Baseline

Command:

```bash
HWP_REPLAY_CHAIN_PATH=logs/chain_hwp_1772451330_20939.jsonl \
HWP_ROUND_SLEEP_SEC=0 \
bash runs/run_benchmarks.sh config/benchmark_inputs.live_subset.txt
```

Result:

- PASS after report-path hardening fix
- report directory:
  - `reports/benchmarks/20260401T113330__47762`

Observed benchmark results:

- `probe`: pass
- `natural`: pass
- `mixed`: pass

Reference artifacts:

- `reports/benchmarks/20260401T113330__47762/results.tsv`
- `reports/benchmarks/20260401T113330__47762/summary.md`
- `reports/benchmarks/20260401T113330__47762/overview.md`
- `reports/benchmarks/20260401T113330__47762/regression.md`

### 3. Multi-Provider Smoke

Command:

```bash
HWP_REPLAY_CHAIN_PATH=logs/chain_hwp_1772451330_20939.jsonl \
HWP_ROUND_SLEEP_SEC=0 \
bash runs/run_benchmarks_multi_provider.sh \
  config/providers.list \
  config/benchmark_inputs.live_subset.txt
```

Result:

- PASS after report-path hardening fix
- report directory:
  - `reports/benchmarks/multi_20260401T113331__47798`

Observed provider execution status:

- `openclaw`: completed
- `openrouter`: skipped_placeholder
- `deepseek`: skipped_placeholder
- `groq`: skipped_placeholder
- `ollama`: skipped_placeholder
- `moonshot`: skipped_placeholder
- `siliconflow`: skipped_placeholder

Reference artifacts:

- `reports/benchmarks/multi_20260401T113331__47798/provider_status.tsv`
- `reports/benchmarks/multi_20260401T113331__47798/comparison.md`
- `reports/benchmarks/multi_20260401T113331__47798/failures.md`

## Release-Critical Issue Found During Audit

The first audit attempt exposed a release-critical issue:

- benchmark and multi-provider runs could collide on the same second-based
  report directory name

Symptoms observed before the fix:

- duplicate rows in `results.tsv`
- false `structured=fail` summaries even when the verifier log itself passed
- false multi-provider `openclaw failed` results
- file-copy failures when one run guessed the other run's latest report directory

Root cause:

- report directories were only keyed by second-resolution timestamps
- multi-provider report collection relied on "latest report dir" guessing

## Fix Applied

The audit issue was fixed in:

- commit `ba57ee9`
- message: `harden benchmark report paths for release validation`

What changed:

- benchmark report directories now use `<timestamp>__<pid>`
- multi-provider report directories now use `multi_<timestamp>__<pid>`
- multi-provider collection reads the actual report dir from benchmark output
- regression baseline lookup now supports PID-suffixed report directories
- chain-log copy handling is more defensive under concurrent runs

## Current Audit Read

As of this audit pass:

- the release-validation baseline is usable
- replay benchmark validation is green
- multi-provider smoke is green for the currently configured real provider path
- placeholder provider configs are now represented explicitly as skipped, not as false failures

## Remaining Gaps Before v1.0

- add or verify a second real-provider smoke path if feasible
- perform one more release audit pass closer to release candidate freeze
- prepare `v1.0 RC1` release notes based on this validation baseline

## Recommendation

The next best step is:

- use this audit as the baseline record for a `v1.0 RC1` pre-release note draft
