# Half Note Protocol Copy Upstream Relation

## Identity

- Local project path: `/Users/mac/Documents/Half Note/hwp-protocol`
- Upstream source path at the time of documentation: `/Users/mac/Documents/HWP`
- Current canonical upstream path: `/Users/mac/Documents/Halfway-Lab/protocol/HWP`
- Upstream repo URL: `git@github.com:halfway-lab/HWP.git`
- Relationship type:
  - direct copy

## Source of Truth

- Canonical source now:
  - `/Users/mac/Documents/Halfway-Lab/protocol/HWP`
- Fallback canonical copy during observation:
  - `/Users/mac/Documents/HWP`
- Is this project allowed to diverge long-term?
  - no
- Is direct editing allowed here?
  - only temporarily and with explicit documentation

## Sync Status

- Last known sync date:
  - unknown, needs explicit capture before migration
- Last known upstream commit/tag:
  - unknown, should be recorded before any further sync work
- Local sync confidence:
  - approximate

## Why This Copy Exists

- app-side integration convenience
- local development snapshot inside the Half Note workspace

## Current Differences

- Known local modifications:
  - not fully audited yet
- Known missing upstream updates:
  - not fully audited yet
- Known extra files only present here:
  - to be confirmed during project backup pass

## Migration Decision

- Keep as temporary copy:
  - yes, only until app-side references are cleaned up
- Replace with reference to upstream:
  - preferred
- Convert to formal fork:
  - not recommended
- Remove after migration:
  - preferred after safe replacement

## Safe Working Rule

- Protocol logic changes must be made in `/Users/mac/Documents/Halfway-Lab/protocol/HWP` first.
- Old `/Users/mac/Documents/HWP` should only be used as fallback during observation if needed.
- If a local-only patch is unavoidable in the copy, document it immediately.
- Do not treat this copy as an equal peer of the canonical HWP repo.
