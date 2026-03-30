# Phased Migration Checklist

## Goal

Move from the current scattered `/Users/mac/Documents` layout into a cleaner workspace structure without losing git history, breaking path assumptions, or confusing protocol ownership.

Target workspace:

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

## Before Any Move

Complete these checks first:

- [x] Confirm canonical protocol source is `/Users/mac/Documents/HWP`
- [x] Confirm `/Users/mac/Documents/Half Note/hwp-protocol` is a copied replica
- [x] Create workspace planning docs
- [x] Create per-project backup/status docs
- [x] Create upstream relation doc for copied protocol repo
- [x] Confirm actual install/dev/build/test commands for each non-HWP project
- [x] Record current git remote URLs for all git repos
- [x] Record any absolute-path assumptions found in scripts or app config

## Batch 0: Command and Path Audit

Objective:

- finish documentation before moving directories

Required tasks:

- [x] Confirm `reading-note` package commands from `package.json`
- [x] Confirm `halfway-demos` startup/build/test commands
- [x] Confirm `Half Note/my-app` startup/build/test commands
- [x] Search `halfway-demos` for references to `/Users/mac/Documents/HWP`
- [x] Search `Half Note/my-app` for references to local `HWP` paths
- [x] Search `reading-note` for path assumptions or local-only config

Exit condition:

- all projects have known commands and known path-coupling notes

Batch 0 findings:

- `reading-note`
  - location: `/Users/mac/Documents/HWP Packages/reading-note`
  - install: `npm install`
  - dev: none declared in `package.json`
  - build: `npm run build`
  - test: `npm test`
  - git remote: none for the workspace itself
  - path coupling:
    - `src/hwp.ts` reads `HWP_REPO_PATH`
    - fallback guesses include `../HWP`, `../../HWP`, and `__dirname ../../HWP`
    - `README.md` explicitly assumes a local HWP checkout

- `halfway-demos`
  - location: `/Users/mac/Documents/halfway-demos`
  - repo remote: `git@github.com:halfway-lab/demos.git`
  - primary demo commands currently live under `demos/question-expander`
  - install: `npm install`
  - dev: `npm run dev`
  - build: `npm run build`
  - preview: `npm run preview`
  - adapter helpers:
    - `npm run adapter`
    - `npm run adapter:live`
    - `npm run adapter:live:file`
    - `npm run adapter:replay`
  - path coupling:
    - `tools/question-expander-adapter.mjs` defaults `HWP_REPO_PATH` to `/Users/mac/Documents/HWP`
    - `demos/question-expander/package.json` hardcodes `/Users/mac/Documents/HWP` in `adapter:live` and `adapter:replay`
    - `demos/question-expander/tools/llm-agent-bridge.mjs` also defaults to `/Users/mac/Documents/HWP`

- `Half Note/my-app`
  - location: `/Users/mac/Documents/Half Note/my-app`
  - repo remote: none configured
  - install: `npm install`
  - dev: `npm run dev`
  - build: `npm run build`
  - start: `npm start`
  - lint: `npm run lint`
  - path coupling:
    - app depends on `@halfway-lab/reading-note`
    - local DB files under `data/halfnote.db*` must move with the app
    - repo contains an embedded `HWP/` tree that adds duplicate protocol materials and migration noise
    - direct app code did not show hardcoded `/Users/mac/Documents/HWP`, but the embedded `HWP/` copy contains many such references

Git remote snapshot:

- canonical HWP repo:
  - `/Users/mac/Documents/HWP` -> `git@github.com:halfway-lab/HWP.git`
- demos repo:
  - `/Users/mac/Documents/halfway-demos` -> `git@github.com:halfway-lab/demos.git`
- copied protocol repo:
  - `/Users/mac/Documents/Half Note/hwp-protocol` -> `git@github.com:halfway-lab/HWP.git`
- app repo:
  - `/Users/mac/Documents/Half Note/my-app` -> no git remote configured

## Batch 1: Packages Move

Move:

- `/Users/mac/Documents/HWP Packages/reading-note`
  ->
- `/Users/mac/Documents/Halfway-Lab/packages/reading-note`

Why first:

- lowest repo-history risk
- not the protocol source
- not the app workspace root

Pre-move checklist:

- [ ] `reading-note/docs/PROJECT_STATUS.md` reviewed
- [ ] `reading-note/docs/RUNBOOK.md` updated with actual commands
- [ ] `node_modules/` is treated as local-only and not part of the move plan
- [ ] package build/test commands are verified in current location

Post-move checklist:

- [x] install works
- [x] build works
- [x] test works
- [ ] any downstream references are updated

Current staged migration status:

- a staged copy now exists at `/Users/mac/Documents/Halfway-Lab/packages/reading-note`
- original source at `/Users/mac/Documents/HWP Packages/reading-note` is still being kept as fallback
- copied scope excluded local/generated items such as `.DS_Store`, `.qoder`, `node_modules`, and `dist`
- fresh validation in the new location succeeded with:
  - `npm install --prefer-offline --no-audit --no-fund`
  - `npm run build`
  - `npm test`

## Batch 2: Demo Move

Move:

- `/Users/mac/Documents/halfway-demos`
  ->
- `/Users/mac/Documents/Halfway-Lab/demos/halfway-demos`

Why second:

- standalone git repo
- lower source-of-truth risk than protocol/app work

Pre-move checklist:

- [ ] `halfway-demos/docs/PROJECT_STATUS.md` reviewed
- [ ] `halfway-demos/docs/RUNBOOK.md` updated with actual commands
- [ ] tool scripts audited for absolute HWP paths

Post-move checklist:

- [ ] demo startup commands still work
- [ ] tool scripts still locate protocol resources correctly
- [ ] asset paths remain valid

## Batch 3: App Move

Move:

- `/Users/mac/Documents/Half Note/my-app`
  ->
- `/Users/mac/Documents/Halfway-Lab/apps/half-note`

Why third:

- app is more path-sensitive
- contains local DB files and embedded HWP material

Pre-move checklist:

- [ ] `my-app/docs/PROJECT_STATUS.md` reviewed
- [ ] `my-app/docs/RUNBOOK.md` updated with actual commands
- [ ] local DB handling is documented
- [ ] embedded `HWP/` references are identified

Post-move checklist:

- [ ] app dev mode runs
- [ ] app build runs
- [ ] local DB still resolves
- [ ] app-to-HWP integration paths are repaired

## Batch 4: Protocol Copy Cleanup

Handle:

- `/Users/mac/Documents/Half Note/hwp-protocol`

This is not a “move first” item. It is a cleanup and de-duplication item.

Preferred sequence:

- [ ] keep it temporarily while app migration stabilizes
- [ ] document exact differences versus canonical HWP
- [ ] reduce any remaining dependency on the local copy
- [ ] replace with a cleaner upstream reference or remove after migration

Success condition:

- there is only one true protocol source in daily practice:
  `/Users/mac/Documents/HWP`

## Batch 5: Protocol Workspace Placement

Optional final move:

- `/Users/mac/Documents/HWP`
  ->
- `/Users/mac/Documents/Halfway-Lab/protocol/HWP`

Why last:

- highest centrality
- highest path-coupling risk
- current main development source

Pre-move checklist:

- [ ] all other project moves are already stable
- [ ] runner/spec/test relative paths are understood
- [ ] any cross-project references are ready to be updated

Post-move checklist:

- [ ] replay benchmarks still pass
- [ ] live benchmarks still pass
- [ ] docs paths still resolve
- [ ] downstream projects can still find canonical protocol repo

## What Must Be Verified After Every Batch

- [ ] git history remains intact
- [ ] README still matches reality
- [ ] `docs/PROJECT_STATUS.md` updated if the path changed
- [ ] `docs/RUNBOOK.md` updated if commands changed
- [ ] any absolute paths are repaired
- [ ] local-only generated data is not accidentally committed

## Recommended Immediate Next Step

Do next:

1. Finish Batch 0 command/path audit.
2. Move `reading-note` first.
3. Verify `reading-note` in the new workspace.
4. Only then proceed to `halfway-demos`.
