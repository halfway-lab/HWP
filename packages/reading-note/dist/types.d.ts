export type Feeling = "resonance" | "question" | "insight" | null;
export type NoteId = string;
export type LinkDirection = "forward" | "backward" | "bidirectional";
export type GraphEdgeKind = "explicit" | "inferred";
export type InferenceKind = "inferred_relation" | "latent_bridge" | "drift_trace" | "thematic_path" | "candidate_cluster";
export type InferenceStatus = "candidate" | "supported" | "contested" | "unfinished";
export interface NoteRecord {
    id: NoteId;
    title: string;
    body: string;
    excerpt?: string;
    tags: string[];
    sourcePath?: string;
    createdAt?: string;
    updatedAt?: string;
    metadata?: Record<string, string | number | boolean | null>;
}
export interface ExplicitLink {
    id: string;
    sourceNoteId: NoteId;
    targetNoteId: NoteId;
    direction: LinkDirection;
    label?: string;
    contextSnippet?: string;
    evidence?: string[];
}
export interface BacklinkRecord {
    noteId: NoteId;
    linkedFromNoteId: NoteId;
    contextSnippet?: string;
}
export interface RelationScore {
    relationId: string;
    score: number;
    basis: "explicit_link" | "backlink" | "content_overlap" | "manual" | "hybrid";
    rationale?: string;
}
export interface GraphNode {
    id: NoteId;
    noteId: NoteId;
    label: string;
    tags: string[];
    degree?: number;
    groupId?: string;
    metadata?: Record<string, string | number | boolean | null>;
}
export interface GraphEdge {
    id: string;
    sourceNodeId: string;
    targetNodeId: string;
    kind: GraphEdgeKind;
    label?: string;
    weight?: number;
    relationScoreId?: string;
    metadata?: Record<string, string | number | boolean | null>;
}
export interface NoteGraphSnapshot {
    notes: NoteRecord[];
    links: ExplicitLink[];
    backlinks: BacklinkRecord[];
    relationScores: RelationScore[];
    nodes: GraphNode[];
    edges: GraphEdge[];
}
export interface NoteContextWindow {
    focusNoteId: NoteId;
    neighborNoteIds: NoteId[];
    historyNoteIds?: NoteId[];
    selectedTags?: string[];
}
export interface HwpNoteAnalysisInput {
    graph: NoteGraphSnapshot;
    focusNoteIds: NoteId[];
    contextWindow?: NoteContextWindow;
    objective?: string;
    maxInferences?: number;
}
export interface InferenceExplanation {
    summary: string;
    evidenceNoteIds: NoteId[];
    evidenceLinks?: string[];
    rationaleSteps?: string[];
}
export interface InferenceConfidence {
    score: number;
    status: InferenceStatus;
    uncertainty?: string;
}
export interface InferredRelation {
    id: string;
    kind: "inferred_relation";
    sourceNoteId: NoteId;
    targetNoteId: NoteId;
    label: string;
    explanation: InferenceExplanation;
    confidence: InferenceConfidence;
}
export interface LatentBridge {
    id: string;
    kind: "latent_bridge";
    noteIds: NoteId[];
    bridgeConcept: string;
    explanation: InferenceExplanation;
    confidence: InferenceConfidence;
}
export interface DriftStep {
    fromNoteId: NoteId;
    toNoteId: NoteId;
    pivot: string;
}
export interface DriftTrace {
    id: string;
    kind: "drift_trace";
    startNoteId: NoteId;
    endNoteId: NoteId;
    steps: DriftStep[];
    explanation: InferenceExplanation;
    confidence: InferenceConfidence;
}
export interface ThematicPathStep {
    noteId: NoteId;
    theme: string;
}
export interface ThematicPath {
    id: string;
    kind: "thematic_path";
    steps: ThematicPathStep[];
    explanation: InferenceExplanation;
    confidence: InferenceConfidence;
}
export interface CandidateCluster {
    id: string;
    kind: "candidate_cluster";
    noteIds: NoteId[];
    clusterLabel: string;
    explanation: InferenceExplanation;
    confidence: InferenceConfidence;
}
export type HwpInference = InferredRelation | LatentBridge | DriftTrace | ThematicPath | CandidateCluster;
export interface HwpInferenceBundle {
    focusNoteIds: NoteId[];
    generatedAt: string;
    inferences: HwpInference[];
}
export interface ReadingNoteGraphResult {
    note: NoteRecord;
    graph: NoteGraphSnapshot;
    analysisInput: HwpNoteAnalysisInput;
}
export interface ReadingNoteInput {
    text: string;
    history?: string[];
    feeling?: Feeling;
    context?: string;
}
export interface ReadingNoteOutput {
    summary: string;
    points: string[];
    connection?: string;
    blindSpot?: string;
    tags: string[];
}
export interface HwpPathRecord {
    continuation_hook?: string;
    blind_spot?: {
        description?: string;
        impact?: string;
    };
}
export interface HwpBlindSpotSignalRecord {
    type?: string;
    description?: string;
    severity?: string;
}
export interface HwpTensionRecord {
    description?: string;
}
export interface HwpRoundRecord {
    questions?: string[];
    variables?: string[];
    paths?: HwpPathRecord[];
    tensions?: Array<string | HwpTensionRecord>;
    blind_spot_signals?: HwpBlindSpotSignalRecord[];
    blind_spot_reason?: string;
}
export interface ReadingNoteHwpRunner {
    run(input: ReadingNoteInput): Promise<HwpRoundRecord[]>;
}
export interface ReadingNoteProcessOptions {
    hwpRunner?: ReadingNoteHwpRunner;
}
