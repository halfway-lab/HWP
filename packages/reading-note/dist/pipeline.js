"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.processReadingNoteFromRounds = processReadingNoteFromRounds;
exports.processReadingNoteGraphFromRounds = processReadingNoteGraphFromRounds;
exports.processReadingNote = processReadingNote;
exports.processReadingNoteGraph = processReadingNoteGraph;
const hwp_1 = require("./hwp");
function processReadingNoteFromRounds(input, rounds) {
    return (0, hwp_1.deriveReadingNoteOutput)(input, rounds);
}
function processReadingNoteGraphFromRounds(input, rounds) {
    const output = processReadingNoteFromRounds(input, rounds);
    const graph = (0, hwp_1.buildReadingNoteGraph)(input, output);
    return {
        note: graph.notes[0],
        graph,
        analysisInput: (0, hwp_1.buildHwpNoteAnalysisInput)(graph),
    };
}
async function processReadingNote(input, options) {
    const rounds = options?.hwpRunner
        ? await options.hwpRunner.run(input)
        : await (0, hwp_1.runHwpChain)(input);
    return processReadingNoteFromRounds(input, rounds);
}
async function processReadingNoteGraph(input, options) {
    const rounds = options?.hwpRunner
        ? await options.hwpRunner.run(input)
        : await (0, hwp_1.runHwpChain)(input);
    return processReadingNoteGraphFromRounds(input, rounds);
}
