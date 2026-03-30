# Reading Note Package Status

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
  - not confirmed yet

## Current Commands

- Install:
  - `npm install`
- Dev:
  - confirm from `package.json`
- Build:
  - confirm from `package.json`
- Test:
  - confirm from `package.json`
- Verify:
  - package-specific verification still needs to be documented

## Current Risks

- Known issues:
  - workspace itself is not a git repo
  - generated files and package state are mixed with source
- Migration risks:
  - package paths and lockfile assumptions may break if moved carelessly
- Path or config coupling:
  - local node/npm layout should be checked before move

## Next Development Step

- Highest-priority next task:
  - capture exact npm commands and intended package role
- What should happen right after migration:
  - verify install/build/test from the new `packages/` location

## Notes

- This is a strong candidate for the first low-risk migration batch.
