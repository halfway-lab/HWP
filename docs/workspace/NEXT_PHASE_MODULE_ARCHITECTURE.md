# Next-Phase Module Architecture

## Goal

Define the next development-phase module boundaries for the reorganized Halfway-Lab workspace.

This document turns the current product direction into a practical architecture split across:

- `reading-note`
- `HWP`
- `half-note`

## Core Product Direction

The intended split is:

- `reading-note package`
  - owns note structure, explicit links, and note-graph primitives
- `HWP package / protocol repo`
  - owns cognition generation, latent relation discovery, and path-level analysis
- `Half Note app`
  - owns UI, interaction, graph rendering, and developer/user workflows

In short:

- explicit note structure belongs in `reading-note`
- AI-discovered latent structure belongs in `HWP`
- visual presentation and interaction belong in `Half Note`

## Module Boundaries

### 1. reading-note

Primary responsibility:

- explicit note-domain model and graphable note relationships

Owns:

- note model
- note parsing
- double-link parsing
- backlink generation
- explicit graph node generation
- explicit graph edge generation
- relation scoring for explicit note-level relationships

Should produce:

- notes
- links
- backlinks
- explicit graph nodes
- explicit graph edges
- explicit relation scores

Should not own:

- latent AI inference
- hidden-connection discovery
- thematic drift reasoning
- UI rendering decisions

### 2. HWP

Primary responsibility:

- cognitive expansion and inferred relation analysis above the explicit note layer

Owns:

- cognition generation
- relation discovery
- implicit/latent connection inference
- topic drift detection
- path analysis
- unfinished-direction generation
- multi-path reasoning outputs

Should produce:

- inferred relations
- latent bridges between notes or clusters
- drift traces
- thematic paths
- candidate clusters
- uncertainty / unfinished markers
- explanation metadata for inferred links

Should not own:

- canonical note storage
- app-specific UI state
- direct graph rendering logic
- primary note parsing rules that belong to `reading-note`

### 3. Half Note

Primary responsibility:

- app UX and presentation of explicit plus inferred structure

Owns:

- note list UI
- double-link panels
- relation-inspection panels
- graph visualization
- node click navigation
- filters/toggles between explicit and inferred edges
- user interaction flows around note exploration

Should consume:

- explicit structures from `reading-note`
- inferred structures from `HWP`

Should not own:

- protocol-core inference rules
- explicit note-domain parsing logic
- duplicate graph-relationship business rules that should live below the UI

## Data-Layer Split

### Explicit Layer

Produced by `reading-note`.

Examples:

- note A links to note B
- note B backlinks note A
- note graph node metadata
- explicit edge strength based on note structure

### Inferred Layer

Produced by `HWP`.

Examples:

- note A and note C may share a hidden conceptual bridge
- a path of thematic drift from one cluster to another
- a latent edge that is not present in direct note links
- a candidate cluster discovered through inferred semantic relation

### Presentation Layer

Consumed and rendered by `Half Note`.

Examples:

- show explicit edges only
- show inferred edges only
- overlay both with separate visual styles
- open a side panel explaining why an inferred edge exists

## Interface Contracts

### reading-note -> Half Note

Recommended outputs:

- `NoteRecord`
- `ExplicitLink`
- `BacklinkRecord`
- `GraphNode`
- `GraphEdge`
- `RelationScore`

The app should be able to render a useful note graph using only this layer.

### HWP -> Half Note

Recommended outputs:

- `InferredRelation`
- `LatentBridge`
- `DriftTrace`
- `ThematicPath`
- `CandidateCluster`
- `InferenceExplanation`
- `InferenceConfidence`

The app should be able to overlay this layer without mutating the underlying note model.

### reading-note -> HWP

Recommended input boundary:

- HWP should consume normalized note content and explicit graph context, not app UI state

Examples:

- note ids
- note titles
- note content or excerpts
- explicit links/backlinks
- graph neighborhood context
- explicit relation scores

This keeps HWP grounded in note-domain structure without tying it to the app.

## Design Rules

1. `reading-note` defines what is explicitly there.
2. `HWP` defines what may be there but is not explicitly linked yet.
3. `Half Note` decides how both should be inspected, compared, and shown.
4. `Half Note` must not become a second business-logic home for note or inference rules.
5. `HWP` must not silently replace explicit note-domain truth from `reading-note`.

## Suggested Development Order

### Step 1. Formalize reading-note outputs

First make the explicit-layer outputs clean and stable.

Priority targets:

- note model
- explicit graph node/edge schema
- relation-score schema
- package-level export surface

### Step 2. Define HWP note-analysis inputs and inferred outputs

Then define the bridge between explicit note structure and cognitive inference.

Priority targets:

- note-analysis request shape
- inferred relation output shape
- drift/path output shape
- explanation/confidence metadata

### Step 3. Make Half Note consume both layers separately

Then wire the app so explicit and inferred structures remain visually and technically distinct.

Priority targets:

- graph overlay model
- explicit vs inferred edge styling
- relation detail panel
- node-click navigation using the normalized graph data

## Recommended Immediate Next Task

The next highest-value implementation task is:

- define the shared TypeScript-facing data contracts between `reading-note` and `HWP`

That gives the app a clean target and prevents accidental coupling.

## Workspace Mapping

Current preferred paths:

- `reading-note`
  - `/Users/mac/Documents/Halfway-Lab/packages/reading-note`
- location rule:
  - treat the root `packages/` directory as the live package-management area
  - do not treat `protocol/HWP/packages/reading-note` as a parallel active package home
  - `/Users/mac/Documents/Halfway-Lab/packages/reading-note`
- `HWP`
  - `/Users/mac/Documents/Halfway-Lab/protocol/HWP`
- `Half Note`
  - `/Users/mac/Documents/Halfway-Lab/apps/half-note`

## Conclusion

The desired architecture is not:

- one giant app that owns note parsing, AI inference, and graph rendering all at once

It is:

- `reading-note` for explicit note structure
- `HWP` for inferred cognitive structure
- `Half Note` for interaction and visualization

That is the cleanest next-phase development shape for the current workspace.
