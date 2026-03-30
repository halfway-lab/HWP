# Protocol Replica Execution Strategy

## Goal

Reduce protocol source-of-truth ambiguity across the Half Note workspace without breaking current app development.

This strategy covers the two local HWP replicas:

- `/Users/mac/Documents/Half Note/hwp-protocol`
- `/Users/mac/Documents/Half Note/my-app/HWP`

Canonical protocol source remains:

- `/Users/mac/Documents/HWP`

## Core Rule

Only one repo should be treated as the editable protocol source:

- canonical source:
  - `/Users/mac/Documents/HWP`

The two replicas should be treated as local historical/development artifacts, not as long-term peer sources.

## Recommended Order

Recommended handling order:

1. handle `my-app/HWP` first
2. keep `Half Note/hwp-protocol` temporarily
3. only after app migration stabilizes, deprecate `Half Note/hwp-protocol`

Why this order:

- `my-app/HWP` is inside the app repo and directly increases Batch 3 complexity
- `Half Note/hwp-protocol` is outside the app repo and is less likely to break app development just by existing
- clearing the embedded app copy first gives the biggest reduction in ambiguity for the smallest architectural cost

## Replica 1: `my-app/HWP`

Current classification:

- stale full-repo replica
- not a direct runtime dependency of the app

Recommended target outcome:

- remove it from the active app repo
- replace it with a lightweight reference marker

Recommended sequence:

1. keep the current analysis docs in canonical HWP
2. do one last hidden-dependency sanity check during Batch 3 prep
3. if no hidden dependency is found, remove `my-app/HWP` from the app repo
4. replace it with a small reference note, such as:
   - `docs/PROTOCOL_REFERENCE.md`
   - a short `README` note
5. if historical traceability is still desired, archive the snapshot outside active app source

What should be preserved before removal:

- note that the embedded repo existed
- note that it pointed to `git@github.com:halfway-lab/HWP.git`
- note the embedded snapshot commit:
  - `34d29e12a752b407de0f209319b5cb34f7ab88c2`
- note that canonical HWP is now the only protocol source

What should not be preserved inside the active app tree:

- the full embedded protocol repo itself

## Replica 2: `Half Note/hwp-protocol`

Current classification:

- copied protocol repo
- local checkout/reference repo used during Half Note development

Recommended target outcome:

- temporary keep during app migration
- later deprecate as a working protocol source

Recommended sequence:

1. keep it temporarily while Batch 3 is unresolved
2. avoid treating it as an editable peer of canonical HWP
3. once app migration is stable, decide between:
   - removing it
   - archiving it as a named local snapshot
4. if retained temporarily, keep its `UPSTREAM_RELATION.md` accurate

What should be preserved before removal or archival:

- current `docs/UPSTREAM_RELATION.md`
- project status/runbook docs already added
- note that canonical HWP is the editable source of truth

Why not remove it first:

- it is a separate replica outside the app repo
- it does not add as much immediate noise to Batch 3 as `my-app/HWP`
- removing the embedded app copy first gives a clearer app boundary

## What To Submit To GitHub

Recommended principle:

- do not submit these local replica repos as new protocol content in Half Note-related repos

What is appropriate to submit:

- reference docs
- runbooks
- upstream relation docs
- migration notes

What is not appropriate to submit:

- another full embedded HWP repo as if it were app source
- a second long-lived protocol source under app ownership

## Minimum Documentation To Keep

Before any replica is removed, make sure these facts survive in docs:

1. canonical protocol source:
   - `/Users/mac/Documents/HWP`
2. removed/archived replica path
3. reason for removal:
   - local development checkout
   - stale protocol copy
   - not source of truth
4. if relevant, the old snapshot commit
5. where developers should look instead

## Practical Recommendation

Best working plan:

1. do not submit either replica as active protocol content
2. clear `my-app/HWP` first
3. keep `Half Note/hwp-protocol` only as a temporary reference during migration
4. after Batch 3 stabilizes, deprecate or archive `Half Note/hwp-protocol`

## Next Action

When ready to continue:

1. prepare the lightweight replacement note for `my-app/HWP`
2. prepare the app-side removal plan
3. only after that start the staged `my-app` move
