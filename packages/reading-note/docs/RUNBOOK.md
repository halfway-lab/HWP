# Reading Note Runbook

## Current Commands

- install: `npm install`
- build: `npm run build`
- test: `npm test`
- verify: `npm run build && npm test`

## Notes

- there is no dedicated `dev` script in `package.json`
- the package expects a local HWP checkout
- prefer setting `HWP_REPO_PATH` explicitly instead of relying on relative repo guessing

## Migration Verification

- package still resolves `HWP_REPO_PATH` after the move
- local package consumption still works after relocation
- `dist/` can be rebuilt cleanly in the new location
