# Old HWP Observation And Retirement Plan

## Goal

Define how the old canonical HWP path should be handled now that the preferred protocol repo path has moved to:

- `/Users/mac/Documents/Halfway-Lab/protocol/HWP`

The old path covered by this plan is:

- `/Users/mac/Documents/HWP`

## Current Status

The old path is no longer the preferred starting point for new protocol work.

It should now be treated as:

- a fallback canonical copy
- a rollback path during observation
- a historical local path kept temporarily to reduce migration risk

It should **not** now be treated as:

- the preferred repo for new protocol changes
- a second actively evolving canonical source

## Observation Window

Recommended initial observation window:

- 1 to 2 weeks of normal protocol work from:
  - `/Users/mac/Documents/Halfway-Lab/protocol/HWP`

The purpose of this window is to confirm that:

- daily protocol work really starts from the new path
- benchmark and verifier flows still run normally from the new path
- no hidden tooling or muscle-memory dependency keeps pulling work back to the old path

## Working Rule During Observation

During observation:

1. begin new protocol work from `/Users/mac/Documents/Halfway-Lab/protocol/HWP`
2. keep old `/Users/mac/Documents/HWP` untouched unless a rollback or comparison is needed
3. do not create fresh protocol commits in the old path unless an explicit rollback is happening
4. if an old-path-only issue is found, document it before making more changes

## Allowed Uses Of The Old Path

The old path is still allowed for:

- rollback testing
- comparison against the new canonical path
- confirming that historical local scripts or habits are no longer needed
- emergency recovery if the new canonical path hits a blocker

The old path should not be used for:

- starting ordinary new protocol work
- new default benchmark runs
- new default live validation runs
- ongoing source-of-truth protocol edits

## Exit Criteria For Final Retirement

Before stronger retirement action is taken, confirm all of these:

- at least one observation window of normal work has passed
- new protocol commits are being made from `Halfway-Lab/protocol/HWP`
- replay verification continues to pass from the new canonical path
- live validation continues to pass from the new canonical path
- no active docs still instruct developers to begin from `/Users/mac/Documents/HWP`
- no important local script still assumes the old path as its primary repo home

## Recommended Final Retirement Sequence

When the exit criteria are met:

1. make one final local archive/backup of `/Users/mac/Documents/HWP` if desired
2. clearly label it as retired or archived
3. stop using it for daily work
4. only then consider removing it from the active `Documents` workspace layout

## Rollback Rule

If the new canonical path causes unexpected problems during observation:

1. pause retirement actions
2. use `/Users/mac/Documents/HWP` as the short-term rollback path
3. document what failed in the new path
4. re-run verifier and benchmark checks after the fix
5. restart the observation window only after confidence returns

## Related Documents

- `docs/workspace/HWP_PROTOCOL_CUTOVER_CHECKLIST.md`
- `docs/workspace/HALFWAY_LAB_DAILY_CUTOVER_DECISION.md`
- `docs/workspace/LEGACY_PATH_RETIREMENT_STRATEGY.md`
