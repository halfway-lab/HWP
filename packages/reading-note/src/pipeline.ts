import {
  HwpRoundRecord,
  ReadingNoteProcessOptions,
  ReadingNoteGraphResult,
  ReadingNoteInput,
  ReadingNoteOutput,
} from "./types";
import {
  buildHwpNoteAnalysisInput,
  buildReadingNoteGraph,
  deriveReadingNoteOutput,
  runHwpChain,
} from "./hwp";

export function processReadingNoteFromRounds(
  input: ReadingNoteInput,
  rounds: HwpRoundRecord[]
): ReadingNoteOutput {
  return deriveReadingNoteOutput(input, rounds);
}

export function processReadingNoteGraphFromRounds(
  input: ReadingNoteInput,
  rounds: HwpRoundRecord[]
): ReadingNoteGraphResult {
  const output = processReadingNoteFromRounds(input, rounds);
  const graph = buildReadingNoteGraph(input, output);

  return {
    note: graph.notes[0],
    graph,
    analysisInput: buildHwpNoteAnalysisInput(graph),
  };
}

export async function processReadingNote(
  input: ReadingNoteInput,
  options?: ReadingNoteProcessOptions
): Promise<ReadingNoteOutput> {
  const rounds = options?.hwpRunner
    ? await options.hwpRunner.run(input)
    : await runHwpChain(input);
  return processReadingNoteFromRounds(input, rounds);
}

export async function processReadingNoteGraph(
  input: ReadingNoteInput,
  options?: ReadingNoteProcessOptions
): Promise<ReadingNoteGraphResult> {
  const rounds = options?.hwpRunner
    ? await options.hwpRunner.run(input)
    : await runHwpChain(input);
  return processReadingNoteGraphFromRounds(input, rounds);
}
