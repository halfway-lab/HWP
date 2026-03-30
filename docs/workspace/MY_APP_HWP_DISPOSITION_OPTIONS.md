# My App Embedded HWP Disposition Options

## Scope

This document defines practical options for handling:

- `/Users/mac/Documents/Half Note/my-app/HWP`

Current working classification:

- stale full-repo replica of canonical HWP
- not a direct runtime dependency of the app

## What It Actually Contains

The embedded tree is not a tiny fixture. It is a full HWP-style repo layout with top-level areas such as:

- `.github`
- `adapters`
- `archive`
- `config`
- `docs`
- `hwp_protocol`
- `inputs`
- `runs`
- `spec`
- `tests`

This matters because the decision is not “keep a helper folder or not”. The decision is whether to keep an entire stale protocol repo inside the app repo.

## Option A: Leave It In Place

Description:

- keep `my-app/HWP` exactly where it is

Pros:

- zero immediate file movement
- no short-term disruption risk

Cons:

- preserves protocol source-of-truth ambiguity
- keeps a stale full repo inside the app repo
- increases future migration confusion
- makes new contributors more likely to edit the wrong HWP tree

Assessment:

- lowest short-term effort
- worst long-term hygiene

Recommendation:

- not recommended as the steady-state plan

## Option B: Reclassify It As An Explicit Snapshot

Description:

- keep the embedded repo content temporarily, but rename/reframe it as a clear snapshot or archive
- example future location:
  - `my-app/archive/hwp-snapshot-34d29e1`

Pros:

- preserves any historical context the app workspace may still want
- removes the illusion that this is a live protocol source
- safer than immediate deletion if there is still uncertainty

Cons:

- still keeps extra protocol material inside the app repo
- requires a cleanup move and naming decision
- still needs later follow-up to decide whether the snapshot is truly needed

Assessment:

- good transitional option
- especially useful if the team wants a low-risk intermediate step

Recommendation:

- reasonable fallback option if immediate removal feels too aggressive

## Option C: Remove It From The App Repo And Rely On Canonical HWP

Description:

- remove the embedded `HWP/` tree from `my-app`
- treat canonical HWP as the only protocol source
- if app documentation needs protocol references, point to canonical HWP instead

Pros:

- strongest source-of-truth clarity
- reduces app repo clutter
- aligns with the current runtime reality that the app does not directly execute this embedded tree

Cons:

- requires confidence that no hidden workflow still depends on the embedded copy
- if someone was using it manually as a local reference, that habit must change

Assessment:

- cleanest end state
- best long-term architecture

Recommendation:

- best final-state option if no hidden dependency is found

## Option D: Replace It With A Lightweight Reference Marker

Description:

- remove the embedded full repo
- leave behind a tiny documentation pointer or marker file
- for example:
  - `docs/PROTOCOL_REFERENCE.md`
  - a note in `README.md`
  - optional commit reference to the old snapshot

Pros:

- keeps the app repo focused
- preserves discoverability for developers
- avoids shipping a full stale repo inside the app workspace

Cons:

- still requires a prior decision on whether any snapshot should be archived elsewhere first

Assessment:

- best companion to Option C
- often the most balanced developer-experience choice

Recommendation:

- strongly recommended together with Option C

Related draft:

- `docs/workspace/MY_APP_PROTOCOL_REFERENCE_NOTE_DRAFT.md`
- `docs/workspace/MY_APP_HWP_REMOVAL_PLAN.md`

## Recommended Path

Best practical sequence:

1. Treat `my-app/HWP` as a stale full-repo replica, not a dependency.
2. Do one final hidden-dependency sanity check during Batch 3 prep.
3. Prepare the lightweight replacement note in advance.
4. If no hidden dependency appears, remove it from the app repo.
5. Replace it with a lightweight reference note that points to canonical HWP.
6. If the team still wants historical traceability, archive a named snapshot outside the active app source tree.

## Recommended Working Decision

Default recommendation:

- final state: Option C + Option D

Conservative transition if the team wants one extra safety step:

- short-term transition: Option B
- final state afterward: Option C + Option D

## What To Avoid

Avoid these patterns:

- continuing to treat `my-app/HWP` as a second editable protocol source
- silently migrating it with the app as if it were normal UI code
- leaving it unnamed and unexplained inside the app repo

## Next Action

Before moving `my-app` into the staged workspace:

- choose whether to go with:
  - transitional archive path: Option B
  - direct cleanup path: Option C + Option D
