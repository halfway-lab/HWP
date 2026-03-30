# Reading Note Package Status

## Basic Info

- Project name: reading-note
- Current path: `/Users/mac/Documents/Halfway-Lab/packages/reading-note`
- Repo type: package inside the Halfway-Lab workspace
- Maintainer role: package/app-support module
- Relationship to HWP:
  - package-level integration layer around HWP-backed note logic

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
  - active package in the Halfway-Lab workspace

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
  - local canonical HWP checkout may be used for HWP-backed flows

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
  - generated files and package state are still mixed with source in the local workspace
- Migration risks:
  - package paths and lockfile assumptions may still need continued cleanup
- Path or config coupling:
  - `src/hwp.ts` reads `HWP_REPO_PATH`
  - fallback repo guesses still exist for compatibility
  - `README.md` assumes a local HWP checkout
  - `.npmrc` should be reviewed before publishing or moving package config

## Next Development Step

- Highest-priority next task:
  - continue replacing relative HWP repo guessing with a cleaner workspace-aware configuration story
- What should happen right after migration:
  - keep verifying install/build/test from the new `packages/` location

## Notes

- Old `/Users/mac/Documents/HWP Packages/reading-note` should now be treated as a fallback path only.
