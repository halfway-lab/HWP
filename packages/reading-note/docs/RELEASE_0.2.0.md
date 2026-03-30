# `@halfway-lab/reading-note` 0.2.0 Release Summary

## Overview

`0.2.0` turns `@halfway-lab/reading-note` into a clearer public API for reading-note extraction and graph shaping on top of HWP rounds.

This release is centered on one idea:

- consumers should integrate against stable root exports instead of internal runner and log details

## Highlights

- Added stable pure post-processing APIs:
  - `processReadingNoteFromRounds(input, rounds)`
  - `processReadingNoteGraphFromRounds(input, rounds)`
- Added a stable execution extension point:
  - `ReadingNoteHwpRunner`
  - `processReadingNote(input, { hwpRunner })`
  - `processReadingNoteGraph(input, { hwpRunner })`
- Added `createDefaultReadingNoteHwpRunner()` for consumers that want the built-in execution path
- Clarified that the package root is the supported public contract
- Added API stability and semantic versioning guidance to the README
- Added changelog coverage for the public API surface

## Why This Matters

Before this release, the package worked, but the internal HWP execution path and log-backed behavior were too close to the integration surface.

With `0.2.0`:

- apps that already own HWP execution can integrate through `fromRounds(...)`
- apps that want this package to execute HWP can still use the default flow
- apps such as Half Note can inject a stable runner without coupling to local log parsing

## Supported Public API

Import from:

```ts
import { ... } from "@halfway-lab/reading-note";
```

Supported root APIs:

- `processReadingNote`
- `processReadingNoteFromRounds`
- `processReadingNoteGraph`
- `processReadingNoteGraphFromRounds`
- `buildReadingNoteGraph`
- `buildHwpNoteAnalysisInput`
- `createDefaultReadingNoteHwpRunner`
- public root-exported TypeScript types

Not part of the public contract:

- deep imports
- workspace-only source paths
- internal log parsing details
- temp-file and repo-discovery internals

## Validation

Verified with:

```bash
npm run build
npm test
npm pack --dry-run --cache /tmp/reading-note-npm-cache
```

## Suggested Short Release Note

`@halfway-lab/reading-note@0.2.0` promotes the package to a clearer public API. This release adds stable `fromRounds(...)` entrypoints, a supported `ReadingNoteHwpRunner` extension point, explicit API stability guidance, and release/changelog documentation so integrators can depend on the package root without coupling to internal HWP runner details.
