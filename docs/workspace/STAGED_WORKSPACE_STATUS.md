# Staged Workspace Status

## Snapshot

This document records the current staged migration status for the future workspace root:

`/Users/mac/Documents/Halfway-Lab`

Current staged layout:

```text
/Users/mac/Documents/Halfway-Lab
  /packages
    /reading-note
  /demos
    /halfway-demos
```

Not yet staged:

- canonical protocol repo:
  - `/Users/mac/Documents/HWP`
- app workspace:
  - `/Users/mac/Documents/Half Note/my-app`
- protocol copy cleanup:
  - `/Users/mac/Documents/Half Note/hwp-protocol`

## What Is Already Staged

### Reading Note

- staged location:
  - `/Users/mac/Documents/Halfway-Lab/packages/reading-note`
- migration mode:
  - copied into the new workspace while keeping the original path as fallback
- original location still preserved:
  - `/Users/mac/Documents/HWP Packages/reading-note`

Validation completed in the staged location:

- `npm install --prefer-offline --no-audit --no-fund`
- `npm run build`
- `npm test`

Validation result:

- install passed
- build passed
- test passed

Important note:

- the staged package currently includes fresh local `node_modules/` and `dist/`
- those are useful for immediate validation, but they are local artifacts rather than migration goals

### Halfway Demos

- staged location:
  - `/Users/mac/Documents/Halfway-Lab/demos/halfway-demos`
- migration mode:
  - local git clone so staged copy keeps full git history
- original repo still preserved:
  - `/Users/mac/Documents/halfway-demos`

Validation completed in the staged location:

- `cd demos/question-expander && npm install --prefer-offline --no-audit --no-fund`
- `cd demos/question-expander && npm run build`

Validation result:

- install passed
- build passed

Staged path hardening already applied:

- `tools/question-expander-adapter.mjs`
  - now prefers `HWP_REPO_PATH`
  - then tries `Halfway-Lab/protocol/HWP`
  - then falls back to the legacy HWP path
- `demos/question-expander/tools/llm-agent-bridge.mjs`
  - now follows the same repo-path resolution strategy
- `demos/question-expander/package.json`
  - `adapter:live` no longer hardcodes `/Users/mac/Documents/HWP`

Current staged demo commit head:

- `b8cbf20 fix: make HWP demo paths workspace-aware`

Known remaining cleanup:

- `adapter:replay` still carries a legacy fallback chain-log path
- replay/log placement should be finalized later, together with protocol placement

## Why Batch 3 Is Different

`my-app` is not in the same state as `reading-note` or `halfway-demos`.

Current app repo path:

- `/Users/mac/Documents/Half Note/my-app`

Current state:

- repo already has many local modifications
- repo also has many untracked directories/files
- repo contains an embedded `HWP/` tree
- repo keeps local DB files under `data/halfnote.db*`

That means Batch 3 is not just a move. It is a cleanup and ownership clarification task.

Main risks before staging `my-app`:

- unclear source-of-truth boundaries because of embedded `HWP/`
- local data files must not be lost or accidentally committed
- existing worktree is already dirty, so a migration could mix new structure work with unrelated app work
- `my-app` depends on `@halfway-lab/reading-note`, so package-location assumptions should be checked after Batch 1 changes

## Recommended Pre-Batch-3 Approach

Do before staging `my-app`:

1. produce a focused inventory of the current dirty worktree
2. separate migration-related files from active app development files
3. decide what `my-app/HWP` actually is:
   - disposable copy
   - fixture
   - temporary embedded dependency
4. decide how `data/halfnote.db*` should be handled during migration
5. only then create a staged app copy under:
   - `/Users/mac/Documents/Halfway-Lab/apps/half-note`

## Practical Interpretation

The workspace migration is going well, but it is still in a staged phase rather than a final cutover phase.

Current reality:

- `reading-note` has a validated staged home
- `halfway-demos` has a validated staged home
- the canonical protocol repo is still at its original path
- the app workspace is the next real complexity boundary

## Next Recommended Step

Before touching Batch 3:

- create a dedicated `my-app` migration-risk summary
- capture which current `my-app` changes are migration-related vs product-development-related
- avoid moving `my-app` until that separation is explicit

Related document:

- `docs/workspace/MY_APP_MIGRATION_RISK_SUMMARY.md`
- `docs/workspace/MY_APP_HWP_DISPOSITION_OPTIONS.md`

Current classification shortcut:

- product-development-heavy:
  - `app/`
  - `components/`
  - `lib/`
  - `types/`
  - `public/logo.png`
  - `design-system.md`
- migration-risk-heavy:
  - `HWP/`:
    - currently best understood as a stale full-repo replica of canonical HWP
    - does not currently appear to be a direct runtime dependency of the app
  - `data/`
  - `docs/`
- local/generated:
  - `.next/`
  - `node_modules/`
