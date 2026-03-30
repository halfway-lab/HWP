# Publish Checklist

## Preflight

- confirm the intended version in `package.json`
- review `README.md` for public API accuracy
- review `CHANGELOG.md` for the target release entry
- review `docs/RELEASE_0.2.0.md` if you need the longer release summary

## Validation

Run:

```bash
npm run build
npm test
npm pack --dry-run --cache /tmp/reading-note-npm-cache
```

Confirm:

- the build succeeds
- tests pass
- the tarball contains the expected public files:
  - `dist/`
  - `README.md`
  - `CHANGELOG.md`
  - `LICENSE`
  - `package.json`

## Public API Check

Confirm the intended root public API still matches the release notes:

- `processReadingNote`
- `processReadingNoteFromRounds`
- `processReadingNoteGraph`
- `processReadingNoteGraphFromRounds`
- `buildReadingNoteGraph`
- `buildHwpNoteAnalysisInput`
- `createDefaultReadingNoteHwpRunner`
- root-exported TypeScript types

## Registry Check

- confirm npm or GitHub Packages auth is active
- confirm the target registry in `publishConfig`
- confirm the package version has not already been published

## Publish

Typical command:

```bash
npm publish
```

If publishing to the configured GitHub Packages registry, ensure the current `.npmrc` and auth context are correct before publishing.

## Post-Publish

- verify the published version page renders correctly
- verify the README displays as expected
- verify install works from a clean consumer project
- publish the GitHub Release or release note using the prepared summary
