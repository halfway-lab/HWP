# Observation Residual Path Audit

## Goal

Record the first post-cutover audit of lingering references to the old protocol path:

- `/Users/mac/Documents/HWP`

This audit helps separate:

- expected fallback mentions
- still-active references that should be cleaned up during observation

## Summary

The first audit showed that old-path references still existed, but they were not all the same kind.

After the first cleanup pass:

- the new canonical protocol repo README/path docs were updated
- active demo defaults were updated to point to the new canonical HWP path
- active staged demo docs were refreshed to describe the new path behavior
- active staged package docs were refreshed locally inside `Halfway-Lab`
- active staged app protocol reference notes were refreshed locally inside `Halfway-Lab`
- staged demo adapter scripts no longer keep `/Users/mac/Documents/HWP` as a hardcoded fallback candidate

That means the most misleading active-path documentation has already been reduced.

### Category A: Expected Observation/Fallback Mentions

These are acceptable for now because they explain the cutover and fallback policy:

- `Halfway-Lab/README.md`
- `Halfway-Lab/WORKSPACE_CONVENTIONS.md`
- `Halfway-Lab/protocol/README.md`
- workspace cutover docs under `docs/workspace/`

These should remain temporarily while the observation window is active.

### Category B: Stale Active-Repo Documentation

These were the first cleanup targets in the new canonical protocol repo:

- `Halfway-Lab/protocol/HWP/README.md`
  - now updated to point at the new canonical path for active links
- `Halfway-Lab/protocol/HWP/docs/PROJECT_STATUS.md`
  - now updated to the new canonical path
- some copied workspace/project-status docs inside the new canonical repo still describe the old path as active

Remaining issue:

- copied historical workspace/project-status docs inside the canonical repo still preserve old-path context

These are lower priority than active docs, because many of them are historical migration records rather than front-door developer guidance.

### Category C: Live Tooling Defaults Still Pointing At The Old Path

These were the most important practical cleanup targets:

- `Halfway-Lab/demos/halfway-demos/tools/question-expander-adapter.mjs`
  - still carries the old path as a fallback candidate
- `Halfway-Lab/demos/halfway-demos/demos/question-expander/tools/llm-agent-bridge.mjs`
  - still carries the old path as a fallback candidate
- `Halfway-Lab/demos/halfway-demos/demos/question-expander/package.json`
  - now points replay examples at the new canonical HWP logs path
- `Halfway-Lab/demos/halfway-demos/demos/question-expander/.env.live.example`
  - now suggests `HWP_REPO_PATH=/Users/mac/Documents/Halfway-Lab/protocol/HWP`

Remaining issue:

- the demo adapter scripts no longer use the old absolute HWP path
- remaining compatibility logic now prefers environment override plus the new canonical workspace path

This means the highest-risk live default drift back to the old path has now been reduced.

## Recommended Cleanup Order

### 1. Secondary Historical Docs

Next clean lower-priority copied historical docs in:

- `/Users/mac/Documents/Halfway-Lab/protocol/HWP/docs/workspace/`
- copied project-status records that still describe the pre-cutover layout

Goal:

- reduce confusion without over-prioritizing historical notes

### 2. Compatibility Fallback Review

Later review whether these compatibility fallbacks are still needed:

- `tools/question-expander-adapter.mjs`
- `demos/question-expander/tools/llm-agent-bridge.mjs`

Goal:

- remove practical drift back to the old path only after the rollback window is no longer valuable

## Current Recommendation

The observation window should continue. The next cleanup work should focus on:

1. secondary historical docs inside the canonical repo
2. eventual review of whether any remaining compatibility fallbacks can be reduced further

Those are now the highest-value remaining cleanup areas with relatively low operational risk.
