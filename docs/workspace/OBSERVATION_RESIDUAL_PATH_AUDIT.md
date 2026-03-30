# Observation Residual Path Audit

## Goal

Record the first post-cutover audit of lingering references to the old protocol path:

- `/Users/mac/Documents/HWP`

This audit helps separate:

- expected fallback mentions
- still-active references that should be cleaned up during observation

## Summary

The first audit shows that old-path references still exist, but they are not all the same kind.

### Category A: Expected Observation/Fallback Mentions

These are acceptable for now because they explain the cutover and fallback policy:

- `Halfway-Lab/README.md`
- `Halfway-Lab/WORKSPACE_CONVENTIONS.md`
- `Halfway-Lab/protocol/README.md`
- workspace cutover docs under `docs/workspace/`

These should remain temporarily while the observation window is active.

### Category B: Stale Active-Repo Documentation

These should be cleaned up in the new canonical protocol repo:

- `Halfway-Lab/protocol/HWP/README.md`
  - still contains many absolute links pointing at the old path
- `Halfway-Lab/protocol/HWP/docs/PROJECT_STATUS.md`
  - still says current path is `/Users/mac/Documents/HWP`
- some copied workspace/project-status docs inside the new canonical repo still describe the old path as active

These are no longer ideal because they can confuse developers about the new canonical location.

### Category C: Live Tooling Defaults Still Pointing At The Old Path

These are the most important practical cleanup targets:

- `Halfway-Lab/demos/halfway-demos/tools/question-expander-adapter.mjs`
  - still carries the old path as a fallback candidate
- `Halfway-Lab/demos/halfway-demos/demos/question-expander/tools/llm-agent-bridge.mjs`
  - still carries the old path as a fallback candidate
- `Halfway-Lab/demos/halfway-demos/demos/question-expander/package.json`
  - `adapter:replay` still points at a chain log under the old path
- `Halfway-Lab/demos/halfway-demos/demos/question-expander/.env.live.example`
  - still suggests `HWP_REPO_PATH=/Users/mac/Documents/HWP`

These are valid observation-period cleanup items because they can still pull day-to-day usage back toward the old location.

## Recommended Cleanup Order

### 1. New Canonical Protocol Repo Docs

First clean the most visible docs in:

- `/Users/mac/Documents/Halfway-Lab/protocol/HWP/README.md`
- `/Users/mac/Documents/Halfway-Lab/protocol/HWP/docs/PROJECT_STATUS.md`

Goal:

- make the new canonical repo self-describe correctly

### 2. Demo Live/Replay Defaults

Next clean demo defaults so they prefer the new canonical path:

- `tools/question-expander-adapter.mjs`
- `demos/question-expander/tools/llm-agent-bridge.mjs`
- `demos/question-expander/package.json`
- `demos/question-expander/.env.live.example`

Goal:

- reduce practical drift back to the old path

### 3. Secondary Historical Docs

Later, update copied migration/status docs inside the new canonical repo where useful.

Goal:

- reduce confusion without over-prioritizing historical notes

## Current Recommendation

The observation window should continue, but the next cleanup work should focus on:

1. new canonical protocol repo docs
2. demo default path assumptions

Those two areas give the highest value for the least risk.
