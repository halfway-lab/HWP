# My App Data Migration Strategy

## Scope

This document defines how to handle local app data for:

- `/Users/mac/Documents/Half Note/my-app/data`

during Batch 3 and later workspace migration.

## What Exists Today

Current data layout includes:

- `data/halfnote.db`
- `data/halfnote.db-shm`
- `data/halfnote.db-wal`
- `data/users/`
- multiple user DB files under `data/users/`

Observed examples:

- `data/users/1565faf5.db`
- `data/users/242e21de.db`
- `data/users/72c21936.db`
- `data/users/test123.db`

Interpretation:

- this is active local application state
- it is not build output
- it is not source code
- it should not be treated like normal repo content during migration

## Runtime Relationship

The app database layer lives in:

- `/Users/mac/Documents/Half Note/my-app/lib/db.ts`

Current behavior:

- database root is `path.join(process.cwd(), 'data')`
- user DB files are created under `data/users/`
- SQLite WAL mode is enabled

Migration implication:

- the app expects local writable storage under `data/`
- the runtime path is app-root-relative, not hardcoded to an absolute filesystem path
- if the app root moves, `data/` should move with it unless a deliberate storage redesign happens later

## Current Risk

Important facts:

- `.gitignore` currently ignores `.next`, `node_modules`, and `.env*`
- `.gitignore` does **not** currently ignore `data/`
- `data/` is currently part of the dirty worktree inventory

Risk:

- local DB state could be accidentally committed
- local DB state could be lost or overwritten during a careless move
- WAL/SHM companion files make “copy just the .db file” an unsafe default

## Recommended Rule

Treat `data/` as:

- local runtime state
- movable with the app during staged migration
- not intended for normal source control

## Recommended Batch 3 Strategy

### Short-Term Working Rule

For the upcoming app migration work:

- keep `data/` with the app workspace
- do not delete it
- do not treat it as disposable build output
- do not include it in broad source commits by accident

### Migration Rule

If `my-app` is staged into a future location such as:

- `/Users/mac/Documents/Halfway-Lab/apps/half-note`

then `data/` should be copied with the staged app workspace as local state.

Meaning:

- app source move: yes
- app local `data/` move: yes
- commit local DB files to git by default: no

### Commit Rule

Recommended default:

- add explicit ignore rules for:
  - `data/*.db`
  - `data/*.db-shm`
  - `data/*.db-wal`
  - `data/users/*.db`
  - `data/users/*.db-shm`
  - `data/users/*.db-wal`

This keeps the app runnable locally while reducing accidental commit risk.

## What To Avoid

Avoid:

- deleting `data/` as part of protocol replica cleanup
- moving only the base `.db` files but not the WAL/SHM files
- mixing local DB cleanup with app source refactors
- assuming test/demo DB files are safe to commit without a deliberate decision

## Success Criteria

This part of Batch 3 is handled well when:

- local DB files are preserved during app staging
- the staged app can still resolve `process.cwd()/data`
- DB files are not accidentally added to normal source commits

## Recommended Next Action

Before or during the next app-focused step:

1. add ignore rules for local DB files in `my-app/.gitignore`
2. keep `data/` as local runtime state
3. when the staged app copy is created, copy `data/` with it
