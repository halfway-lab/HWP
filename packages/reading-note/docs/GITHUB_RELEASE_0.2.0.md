# GitHub Release Body: 0.2.0

## `@halfway-lab/reading-note` 0.2.0

`0.2.0` promotes `@halfway-lab/reading-note` into a clearer public API for reading-note extraction and graph shaping on top of HWP rounds.

### Highlights

- Added stable pure post-processing APIs:
  - `processReadingNoteFromRounds(input, rounds)`
  - `processReadingNoteGraphFromRounds(input, rounds)`
- Added a stable execution extension point:
  - `ReadingNoteHwpRunner`
  - `processReadingNote(input, { hwpRunner })`
  - `processReadingNoteGraph(input, { hwpRunner })`
- Added `createDefaultReadingNoteHwpRunner()` for consumers that want the built-in execution path
- Clarified that the package root is the supported public contract
- Added API stability and semantic versioning guidance

### Why this release matters

Consumers can now integrate against stable root exports instead of coupling to internal HWP runner and log details.

- If your app already owns HWP execution, use:
  - `processReadingNoteFromRounds(...)`
  - `processReadingNoteGraphFromRounds(...)`
- If your app wants this package to drive execution, use:
  - `processReadingNote(...)`
  - `processReadingNoteGraph(...)`
- If your app needs custom execution wiring, provide:
  - `ReadingNoteHwpRunner`

### Validation

Verified with:

```bash
npm run build
npm test
npm pack --dry-run --cache /tmp/reading-note-npm-cache
```
