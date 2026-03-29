import { ReadingNoteInput, ReadingNoteOutput } from "./types";
import { deriveReadingNoteOutput, runHwpChain } from "./hwp";

export async function processReadingNote(
  input: ReadingNoteInput
): Promise<ReadingNoteOutput> {
  const rounds = await runHwpChain(input);
  return deriveReadingNoteOutput(input, rounds);
}
