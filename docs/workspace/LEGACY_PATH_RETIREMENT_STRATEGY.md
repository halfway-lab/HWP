# Legacy Path Retirement Strategy

## Goal

Define which old workspace paths can now move into backup/retirement observation mode, and which still need to stay active.

## Status Key

- `ready_for_backup_observation`
  - can stop being the preferred daily working path
  - keep as rollback/backup path for an observation period
- `transitional_replica`
  - not preferred daily source, but still intentionally retained for a limited time

## Strategy Table

| Path | Current Status | Why | Suggested Holding Pattern |
| --- | --- | --- | --- |
| `/Users/mac/Documents/HWP Packages` | `ready_for_backup_observation` | `reading-note` has a validated staged home under `Halfway-Lab/packages/reading-note` | keep as fallback/backup during observation, do not start new package work here |
| `/Users/mac/Documents/halfway-demos` | `ready_for_backup_observation` | staged demo repo under `Halfway-Lab/demos/halfway-demos` has passed install/build | keep as fallback/backup during observation, do not start new demo work here |
| `/Users/mac/Documents/Half Note/my-app` | `ready_for_backup_observation` | staged app copy under `Halfway-Lab/apps/half-note` has passed install/build; embedded `HWP/` has been removed from active tree | keep as fallback/rollback path during observation, avoid treating as preferred daily app path |
| `/Users/mac/Documents/Half Note/hwp-protocol` | `transitional_replica` | still a local protocol replica; not preferred, and kept only while the new canonical path settles | keep temporarily, do not treat as editable peer source, deprecate after protocol cutover settles |
| `/Users/mac/Documents/HWP` | `ready_for_backup_observation` | canonical protocol path has moved to `Halfway-Lab/protocol/HWP` after staged verifier and live subset validation | keep as fallback canonical copy during observation; do not start new protocol work here |

## Practical Meaning

### Paths That Can Leave Daily Use Now

These old paths can now stop being the default working locations:

- `/Users/mac/Documents/HWP Packages`
- `/Users/mac/Documents/halfway-demos`
- `/Users/mac/Documents/Half Note/my-app`

Recommended behavior:

- stop starting new daily work there
- keep them available as rollback/backup paths during an observation period

### Path That Has Just Changed Status

This old path has now moved out of daily canonical use:

- `/Users/mac/Documents/HWP`

Reason:

- canonical protocol path is now `/Users/mac/Documents/Halfway-Lab/protocol/HWP`
- the old repo should still be kept during observation as a rollback/fallback path

### Replica Path That Should Fade Out

This path should already be treated as non-primary:

- `/Users/mac/Documents/Half Note/hwp-protocol`

Recommended behavior:

- keep temporarily
- do not treat it as a working peer repo
- plan to retire/archive it after protocol cutover stabilizes

## Suggested Observation Window

Recommended observation window before stronger retirement actions:

- app/package/demo old paths:
  - 1 to 2 weeks of normal daily work from `Halfway-Lab`
- protocol replica path:
  - keep until canonical HWP cutover has settled and the old fallback path is no longer needed

## Recommended Next Actions

1. begin daily work from `Halfway-Lab` for app/package/demo
2. treat the old app/package/demo paths as fallback only
3. begin new protocol work from `Halfway-Lab/protocol/HWP`
4. keep old `/Users/mac/Documents/HWP` only as fallback during observation
5. once protocol cutover is stable, plan retirement of:
   - `/Users/mac/Documents/Half Note/hwp-protocol`
   - later, old canonical `/Users/mac/Documents/HWP` path

## Related Document

- `docs/workspace/OLD_HWP_OBSERVATION_AND_RETIREMENT_PLAN.md`
