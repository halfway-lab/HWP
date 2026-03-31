# Phased Migration Checklist

Historical note:

- this checklist preserves the phased migration process and original move order
- items below may remain as completed migration history even when the current workspace has already moved past that phase

## Goal

Move from the scattered `/Users/mac/Documents` layout into a cleaner workspace structure without losing git history, breaking path assumptions, or confusing protocol ownership.

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
    /question-expander
  /docs
    /workspace
```

Current status:

- this target layout now exists and is the preferred daily workspace
- canonical protocol path is now `/Users/mac/Documents/Halfway-Lab/protocol/HWP`
- `apps/question-expander` now exists as a separate product app under the root `apps/` directory
- old `/Users/mac/Documents/HWP` is now a fallback canonical copy during observation

## Before Any Move

Complete these checks first:

- [x] Confirm original canonical protocol source was `/Users/mac/Documents/HWP`
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

Batch 0 findings were recorded against the original scattered layout and are kept here as migration history.

- `reading-note`
  - original location: `/Users/mac/Documents/HWP Packages/reading-note`
  - install: `npm install`
  - dev: none declared in `package.json`
  - build: `npm run build`
  - test: `npm test`
  - git remote: none for the workspace itself

- `halfway-demos`
  - original location: `/Users/mac/Documents/halfway-demos`
  - repo remote: `git@github.com:halfway-lab/demos.git`
  - primary demo commands currently live under `demos/question-expander`
  - install: `npm install`
  - dev: `npm run dev`
  - build: `npm run build`
  - preview: `npm run preview`

- `Half Note/my-app`
  - original location: `/Users/mac/Documents/Half Note/my-app`
  - repo remote: none configured
  - install: `npm install`
  - dev: `npm run dev`
  - build: `npm run build`
  - start: `npm start`
  - lint: `npm run lint`

Git remote snapshot at audit time:

- original canonical HWP repo:
  - `/Users/mac/Documents/HWP` -> `git@github.com:halfway-lab/HWP.git`
- original demos repo:
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

- preferred daily path has already cut over to `/Users/mac/Documents/Halfway-Lab/packages/reading-note`
- old package path is now fallback-only
