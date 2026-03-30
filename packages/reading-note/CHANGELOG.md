# Changelog

All notable changes to `@halfway-lab/reading-note` will be documented in this file.

The format is based on Keep a Changelog, and this package follows Semantic Versioning for its root public API.

## [0.2.0] - 2026-03-30

### Added

- Added stable public post-processing APIs:
  - `processReadingNoteFromRounds(input, rounds)`
  - `processReadingNoteGraphFromRounds(input, rounds)`
- Added a stable runner extension contract:
  - `ReadingNoteHwpRunner`
  - `ReadingNoteProcessOptions`
  - `createDefaultReadingNoteHwpRunner()`
- Added graph-oriented public APIs and examples to the README.
- Added tests that lock the root export surface and key public behaviors.

### Changed

- Refined the package into a public root API with explicit stability guidance.
- Updated `processReadingNote(...)` and `processReadingNoteGraph(...)` to support injected HWP runners.
- Reorganized the internal HWP execution path so log-backed execution is now an internal default implementation instead of the only integration route.
- Promoted `0.2.0` as the first version with an explicit public API stability and versioning story.

### Fixed

- Sanitized structured HWP input line values to avoid delimiter collisions from user-provided text.
- Improved graph analysis neighbor detection so incoming links are included.
- Reduced graph note ID collision risk with stable hashed suffixes.
- Aligned package contents, docs, and exports so published artifacts match the documented public API.
