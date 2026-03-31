# Halfway-Lab Daily Cutover Decision

Historical note:

- this document records the cutover decision at the time it was made
- for current daily paths and project status, prefer the root workspace docs under `/Users/mac/Documents/Halfway-Lab`

## Decision

From the current migration stage onward, the preferred daily working entry points should be:

- app work:
  - `/Users/mac/Documents/Halfway-Lab/apps/half-note`
- question-expander app work:
  - `/Users/mac/Documents/Halfway-Lab/apps/question-expander`
- package work:
  - dedicated `reading-note` repository
- demo work:
  - `/Users/mac/Documents/Halfway-Lab/demos/halfway-demos`

Canonical protocol work now also uses:

- `/Users/mac/Documents/Halfway-Lab/protocol/HWP`

This means the workspace has now fully cut over for daily use, including protocol-core.

## What This Means In Practice

Use `Halfway-Lab` first when doing:

- Half Note UI/app work
- Question Expander app work
- reading-note package work
- demo work

Do **not** use local protocol replicas as the source of truth.

Use canonical HWP when doing:

- protocol core
- runners
- adapters
- verification logic
- protocol-spec changes

Old `/Users/mac/Documents/HWP` should now be treated as a fallback canonical copy during an observation period, not the preferred starting point for new protocol work.

## Paths By Status

### Preferred Daily Paths

- `/Users/mac/Documents/Halfway-Lab/apps/half-note`
- `/Users/mac/Documents/Halfway-Lab/apps/question-expander`
- dedicated `reading-note` repository
- `/Users/mac/Documents/Halfway-Lab/demos/halfway-demos`
- `/Users/mac/Documents/Halfway-Lab/protocol/HWP`

### Fallback Paths

These paths still exist, but should not be the default place for new work:

- `/Users/mac/Documents/HWP Packages/reading-note`
- `/Users/mac/Documents/halfway-demos`
- `/Users/mac/Documents/Half Note/my-app`

### Transitional / Replica Paths

These paths should not be treated as normal working sources:

- `/Users/mac/Documents/Half Note/hwp-protocol`
- `/Users/mac/Documents/Half Note/_protocol-replicas/my-app-HWP-34d29e1`

## Why This Is The Right Cutover Level

This full workspace cutover is justified because:

- `reading-note` staged copy has already passed install/build/test
- `halfway-demos` staged copy has already passed install/build
- `half-note` staged copy has already passed install/build
- `my-app/HWP` has already been removed from the active app tree
- `Halfway-Lab` now has a usable root README and workspace conventions doc
- `Halfway-Lab/protocol/HWP` staged clone has already passed `bash runs/verify_v06_all.sh`
- `Halfway-Lab/protocol/HWP` staged clone has already passed the live subset baseline for `probe`, `natural`, and `mixed`
- the final protocol target path now exists and has been exercised as a working repo

## Working Rule

Starting now:

1. begin new app work from `Halfway-Lab/apps/half-note`
2. begin new question-expander app work from `Halfway-Lab/apps/question-expander`
3. begin new package work from the dedicated `reading-note` repository
4. begin new demo work from `Halfway-Lab/demos/halfway-demos`
5. begin new protocol-core work from `Halfway-Lab/protocol/HWP`

If old paths are used, treat them as compatibility paths or rollback paths, not preferred daily homes.

## Not Declared Yet

This decision does **not** yet declare:

- old paths as deleted
- `Half Note/hwp-protocol` as already removed
- immediate destruction of old `/Users/mac/Documents/HWP`

Those actions require the post-cutover observation and retirement process.

## Related Documents

- `docs/workspace/STAGED_WORKSPACE_STATUS.md`
- `docs/workspace/HWP_PROTOCOL_CUTOVER_CHECKLIST.md`
