# Staged Repo Remote Normalization

## Goal

Record the current remote state of staged repos inside `Halfway-Lab`, and define what still needs to be normalized now that daily work has cut over.

## Current Findings

### Canonical Protocol Repo

Current staged canonical repo:

- `/Users/mac/Documents/Halfway-Lab/protocol/HWP`

Current `origin`:

- `/Users/mac/Documents/HWP`

Meaning:

- the new canonical working repo is still chained to the old local repo path as its remote
- this is acceptable during local observation
- this is not the ideal long-term remote setup for a true canonical repo

### Staged Demo Repo

Current staged demo repo:

- `/Users/mac/Documents/Halfway-Lab/demos/halfway-demos`

Current `origin`:

- `/Users/mac/Documents/halfway-demos`

Meaning:

- the staged demo repo still treats the old local demo repo as upstream
- this is acceptable during observation
- this should be normalized later if the staged repo becomes the stable long-term home

## Why This Matters

Without remote normalization:

- pushing from the staged repo may only sync back into an old local path
- the new workspace can look canonical locally while still depending on legacy local repos structurally
- remote expectations become confusing for future maintenance

## Observation-Phase Recommendation

During the observation window:

- keep the current local-path remotes in place if they are helping rollback safety
- avoid pretending that remote normalization is already finished
- treat this as a separate infrastructure cleanup step after the path cutover stabilizes

## Later Normalization Targets

### Protocol

Desired end state:

- `/Users/mac/Documents/Halfway-Lab/protocol/HWP`
  - should point directly to the intended canonical Git remote

### Demos

Desired end state:

- `/Users/mac/Documents/Halfway-Lab/demos/halfway-demos`
  - should point directly to its intended long-term Git remote

## Suggested Timing

Do this after:

- the observation window is stable
- the old fallback paths are no longer being used for rollback
- the new workspace paths are clearly accepted as the real long-term homes

## Related Documents

- `docs/workspace/HALFWAY_LAB_DAILY_CUTOVER_DECISION.md`
- `docs/workspace/OLD_HWP_OBSERVATION_AND_RETIREMENT_PLAN.md`
- `docs/workspace/LEGACY_PATH_RETIREMENT_STRATEGY.md`
