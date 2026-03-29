export type Feeling = "resonance" | "question" | "insight" | null;

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
