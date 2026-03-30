# My App Protocol Reference Note Draft

## Purpose

This draft is the proposed lightweight replacement note for the day when:

- `/Users/mac/Documents/Half Note/my-app/HWP`

is removed from the app repo.

The goal is to preserve developer orientation without keeping a full stale protocol repo inside `my-app`.

## Recommended Future Location

One of these locations inside `my-app` would be appropriate:

- `docs/PROTOCOL_REFERENCE.md`
- or a short section inside `README.md`

Preferred default:

- `docs/PROTOCOL_REFERENCE.md`

## Draft Content

Suggested note text:

---

# Protocol Reference

This app does not treat an embedded `HWP/` folder as its protocol source anymore.

Canonical HWP source:

- local canonical repo:
  - `/Users/mac/Documents/HWP`
- upstream repo:
  - `git@github.com:halfway-lab/HWP.git`

Why the embedded copy was removed:

- it was a local development-era protocol replica
- it was not the canonical source of truth
- it did not appear to be a required runtime dependency for the app
- keeping it inside the app repo increased source-of-truth ambiguity

How this app connects to HWP-related capability:

- app AI flow currently uses:
  - `@halfway-lab/reading-note`
- key app integration file:
  - `lib/ai.ts`

If you need protocol-core changes:

1. make the change in canonical HWP
2. verify it there first
3. then update the app/package integration path if needed

Historical note:

- this app previously carried an embedded HWP replica
- if you need the old snapshot reference, check workspace migration docs in canonical HWP

---

## Shorter Alternative

If a shorter version is preferred for `README.md`, use:

---

## Protocol Source

This app does not maintain its own embedded HWP source.

Use canonical HWP instead:

- local: `/Users/mac/Documents/HWP`
- upstream: `git@github.com:halfway-lab/HWP.git`

The previous embedded `HWP/` directory was a local development-era replica, not the long-term source of truth.

---

## Recommendation

When Batch 3 reaches the actual cleanup step:

1. add `docs/PROTOCOL_REFERENCE.md` to `my-app`
2. only then remove the embedded `HWP/` tree
3. optionally add one short sentence to `my-app/README.md` pointing to the new reference note
