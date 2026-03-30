# Workspace Reorganization Plan

## Goal

Create a single, predictable workspace layout for the four active project areas under `/Users/mac/Documents`, while keeping git history intact and avoiding a risky all-at-once migration.

This plan treats:

- `/Users/mac/Documents/HWP` as the protocol source of truth
- `/Users/mac/Documents/HWP Packages` as the package workspace
- `/Users/mac/Documents/halfway-demos` as the demo repo
- `/Users/mac/Documents/Half Note` as the app workspace

## Current Reality

### Protocol

- Path: `/Users/mac/Documents/HWP`
- Git: yes
- Role: canonical HWP protocol source
- Notes:
  - Contains protocol core, spec, runners, tests, docs, configs, adapters
  - This is the upstream source for protocol work

### Packages

- Path: `/Users/mac/Documents/HWP Packages`
- Git: no
- Current child:
  - `reading-note`
- Notes:
  - `reading-note` has Node package structure and build artifacts
  - This workspace should become a clean package area

### Demo

- Path: `/Users/mac/Documents/halfway-demos`
- Git: yes
- Notes:
  - Looks like a standalone demo/tooling repo
  - Already has its own README, docs, tools, and assets

### App

- Path: `/Users/mac/Documents/Half Note`
- Git: no
- Important children:
  - `hwp-protocol` (git repo)
  - `my-app` (git repo)
- Notes:
  - `hwp-protocol` is confirmed to be a copy of `HWP`
  - `my-app` is the actual app repo
  - There is also a top-level product/development note file:
    - `2026-03-29-HWP开发读书笔记APP.md`

## Source-of-Truth Rule

For protocol work:

- Source of truth: `/Users/mac/Documents/HWP`
- Replica/copy: `/Users/mac/Documents/Half Note/hwp-protocol`

This means the copy under `Half Note` should not be treated as a long-term independent protocol repo.

## Recommended Target Workspace

Recommended future layout:

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
  /docs
    /workspace
```

Notes:

- Keep each git repo as its own repo during migration.
- Do not force monorepo conversion in phase 1.
- The first goal is consistent placement, not repo unification.

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

### Phase 2: Low-Risk Moves

Move first:

- `HWP Packages/reading-note`
- `halfway-demos`

Reason:

- Lower coupling than the main protocol repo
- Easier to repair references if needed

### Phase 3: App Workspace Cleanup

Then handle:

- `Half Note/my-app`
- top-level app notes/docs

Also decide what to do with:

- `Half Note/hwp-protocol`

Preferred direction:

- deprecate it as a long-term editable repo
- replace with a documented link/reference to the canonical protocol repo

### Phase 4: Protocol Workspace Placement

Finally decide whether to:

- move `HWP` under the new workspace root
- or keep it where it is temporarily and only normalize the other projects first

Recommended:

- move protocol last, because it is the current main development source

## First Batch Checklist

The first actual batch should be:

1. Create the backup docs for all four project areas.
2. Create `UPSTREAM_RELATION.md` for `Half Note/hwp-protocol`.
3. Confirm current startup/test commands for:
   - HWP
   - reading-note
   - halfway-demos
   - Half Note/my-app
4. Only after that, begin directory migration.

## Decisions Already Made

- `HWP` is the canonical protocol source.
- `Half Note/hwp-protocol` is a copied replica of `HWP`.
- Migration should be phased.
- Backup docs must be prepared before moving projects.
- local protocol replicas in the Half Note workspace should not be treated as long-term peer protocol sources.

Related execution doc:

- `docs/workspace/PROTOCOL_REPLICA_EXECUTION_STRATEGY.md`
- `docs/workspace/HWP_PROTOCOL_CUTOVER_CHECKLIST.md`

## Post-Reorg Product Direction

After the workspace structure is stabilized, the next development step should follow a clearer module split instead of mixing note logic, inference logic, and UI logic in one place.

Recommended responsibility split:

- `reading-note package`
  - note model
  - double-link parsing
  - backlinks
  - graph node/edge generation
  - relation scoring
- `HWP package`
  - cognitive generation
  - relation discovery
  - implicit connection inference
  - topic drift analysis
  - path analysis
- `Half Note`
  - UI lists and note views
  - double-link panel
  - graph visualization
  - node-click navigation

Architectural rule:

- `reading-note` owns explicit note structure
- `HWP` owns inferred or exploratory structure
- `Half Note` consumes those outputs and renders the user experience
