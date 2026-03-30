# Half Note Protocol Copy Upstream Relation

## Identity

- Local project path: `/Users/mac/Documents/Half Note/hwp-protocol`
- Upstream source path: `/Users/mac/Documents/HWP`
- Upstream repo URL: not recorded in this file yet; use the canonical HWP repo remote
- Relationship type:
  - direct copy

## Source of Truth

- Canonical source:
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

- Protocol logic changes must be made in `/Users/mac/Documents/HWP` first.
- If a local-only patch is unavoidable in the copy, document it immediately.
- Do not treat this copy as an equal peer of the canonical HWP repo.
