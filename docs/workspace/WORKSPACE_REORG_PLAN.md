# Workspace Reorganization Plan

Historical note:

- this plan records the migration framing and original starting state
- the active workspace has already cut over; treat this file as planning history plus high-level rationale

## Goal

Create a single, predictable workspace layout for the four active project areas under `/Users/mac/Documents`, while keeping git history intact and avoiding a risky all-at-once migration.

This plan originally started from:

- `/Users/mac/Documents/HWP` as the protocol source of truth
- `/Users/mac/Documents/HWP Packages` as the package workspace
- `/Users/mac/Documents/halfway-demos` as the demo repo
- `/Users/mac/Documents/Half Note` as the app workspace

Current reality after cutover:

- canonical protocol path is now `/Users/mac/Documents/Halfway-Lab/protocol/HWP`
- old `/Users/mac/Documents/HWP` is now a fallback canonical copy during observation
- old package/demo/app paths are now fallback or retirement-observation paths

## Historical Starting Reality

### Protocol

- Original path: `/Users/mac/Documents/HWP`
- Current canonical path: `/Users/mac/Documents/Halfway-Lab/protocol/HWP`
- Git: yes
- Role:
  - canonical HWP protocol source moved into the Halfway-Lab workspace
- Notes:
  - Contains protocol core, spec, runners, tests, docs, configs, adapters
  - Old `/Users/mac/Documents/HWP` is now kept only as a fallback during observation

### Packages

- Original path: `/Users/mac/Documents/HWP Packages`
- Migration-stage preferred path: `/Users/mac/Documents/Halfway-Lab/packages/reading-note`
- Git: no workspace repo for the old package area
- Current child:
  - `reading-note`
- Notes:
  - `reading-note` later moved beyond the workspace staging path into its own dedicated repository
  - the old package workspace is now fallback-only

### Demo

- Original path: `/Users/mac/Documents/halfway-demos`
- Current preferred path: `/Users/mac/Documents/Halfway-Lab/demos/halfway-demos`
- Git: yes
- Notes:
  - the staged demo repo is now the preferred daily path
  - the old local demo path is now fallback-only

### App

- Original path: `/Users/mac/Documents/Half Note`
- Current preferred app path: `/Users/mac/Documents/Halfway-Lab/apps/half-note`
- Git: no top-level app workspace repo
- Important children in the old location:
  - `hwp-protocol` (git repo replica)
  - `my-app` (git repo)
- Notes:
  - `hwp-protocol` is confirmed to be a copy of HWP
  - `my-app` was the original app repo
  - the old app-side embedded `HWP/` replica has already been removed from the active app tree

## Source-of-Truth Rule

For protocol work now:

- Canonical source: `/Users/mac/Documents/Halfway-Lab/protocol/HWP`
- Fallback canonical copy during observation: `/Users/mac/Documents/HWP`
- Replica/copy: `/Users/mac/Documents/Half Note/hwp-protocol`

This means the copy under `Half Note` should not be treated as a long-term independent protocol repo.

## Recommended Target Workspace

The planned target layout is now the active working layout:

```text
/Users/mac/Documents/Halfway-Lab
  /protocol
    /HWP
  /packages
    /reading-note
  /demos
    /halfway-demos
  /apps
    /half-note
    /question-expander
  /docs
    /workspace
```

Notes:

- Keep each git repo as its own repo during migration.
- Do not force monorepo conversion in phase 1.
- The first goal was consistent placement, not repo unification.
- That placement goal is now largely achieved for daily work.

## Migration Principles

1. Keep git history intact.
2. Do not migrate everything in one step.
3. Document every project before moving anything.
4. Treat copied protocol trees as replicas, not equal peers.
5. Prefer fixing path references after each batch instead of after a giant move.

## Required Backup Before Migration

Before moving any project, create or confirm these docs inside each project:

- `README.md`
- `docs/PROJECT_STATUS.md`
- `docs/DEV_LOG.md`
- `docs/RUNBOOK.md`

For copied or downstream protocol trees, also create:

- `docs/UPSTREAM_RELATION.md`

## Phase Plan

### Phase 1: Documentation and Backup

Do first:

- Create workspace-level migration docs
- Create per-project status docs
- Create upstream relation doc for copied protocol repo
- Capture current run/test commands
- Capture current repo relationships
