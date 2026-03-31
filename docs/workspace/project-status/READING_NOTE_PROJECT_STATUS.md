# Reading Note Package Status

Historical snapshot note:

- this file records the old package-path snapshot from the migration period
- it should not be treated as the current source for active package status
- `reading-note` now belongs in its own dedicated repository rather than under this protocol repo or workspace snapshot tree
- for the current maintained package status, prefer the dedicated `reading-note` repository docs
- for workspace-wide context, prefer `/Users/mac/Documents/Halfway-Lab/WORKSPACE_STATUS.md`

## Basic Info

- Project name: reading-note
- Current path: `/Users/mac/Documents/HWP Packages/reading-note`
- Repo type: package inside non-git workspace
- Maintainer role: package/app-support module
- Relationship to HWP:
  - likely a package-level integration layer around HWP concepts

## Purpose

- What this project is for:
  - package-oriented implementation for reading-note related logic
- Primary users:
  - downstream app or package developers
- Why it exists separately:
  - package-shaped codebase with its own Node build/test flow

## Current Scope

- Main features:
  - TS sources in `src/`
  - built outputs in `dist/`
  - package metadata in `package.json`
  - tests under `tests/`
- Out-of-scope items:
  - protocol source ownership
- Current maturity:
  - active but workspace-level packaging needs cleanup

## Entry Points

- Main README: `README.md`
- Main app/server entry: none
- Main package entry:
  - `src/index.ts`
  - `package.json`
- Main test entry:
  - `tests/reading-note.test.ts`

## Directory Notes

- Important directories:
  - `src/`
  - `tests/`
  - `dist/`
- Generated directories:
  - `dist/`
  - `node_modules/`
- Sensitive/local-only files:
  - `.npmrc`

## Environment and Dependencies

- Runtime:
  - Node.js
- Package manager:
  - npm
- Required env files or secrets:
  - confirm whether `.npmrc` contains registry-specific setup
- External services/providers:
  - local HWP checkout is expected for HWP-backed flows

## Current Commands

- Install:
  - `npm install`
- Dev:
  - no dedicated `dev` script in `package.json`
- Build:
  - `npm run build`
- Test:
  - `npm test`
- Verify:
  - `npm run build && npm test`

## Current Risks

- Known issues:
  - workspace itself is not a git repo
  - generated files and package state are mixed with source
- Migration risks:
  - package paths and lockfile assumptions may break if moved carelessly
- Path or config coupling:
  - `src/hwp.ts` reads `HWP_REPO_PATH`
  - fallback repo guesses include `../HWP`, `../../HWP`, and `__dirname ../../HWP`
  - `README.md` assumes a local HWP checkout
  - `.npmrc` should be reviewed before publishing or moving package config

## Next Development Step

- Highest-priority next task:
  - replace relative HWP repo guessing with a cleaner workspace-aware configuration story
- What should happen right after migration:
  - verify install/build/test from the new `packages/` location

## Notes

- This is a strong candidate for the first low-risk migration batch.
- The package has since moved out to its own dedicated repository.
- Validation in the new location succeeded with:
  - `npm install --prefer-offline --no-audit --no-fund`
  - `npm run build`
  - `npm test`
- Original path is still being kept temporarily as fallback until downstream references are updated.
- Do not treat any path inside this HWP repo as the active package home.
