# Shared Note Inference Contracts

## Goal

Define the shared data-contract layer between:

- `reading-note`
- `HWP`
- `Half Note`

These contracts are first implemented in:

- `/Users/mac/Documents/Halfway-Lab/packages/reading-note/src/types.ts`

## Contract Split

### Explicit Layer

Owned by `reading-note`.

Primary contract types:

- `NoteRecord`
- `ExplicitLink`
- `BacklinkRecord`
- `RelationScore`
- `GraphNode`
- `GraphEdge`
- `NoteGraphSnapshot`
- `NoteContextWindow`

These types describe what is explicitly present in the note system.

### Inference Request Layer

Passed from the note layer into `HWP`.

Primary contract type:

- `HwpNoteAnalysisInput`

This keeps `HWP` grounded in note data instead of app UI state.

### Inference Result Layer

Owned by `HWP`.

Primary contract types:

- `InferenceExplanation`
- `InferenceConfidence`
- `InferredRelation`
- `LatentBridge`
- `DriftTrace`
- `ThematicPath`
- `CandidateCluster`
- `HwpInference`
- `HwpInferenceBundle`

These types describe inferred structure that is not explicitly present in note links.

## Design Rule

The architecture rule is:

1. `reading-note` exports explicit note and graph structure.
2. `HWP` consumes that structure and exports inferred structure.
3. `Half Note` renders both layers without redefining their business logic.

## Current Implementation Status

Current status:

- the shared TypeScript-facing contract draft now exists in:
  - `/Users/mac/Documents/Halfway-Lab/packages/reading-note/src/types.ts`
- this is currently a schema draft, not yet a fully wired runtime pipeline

## Next Recommended Step

The next implementation step should be:

- make `reading-note` export a stable `NoteGraphSnapshot`
- then add an HWP-facing adapter that consumes `HwpNoteAnalysisInput`
- then make `Half Note` consume explicit plus inferred graph layers separately
