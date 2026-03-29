import { ReadingNoteInput, ReadingNoteOutput } from "./types";
interface HwpPath {
    continuation_hook?: string;
    blind_spot?: {
        description?: string;
        impact?: string;
    };
}
interface HwpBlindSpotSignal {
    type?: string;
    description?: string;
    severity?: string;
}
interface HwpTension {
    description?: string;
}
interface HwpRound {
    questions?: string[];
    variables?: string[];
    paths?: HwpPath[];
    tensions?: Array<string | HwpTension>;
    blind_spot_signals?: HwpBlindSpotSignal[];
    blind_spot_reason?: string;
}
export declare function buildHwpInputLine(input: ReadingNoteInput): string;
export declare function resolveHwpRepoPath(): Promise<string>;
export declare function runHwpChain(input: ReadingNoteInput): Promise<HwpRound[]>;
export declare function deriveReadingNoteOutput(input: ReadingNoteInput, rounds: HwpRound[]): ReadingNoteOutput;
export {};
