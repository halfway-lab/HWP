# UPSTREAM_RELATION Template

Use this document only for a repo or directory that is a copy, mirror, embedded snapshot, or downstream adaptation of another source project.

## Identity

- Local project path:
- Upstream source path:
- Upstream repo URL:
- Relationship type:
  - direct copy / embedded snapshot / fork / downstream adaptation

## Source of Truth

- Canonical source:
- Is this project allowed to diverge long-term?
- Is direct editing allowed here?

Recommended default:

- Canonical source is upstream
- Direct editing here should be temporary and minimal

## Sync Status

- Last known sync date:
- Last known upstream commit/tag:
- Local sync confidence:
  - exact / approximate / unknown

## Why This Copy Exists

- App integration
- temporary experimentation
- local packaging
- legacy compatibility
- other:

## Current Differences

- Known local modifications:
- Known missing upstream updates:
- Known extra files only present here:

## Migration Decision

- Keep as temporary copy:
- Replace with reference to upstream:
- Convert to formal fork:
- Remove after migration:

## Safe Working Rule

- When protocol logic changes, update upstream first.
- If a local-only patch is unavoidable, document it immediately.
- Never assume this copy is the primary source unless explicitly re-designated.
