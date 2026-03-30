# My App Migration Risk Summary

## Scope

This document summarizes the current migration risks for:

- `/Users/mac/Documents/Half Note/my-app`

It exists to prepare Batch 3 without mixing app-product work, local data, and protocol-copy cleanup into one uncontrolled move.

## Current Repo State

Path:

- `/Users/mac/Documents/Half Note/my-app`

Git remote:

- none configured

Current worktree state:

- not clean
- has both modified tracked files and many untracked directories/files

Tracked modified files:

- `app/globals.css`
- `app/layout.tsx`
- `app/page.tsx`
- `next.config.ts`
- `package-lock.json`
- `package.json`

Untracked top-level areas:

- `HWP/`
- `app/api/`
- `app/book/`
- `app/insight/`
- `app/nav/`
- `app/result/`
- `components/`
- `data/`
- `design-system.md`
- `docs/`
- `lib/`
- `public/logo.png`
- `types/`

Interpretation:

- this is not a repo that can be safely “moved as-is” without first separating migration work from ongoing application development

## Current Change Classification

The current dirty worktree is best understood as three different classes of changes rather than one batch.

### 1. Product Development Changes

These look like active application/product work, not migration work:

- tracked UI shell changes:
  - `app/globals.css`
  - `app/layout.tsx`
  - `app/page.tsx`
  - `next.config.ts`
  - `package.json`
  - `package-lock.json`
- new route areas:
  - `app/api/`
  - `app/book/`
  - `app/insight/`
  - `app/nav/`
  - `app/result/`
- new UI/component areas:
  - `components/`
  - `types/`
  - `public/logo.png`
  - `design-system.md`
- new app logic:
  - `lib/`

Observed signal:

- this looks like a meaningful application build-out
- it should be treated as app product work first, migration work second

### 2. Migration-Risk Structure

These are the items that directly affect workspace migration safety:

- `HWP/`
  - embedded protocol tree inside the app repo
- `data/`
  - local SQLite database files and user data
- `docs/`
  - useful for backup/continuity, but not a migration blocker by itself

Observed signal:

- these are the parts that most directly create source-of-truth ambiguity or local-state handling risk

### 3. Local/Generated Artifacts

These should not drive the migration decision:

- `.next/`
- `node_modules/`
- `.git/index.lock`

Observed signal:

- these are local runtime/build artifacts
- they should be ignored, rebuilt, or cleaned as needed rather than “migrated” as source

## Main Coupling Points

### Reading Note Dependency

The app currently depends on:

- `@halfway-lab/reading-note`

Observed usage:

- `lib/ai.ts`
- `app/api/process/route.ts`

Migration implication:

- after Batch 1, the package has a staged workspace home, but the app still resolves the published npm package today
- Batch 3 should explicitly decide whether the app keeps consuming the published package or switches to a local workspace/package link later

### Local Database

The app uses:

- `better-sqlite3`
- `lib/db.ts`
- local files under `data/halfnote.db*`

Observed local data size:

- `data/`: about `428K`

Migration implication:

- database files are small enough to move safely, but they are local state and must not be treated like normal source files
- the migration plan should explicitly define whether `data/` is copied, ignored, backed up, or regenerated

### Embedded Protocol Copy

The app repo contains:

- `/Users/mac/Documents/Half Note/my-app/HWP`

Observed size:

- embedded `HWP/`: about `1.0M`

Observed risk:

- this directory is an additional embedded protocol tree
- it creates source-of-truth ambiguity
- it also contains many references to canonical HWP paths in its own docs/materials
- it is not just loose reference material; it is a full git repo copy

Observed repo facts:

- remote:
  - `git@github.com:halfway-lab/HWP.git`
- current branch:
  - `main`
- embedded repo HEAD:
  - `34d29e12a752b407de0f209319b5cb34f7ab88c2`
- canonical HWP current HEAD:
  - `cd53ad05204a724cc8786b4abfecb1e89a738bf5`

Interpretation:

- this is best classified as a stale full-repo replica of HWP
- it is not a lightweight fixture
- it is not a clean downstream dependency either
- it preserves an older state of HWP inside the app repo and therefore increases drift risk over time

Observed app-runtime relationship:

- direct app/runtime code did not show imports from the embedded `HWP/` tree
- actual AI integration goes through:
  - `@halfway-lab/reading-note`
  - `lib/ai.ts`
  - `app/api/process/route.ts`
- database handling is separate and local:
  - `lib/db.ts`
  - `data/`

Working implication:

- the embedded `HWP/` tree does not currently appear to be a required runtime dependency for the app
- it behaves more like an in-repo stale protocol copy/reference bundle than an active execution dependency

Migration implication:

- Batch 3 should not treat `my-app/HWP` as a normal app directory
- it must first be classified as one of:
  - disposable copy
  - explicit reference snapshot
  - temporary embedded dependency

Until that is decided, moving the app repo would preserve ambiguity instead of reducing it.

## Local Artifact Pressure

Current local/generated directories:

- `.next/`: about `311M`
- `node_modules/`: about `496M`

Relevant ignore rules already exist for:

- `node_modules`
- `.next`
- `.env*`

Important gap:

- current `.gitignore` does not explicitly mention `data/halfnote.db*`

Migration implication:

- generated artifacts should not influence the migration decision
- `data/` handling should be made explicit before staging the app move

## Why Batch 3 Is Higher Risk

Compared with `reading-note` and `halfway-demos`, `my-app` is higher risk because:

1. the repo is already dirty
2. the repo includes local state, not just source code
3. the repo includes an embedded protocol tree
4. the repo has no configured remote, so lineage/publish workflow is less obvious
5. the repo is where UI/product development is happening, so a migration mistake is more disruptive

## Recommended Pre-Move Decisions

Before creating a staged app copy under:

- `/Users/mac/Documents/Halfway-Lab/apps/half-note`

decide these items explicitly:

1. Is `my-app/HWP` being removed, archived, or preserved as a named fixture?
2. Should `data/halfnote.db*` be copied into the staged app workspace, or kept local-only?
3. Should the app continue consuming published `@halfway-lab/reading-note`, or switch later to a workspace-local package?
4. Which current modified/untracked files belong to active product work versus migration work?

More specific interpretation:

- most current UI/routes/components/lib changes belong to product development
- `HWP/` and `data/` are the true migration-risk items
- `.next/` and `node_modules/` are local generated artifacts and should stay out of the move plan

## Recommended Batch 3 Entry Plan

Suggested order:

1. snapshot the current dirty worktree inventory
2. separate migration-only notes from active product changes
3. classify `my-app/HWP`
4. decide database handling
5. only then create the staged app copy

Practical split for step 2:

- product development bucket:
  - `app/`
  - `components/`
  - `lib/`
  - `types/`
  - `public/logo.png`
  - `design-system.md`
- migration-risk bucket:
  - `HWP/`
  - `data/`
  - `docs/`
- generated/local bucket:
  - `.next/`
  - `node_modules/`

## Recommended Working Classification For `my-app/HWP`

Based on the current evidence, the most accurate working classification is:

- stale full-repo replica of canonical HWP

More specifically:

- not an active app runtime dependency
- not a lightweight fixture
- effectively a stale embedded protocol copy/reference bundle

This means the default planning assumption should be:

- do not keep editing it as if it were an equal protocol source
- do not silently migrate it as ordinary app content
- either archive it as an explicit snapshot, or remove/replace it after extracting anything the app truly still needs

## Practical Conclusion

`my-app` should be treated as a cleanup-and-boundary batch, not a simple relocation batch.

That means Batch 3 should begin with clarification work, not with copying files.
