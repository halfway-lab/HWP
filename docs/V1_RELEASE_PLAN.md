# HWP v1.0 Release Plan

Last updated: 2026-03-31

## Goal

Ship **HWP v1.0** on **2026-04-20**.

This release should mark the point where HWP is no longer just a stable RC2
protocol-core line, but a releaseable protocol platform with:

- stable protocol materialization
- stable verifier and benchmark workflows
- usable benchmark and dashboard outputs
- documented machine-facing contracts
- a clear release checklist and validation baseline

## Current Starting Point

Current mainline status is still:

- **HWP v0.6 RC2**

Already true on the current main branch:

- protocol transform/materialization is in Python-side core modules
- fixture/log verification is aligned with current RC2 behavior
- replay and live single-provider paths are working
- benchmark overview and multi-provider overview exist
- lightweight dashboard and JSON API exist
- benchmark/dashboard data contracts are documented
- package ownership has been separated out of this protocol repo

## v1.0 Release Definition

`v1.0` does **not** mean every future protocol idea is finished.

For this repository, `v1.0` should mean:

1. the main workflow is stable and documented
2. key machine-facing outputs are treated as intentional contracts
3. release validation is repeatable
4. known residual risks are named and bounded
5. downstream consumers can integrate without guessing hidden behavior

## Release Criteria

All of the following should be true before cutting `v1.0`.

### 1. Version And Documentation Consistency

- README, PROJECT_STATUS, RUNBOOK, STABILITY_STATUS, DATA_CONTRACTS, and RELEASE_NOTES agree on current release state
- no high-traffic document still describes package ownership as living inside this protocol repo
- `v1.0` release notes exist before the final cut

### 2. Protocol And Runner Stability

- no known contradictions remain between protocol rules, transform output, and verifier expectations
- runner behavior for replay, dry-run, timeout, and timing summary is stable
- no known shell/platform blocker remains on default supported developer setups

### 3. Benchmark And Dashboard Stability

- `run_benchmarks.sh` consistently produces:
  - `results.tsv`
  - `summary.md`
  - `overview.md`
  - `overview.tsv`
- `run_benchmarks_multi_provider.sh` clearly distinguishes:
  - completed providers
  - skipped placeholder providers
  - failed providers
- dashboard routes and API routes work against current artifacts without schema ambiguity

### 4. Data Contract Stability

- fields documented in `docs/DATA_CONTRACTS.md` are treated as stable for the release
- any remaining schema changes before release must update code, docs, and tests in the same change

### 5. Validation Baseline

- `python3 -m unittest` passes on main
- replay benchmark baseline passes
- at least one real configured provider passes a multi-provider smoke run
- dashboard/API smoke validation passes against generated artifacts

### 6. Residual Risk Handling

- live long-chain latency is documented as an operational risk if it is still present
- default smoke guidance is documented clearly enough for release users

## Non-Goals For v1.0

The following are explicitly not required to ship `v1.0`:

- solving every live provider latency issue in all environments
- supporting every possible provider with real credentials in this repo
- a production-grade frontend application beyond the lightweight dashboard
- major protocol redesign beyond the current RC2-era structure

## Timeline

## Phase 1: Release Alignment
**Target**: 2026-04-01 to 2026-04-05

Objective:

- stop version drift
- align docs and release framing

Required outcomes:

- create and keep this release plan up to date
- audit README, PROJECT_STATUS, RUNBOOK, STABILITY_STATUS, DATA_CONTRACTS, RELEASE_NOTES
- remove or rewrite remaining high-impact wording that conflicts with current repository boundaries
- define release criteria and validate them with current branch state

Exit condition:

- release framing is coherent and no obvious documentation contradiction remains in high-traffic docs

## Phase 2: Validation Hardening
**Target**: 2026-04-06 to 2026-04-10

Objective:

- harden the release validation story

Required outcomes:

- run replay benchmark validation on current mainline
- run multi-provider smoke on the currently configured real provider plus placeholder-skipped configs
- if feasible, add a second real-provider smoke path
- ensure benchmark and dashboard outputs are still aligned with `DATA_CONTRACTS.md`
- document the default smoke workflow for release users

Exit condition:

- the repo has a repeatable release-validation baseline, not just a locally remembered one

## Phase 3: Release Candidate Freeze
**Target**: 2026-04-11 to 2026-04-15

Objective:

- stop feature expansion and enter release-candidate mode

Required outcomes:

- new work is limited to bugfixes, doc fixes, and release blockers
- run full test baseline
- run benchmark/dashboard smoke baseline
- draft `v1.0` release notes
- list all known residual risks explicitly

Exit condition:

- branch is effectively in `v1.0 RC` condition

## Phase 4: Final Release Prep
**Target**: 2026-04-16 to 2026-04-19

Objective:

- prepare the final release artifact and final verification

Required outcomes:

- final release notes reviewed
- release checklist reviewed
- branch clean and synced
- final smoke and test run completed
- release tag and release message prepared

Exit condition:

- only release-day execution remains

## Release Day
**Target**: 2026-04-20

Objective:

- publish `v1.0`

Required outcomes:

- release notes published
- release tag created
- current mainline state clearly described as `v1.0`
- release validation record preserved in docs or release notes

## Release Checklist

### Branch And Repository

- main is clean and synced
- no unintended local-only files remain in the release scope
- release notes reflect actual shipped behavior

### Tests And Validation

- `python3 -m unittest`
- replay benchmark smoke
- multi-provider smoke
- dashboard/API smoke

### Documentation

- README reviewed
- RUNBOOK reviewed
- PROJECT_STATUS reviewed
- STABILITY_STATUS reviewed
- DATA_CONTRACTS reviewed
- RELEASE_NOTES reviewed

### Operational Readiness

- default provider setup flow is documented
- timeout and smoke guidance are documented
- residual risks are explicitly called out

## Known Risks To Watch Before v1.0

- long live-chain latency in later rounds
- uneven real-provider coverage across multi-provider smoke
- potential future schema drift between docs and implementation if contracts change quickly

## Recommended Immediate Next Step

The next highest-value step is:

- perform one release-oriented audit pass against:
  - `README.md`
  - `docs/PROJECT_STATUS.md`
  - `docs/RUNBOOK.md`
  - `docs/STABILITY_STATUS.md`
  - `docs/DATA_CONTRACTS.md`
  - `docs/RELEASE_NOTES.md`

The goal of that pass is not new functionality. It is to ensure the repository
is telling one coherent story before the release candidate phase begins.
