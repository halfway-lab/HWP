import { HwpNoteAnalysisInput, HwpRoundRecord, NoteGraphSnapshot, ReadingNoteHwpRunner, ReadingNoteInput, ReadingNoteOutput } from "./types";
export declare function buildHwpInputLine(input: ReadingNoteInput): string;
export declare function resolveHwpRepoPath(): Promise<string>;
export declare function createDefaultReadingNoteHwpRunner(): ReadingNoteHwpRunner;
export declare function runHwpChain(input: ReadingNoteInput): Promise<HwpRoundRecord[]>;
export declare function deriveReadingNoteOutput(input: ReadingNoteInput, rounds: HwpRoundRecord[]): ReadingNoteOutput;
export declare function buildReadingNoteGraph(input: ReadingNoteInput, output: ReadingNoteOutput): NoteGraphSnapshot;
export declare function buildHwpNoteAnalysisInput(graph: NoteGraphSnapshot): HwpNoteAnalysisInput;
