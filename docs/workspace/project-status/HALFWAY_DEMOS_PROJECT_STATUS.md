# Halfway Demos Project Status

Historical snapshot note:

- this file is kept as a migration-era summary under the protocol workspace docs
- for the current maintained demo status, prefer `/Users/mac/Documents/Halfway-Lab/demos/halfway-demos/docs/PROJECT_STATUS.md`
- for workspace-wide context, prefer `/Users/mac/Documents/Halfway-Lab/WORKSPACE_STATUS.md`

## Basic Info

- Project name: halfway-demos
- Current path: `/Users/mac/Documents/Halfway-Lab/demos/halfway-demos`
- Repo type: standalone git repo inside the Halfway-Lab workspace
- Maintainer role: demo/tooling repo
- Relationship to HWP:
  - demo-facing usage of HWP tools and adapters

## Purpose

- What this project is for:
  - demo experiences, assets, and helper tools around HWP
- Primary users:
  - demo builders
  - internal experimentation
- Why it exists separately:
  - cleaner separation between protocol core and demo-specific artifacts

## Current Scope

- Main features:
  - `demos/`
  - `tools/`
  - `assets/`
  - repo-level README/docs
- Out-of-scope items:
  - protocol source ownership
- Current maturity:
  - active demo support repo in the Halfway-Lab workspace

## Entry Points

- Main README: `README.md`
- Main app/server entry:
  - `demos/question-expander` for the primary documented demo flow
  - repo-level adapter helper at `tools/question-expander-adapter.mjs`
- Main package entry:
  - not primary
- Main test entry:
  - `cd demos/question-expander && npm run test:run`

## Directory Notes

- Important directories:
  - `demos/`
  - `tools/`
  - `assets/`
  - `docs/`
- Generated directories:
  - none obvious from quick scan
- Sensitive/local-only files:
  - none confirmed yet

## Environment and Dependencies

- Runtime:
  - Node-based tooling and Vite demo app
- Package manager:
  - npm
- Required env files or secrets:
  - adapter/provider config may be used by tools
- External services/providers:
  - HWP-compatible adapters or APIs

## Current Commands

- Install:
  - `cd demos/question-expander && npm install`
- Dev:
  - `cd demos/question-expander && npm run dev`
- Build:
  - `cd demos/question-expander && npm run build`
- Test:
  - `cd demos/question-expander && npm run test:run`
- Verify:
  - `cd demos/question-expander && npm run build`
  - `cd demos/question-expander && npm run test:run`
  - `cd demos/question-expander && npm run adapter`
  - `cd demos/question-expander && npm run adapter:live`
  - `cd demos/question-expander && npm run adapter:live:file`
  - `cd demos/question-expander && npm run adapter:replay`

## Current Risks

- Known issues:
  - current runbook is still split between repo-level and demo-level docs
- Migration risks:
  - some historical docs still preserve pre-cutover paths
- Path or config coupling:
  - active defaults now point to `/Users/mac/Documents/Halfway-Lab/protocol/HWP`
  - `adapter:replay` still depends on a specific local chain-log path
  - some adapter helpers preserve fallback behavior for older local paths during observation

## Next Development Step

- Highest-priority next task:
  - keep reducing legacy fallback assumptions while preserving a safe rollback path during observation
- What should happen right after migration:
  - continue testing tool-to-protocol path references from the new workspace

## Notes

- Old `/Users/mac/Documents/halfway-demos` should now be treated as a fallback path only.
- `apps/question-expander` is the product-app counterpart for question expansion; this repo remains the demo/prototype home.
- Validation in the new location succeeded with:
  - `cd demos/question-expander && npm install --prefer-offline --no-audit --no-fund`
  - `cd demos/question-expander && npm run build`
- Staged path hardening is already in place for:
  - `tools/question-expander-adapter.mjs`
  - `demos/question-expander/tools/llm-agent-bridge.mjs`
- `adapter:replay` still carries a legacy fallback chain-log path and should be cleaned up later, after protocol/log placement is finalized.
- If this file diverges from `demos/halfway-demos/docs/PROJECT_STATUS.md`, treat the demo-repo document as authoritative.
