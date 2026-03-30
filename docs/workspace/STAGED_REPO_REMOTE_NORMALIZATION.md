# Staged Repo Remote Normalization

## Goal

Record the remote normalization status of staged repos inside `Halfway-Lab` now that daily work has cut over.

## Current Findings

### Canonical Protocol Repo

Current staged canonical repo:

- `/Users/mac/Documents/Halfway-Lab/protocol/HWP`

Current `origin`:

- `git@github.com:halfway-lab/HWP.git`

Meaning:

- the new canonical working repo now points directly to the canonical GitHub remote
- remote normalization for the staged protocol repo is complete
- the repo was rebased onto the latest GitHub `main` and the staged cleanup commit was pushed

Current local-only note:

- the staged protocol repo still has an untracked local benchmark helper file:
  - `config/benchmark_inputs.live_subset.txt`
- this is a local observation artifact, not a remote-normalization blocker

### Staged Demo Repo

Current staged demo repo:

- `/Users/mac/Documents/Halfway-Lab/demos/halfway-demos`

Current `origin`:

- `git@github.com:halfway-lab/demos.git`

Meaning:

- the staged demo repo now points directly to its GitHub remote
- remote normalization for the staged demo repo is complete
- the staged cleanup commit was pushed successfully

## Why This Matters

Before normalization, the risk was:

- pushing from the staged repo may only sync back into an old local path
- the new workspace can look canonical locally while still depending on legacy local repos structurally
- remote expectations become confusing for future maintenance

Those risks are now resolved for the staged protocol and demo repos.

## Observation-Phase Recommendation

During the observation window:

- keep watching for any tooling or habit that still assumes the old local repo paths
- allow the old local paths to remain available as fallback copies only
- treat future remote cleanup mainly as a package/app/fallback retirement concern, not as a blocker for the current cutover

## Later Normalization Targets

### Protocol

Current end state:

- `/Users/mac/Documents/Halfway-Lab/protocol/HWP`
  - points directly to `git@github.com:halfway-lab/HWP.git`

### Demos

Current end state:

- `/Users/mac/Documents/Halfway-Lab/demos/halfway-demos`
  - points directly to `git@github.com:halfway-lab/demos.git`

## Suggested Timing

Still worth checking later:

- whether additional staged repos need the same remote treatment
- when the old local fallback repos can stop being kept around for rollback

## Related Documents

- `docs/workspace/HALFWAY_LAB_DAILY_CUTOVER_DECISION.md`
- `docs/workspace/OLD_HWP_OBSERVATION_AND_RETIREMENT_PLAN.md`
- `docs/workspace/LEGACY_PATH_RETIREMENT_STRATEGY.md`
