import { HwpRoundRecord, ReadingNoteProcessOptions, ReadingNoteGraphResult, ReadingNoteInput, ReadingNoteOutput } from "./types";
export declare function processReadingNoteFromRounds(input: ReadingNoteInput, rounds: HwpRoundRecord[]): ReadingNoteOutput;
export declare function processReadingNoteGraphFromRounds(input: ReadingNoteInput, rounds: HwpRoundRecord[]): ReadingNoteGraphResult;
export declare function processReadingNote(input: ReadingNoteInput, options?: ReadingNoteProcessOptions): Promise<ReadingNoteOutput>;
export declare function processReadingNoteGraph(input: ReadingNoteInput, options?: ReadingNoteProcessOptions): Promise<ReadingNoteGraphResult>;
