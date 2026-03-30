# Halfway Demos Project Status

## Basic Info

- Project name: halfway-demos
- Current path: `/Users/mac/Documents/halfway-demos`
- Repo type: standalone git repo
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
  - active / demo support repo

## Entry Points

- Main README: `README.md`
- Main app/server entry:
  - demo-specific, to be confirmed from tools/scripts
- Main package entry:
  - not primary
- Main test entry:
  - not yet formalized in current quick scan

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
  - likely Node-based tooling
- Package manager:
  - to confirm
- Required env files or secrets:
  - adapter/provider config may be used by tools
- External services/providers:
  - HWP-compatible adapters or APIs

## Current Commands

- Install:
  - to confirm from repo docs
- Dev:
  - to confirm from repo docs
- Build:
  - to confirm from repo docs
- Test:
  - to confirm from repo docs
- Verify:
  - to confirm from repo docs

## Current Risks

- Known issues:
  - current runbook not yet centralized
- Migration risks:
  - demo tools may reference absolute or sibling paths under `/Users/mac/Documents`
- Path or config coupling:
  - likely coupled to current HWP repo path in some helper scripts

## Next Development Step

- Highest-priority next task:
  - capture actual demo startup commands and path assumptions
- What should happen right after migration:
  - test tool-to-protocol path references

## Notes

- This is a good early migration candidate once docs and runbook are captured.
