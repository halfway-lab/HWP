"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.processReadingNote = processReadingNote;
const hwp_1 = require("./hwp");
async function processReadingNote(input) {
    const rounds = await (0, hwp_1.runHwpChain)(input);
    return (0, hwp_1.deriveReadingNoteOutput)(input, rounds);
}
