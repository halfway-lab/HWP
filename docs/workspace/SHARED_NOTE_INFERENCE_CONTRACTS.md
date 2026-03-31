# Shared Note Inference Contracts

## Goal

Define the shared data-contract layer between:

- `reading-note`
- `HWP`
- `Half Note`

These contracts are first implemented in:

- `/Users/mac/Documents/Halfway-Lab/packages/reading-note/src/types.ts`

Working location rule:

- the active package home is `/Users/mac/Documents/Halfway-Lab/packages/reading-note`
- any older `protocol/HWP/packages/reading-note` copy should be treated as retirement-era history, not the live package location

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
- `reading-note` now exposes:
  - `buildReadingNoteGraph`
  - `buildHwpNoteAnalysisInput`
  - `processReadingNoteGraph`
- `HWP` now exposes a first runtime adapter through:
  - `python3 -m hwp_protocol.cli note-infer <input_json>`
- this runtime adapter is intentionally minimal and deterministic
- it is suitable as a first integration layer, not yet a final inference engine

Location note:

- contract evolution should continue from the root package home under `Halfway-Lab/packages/reading-note`

## Next Recommended Step

The next implementation step should be:

- make `Half Note` consume `NoteGraphSnapshot` plus `HwpInferenceBundle` as separate graph layers
- refine the HWP inference adapter beyond the current heuristic baseline
- decide where the long-term shared schema should live if it needs to be published or versioned independently
