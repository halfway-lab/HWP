# HWP Protocol Cutover Checklist

## Goal

Define the conditions that should be satisfied before moving canonical HWP from:

- `/Users/mac/Documents/HWP`

to its intended future workspace location:

- `/Users/mac/Documents/Halfway-Lab/protocol/HWP`

## Why HWP Moves Last

Canonical HWP is still the most central repo in the entire workspace.

It currently anchors:

- protocol core
- runners
- adapters
- verification scripts
- migration status docs

It also remains the protocol source of truth for:

- `reading-note`
- `halfway-demos`
- `half-note`

That makes it the highest-risk relocation in the whole workspace plan.

## Current Readiness Snapshot

Already true:

- `reading-note` has a validated staged home under `Halfway-Lab/packages/reading-note`
- `halfway-demos` has a validated staged home under `Halfway-Lab/demos/halfway-demos`
- `half-note` has a validated staged home under `Halfway-Lab/apps/half-note`
- the embedded app-side `my-app/HWP` replica has been removed from the active app tree
- workspace entry docs now exist in `Halfway-Lab`
- daily-use cutover for app/package/demo can now be declared separately from protocol cutover
- a staged protocol clone now exists at `Halfway-Lab/protocol/HWP`
- the staged protocol clone has passed `bash runs/verify_v06_all.sh`
- the staged protocol clone has passed a live subset baseline for `probe`, `natural`, and `mixed`

Not yet true:

- canonical HWP is still the live protocol source at `/Users/mac/Documents/HWP`
- `/Users/mac/Documents/Half Note/hwp-protocol` still exists as a temporary local protocol replica
- final cutover policy has not yet been declared

## Required Conditions Before Cutover

### 1. Workspace Entry Stability

Confirm that daily work can already start from:

- `Halfway-Lab/apps/half-note`
- `Halfway-Lab/packages/reading-note`
- `Halfway-Lab/demos/halfway-demos`

Desired condition:

- old paths are fallback only, not the preferred starting point for new work

### 2. Replica Ambiguity Reduced

Confirm both of these:

- `my-app/HWP` is no longer in the active app tree
- `Half Note/hwp-protocol` is no longer treated as an editable peer source

Desired condition:

- developers have only one real protocol source in practice:
  - `/Users/mac/Documents/HWP`

### 3. Cross-Project Path Review

Before moving HWP, re-check these path-sensitive areas:

- `reading-note`
  - `HWP_REPO_PATH`
  - fallback repo guessing in `src/hwp.ts`
- `halfway-demos`
  - `tools/question-expander-adapter.mjs`
  - `demos/question-expander/tools/llm-agent-bridge.mjs`
  - any remaining replay/log fallback paths
- workspace docs
  - root `Halfway-Lab/README.md`
  - `Halfway-Lab/WORKSPACE_CONVENTIONS.md`
  - HWP workspace docs under `docs/workspace/`

Desired condition:

- moving HWP would require only known, bounded path updates

### 4. Protocol Validation Baseline

Immediately before cutover, confirm protocol validation from canonical HWP still passes.

Minimum recommended checks:

- replay benchmark baseline
- one live benchmark subset
- current structured/verifier pipeline

Desired condition:

- cutover starts from a verified green baseline, not from a questionable state

### 5. Old-Path Fallback Policy

Decide in advance:

- whether `/Users/mac/Documents/HWP` will remain temporarily as a fallback clone/path
- or whether the move is intended as a direct cutover

Preferred safer option:

- use a staged/copy-based cutover first, then switch daily workflow, then retire the old path

### 6. Documentation Cutover Plan

Before moving HWP, know which docs must be updated immediately afterward:

- `Halfway-Lab/README.md`
- `Halfway-Lab/WORKSPACE_CONVENTIONS.md`
- HWP `README.md`
- workspace migration docs under `docs/workspace/`
- any scripts or docs that still mention `/Users/mac/Documents/HWP`

Desired condition:

- documentation change list is explicit before the move starts

## Minimum Cutover Checklist

Use this as the direct go/no-go list:

- [ ] staged app/package/demo paths are the practical daily starting points
- [ ] `Half Note/hwp-protocol` is no longer being treated as a working peer source
- [ ] remaining HWP path-sensitive scripts are identified
- [x] replay/log-based verifier baseline is green in the staged protocol clone
- [x] live subset baseline is green in the staged protocol clone
- [x] `Halfway-Lab/protocol/` target path plan is prepared
- [ ] immediate post-move documentation edits are listed
- [ ] fallback policy for old `/Users/mac/Documents/HWP` is decided

## Recommended Cutover Method

Preferred order:

1. create `/Users/mac/Documents/Halfway-Lab/protocol`
2. make a staged copy or clone of canonical HWP there
3. validate replay/live baselines from the staged protocol location
4. update workspace docs to point to the new canonical protocol location
5. only then declare `Halfway-Lab/protocol/HWP` the preferred protocol path
6. retire old `/Users/mac/Documents/HWP` later, after confidence is high

This mirrors the same low-risk strategy used for the other staged workspace moves.

## Recommendation

Current recommendation:

- do not move canonical HWP yet
- finish the cutover checklist first
- then perform a staged protocol migration rather than a direct one-step move

Related decision doc:

- `docs/workspace/HALFWAY_LAB_DAILY_CUTOVER_DECISION.md`
