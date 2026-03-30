# Half Note App Workspace Status

## Basic Info

- Project name: Half Note workspace
- Current path: `/Users/mac/Documents/Half Note`
- Repo type: non-git workspace containing nested git repos
- Maintainer role: app workspace / product workspace
- Relationship to HWP:
  - contains an app repo plus a copied protocol repo

## Purpose

- What this project is for:
  - product workspace for the Half Note app and related notes/materials
- Primary users:
  - app developers
  - product experimentation
- Why it exists separately:
  - app/product work is distinct from protocol-core work

## Current Scope

- Main features:
  - app repo: `my-app`
  - copied protocol repo: `hwp-protocol`
  - top-level development note:
    - `2026-03-29-HWP开发读书笔记APP.md`
- Out-of-scope items:
  - should not become the canonical home of protocol logic
- Current maturity:
  - active workspace, structurally mixed

## Entry Points

- Main README:
  - `my-app/README.md`
  - `hwp-protocol/README.md`
- Main app/server entry:
  - `my-app/app/page.tsx`
- Main package entry:
  - `my-app/package.json`
- Main test entry:
  - app-level test commands still need explicit capture

## Directory Notes

- Important directories:
  - `my-app/`
  - `hwp-protocol/`
- Generated directories:
  - `my-app/.next/`
  - `my-app/node_modules/`
- Sensitive/local-only files:
  - `my-app/data/halfnote.db*`

## Environment and Dependencies

- Runtime:
  - Next.js / Node app for `my-app`
  - copied Python/shell protocol repo under `hwp-protocol`
- Package manager:
  - npm for `my-app`
- Required env files or secrets:
  - to confirm in app repo
- External services/providers:
  - app may depend on HWP-backed AI routes/providers

## Current Risks

- Known issues:
  - copied protocol repo may drift from the canonical HWP repo
- Migration risks:
  - nested repos plus local DB files increase move complexity
- Path or config coupling:
  - app may refer to embedded local HWP paths

## Next Development Step

- Highest-priority next task:
  - split documentation between `my-app` and the copied `hwp-protocol`
- What should happen right after migration:
  - verify app startup and protocol integration paths

## Notes

- Treat `hwp-protocol` here as a replica, not a second protocol source.
