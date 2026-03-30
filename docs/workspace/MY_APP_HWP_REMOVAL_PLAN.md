# My App Embedded HWP Removal Plan

## Goal

Prepare a safe removal path for:

- `/Users/mac/Documents/Half Note/my-app/HWP`

without breaking current app behavior.

## Latest Sanity Check Result

A final hidden-dependency sanity check was performed against likely runtime/config code paths in `my-app`.

Observed result:

- no direct runtime imports from the embedded `HWP/` tree were found
- no hardcoded runtime path references to the embedded `HWP/` tree were found in app execution code
- process routes continue to call:
  - `@halfway-lab/reading-note`
  - `lib/ai.ts`
- streaming and non-streaming process routes both resolve through the app integration layer, not the embedded protocol repo

Interpretation:

- the embedded `HWP/` tree currently appears removable from an app-runtime perspective
- remaining risk is workflow/documentation habit risk, not primary runtime dependency risk

## Preconditions Before Removal

Complete these first:

1. keep canonical HWP available at:
   - `/Users/mac/Documents/HWP`
2. keep `my-app/docs/PROTOCOL_REFERENCE.md` in place
3. do not combine the removal with unrelated product-feature edits
4. do not treat `.next/` or `node_modules/` as part of the cleanup decision

## Recommended Removal Sequence

1. Preserve the reference note
   - keep `docs/PROTOCOL_REFERENCE.md`

2. Preserve historical traceability in docs
   - keep migration docs in canonical HWP
   - preserve the known embedded snapshot commit in docs:
     - `34d29e12a752b407de0f209319b5cb34f7ab88c2`

3. Remove the embedded tree from `my-app`
   - target:
     - `/Users/mac/Documents/Half Note/my-app/HWP`

4. Re-run a light app sanity check
   - inspect `git status`
   - confirm `lib/ai.ts` still points to `@halfway-lab/reading-note`
   - confirm API routes still compile logically against the package path

5. Decide later whether to archive the old embedded snapshot elsewhere
   - outside active app source

## What Not To Do

Avoid:

- removing `HWP/` and `data/` in the same step
- mixing embedded-HWP cleanup with broad app refactors
- treating the cleanup as proof that `my-app` is ready for full migration immediately

## Success Criteria

Removal is considered successful when:

- `my-app/HWP` is no longer present in the active app repo
- `docs/PROTOCOL_REFERENCE.md` remains available
- app integration still clearly points to canonical HWP via `@halfway-lab/reading-note`
- no new hidden dependency on the embedded protocol tree appears

## Recommended Next Action

When you decide to execute cleanup rather than just prepare for it:

1. snapshot current `my-app` worktree state
2. remove only `my-app/HWP`
3. re-check repo status
4. then continue Batch 3 planning
