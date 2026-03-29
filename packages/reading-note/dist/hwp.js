"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.buildHwpInputLine = buildHwpInputLine;
exports.resolveHwpRepoPath = resolveHwpRepoPath;
exports.runHwpChain = runHwpChain;
exports.deriveReadingNoteOutput = deriveReadingNoteOutput;
const node_child_process_1 = require("node:child_process");
const node_fs_1 = require("node:fs");
const node_os_1 = __importDefault(require("node:os"));
const node_path_1 = __importDefault(require("node:path"));
function execFileAsync(file, args, options) {
    return new Promise((resolve, reject) => {
        (0, node_child_process_1.execFile)(file, args, { ...options, encoding: "utf8" }, (error, stdout, stderr) => {
            if (error) {
                const details = [stderr, stdout].filter(Boolean).join("\n").trim();
                reject(new Error(details ? `HWP runner failed: ${details}` : `HWP runner failed: ${error.message}`));
                return;
            }
            resolve({ stdout, stderr });
        });
    });
}
function oneLine(value) {
    return value.replace(/\s+/g, " ").trim();
}
function uniqueNonEmpty(values) {
    const seen = new Set();
    const result = [];
    for (const value of values) {
        const normalized = value ? oneLine(value) : "";
        if (!normalized || seen.has(normalized)) {
            continue;
        }
        seen.add(normalized);
        result.push(normalized);
    }
    return result;
}
function trimSentence(value) {
    return oneLine(value).replace(/[。！？!?]+$/u, "");
}
function cleanFragment(value) {
    return trimSentence(value)
        .replace(/^[“"'`]+|[”"'`]+$/gu, "")
        .replace(/[“”"'`]/gu, "")
        .replace(/^(中|里|上|下|与|和|及)\s*/u, "")
        .replace(/\s+/g, " ")
        .trim();
}
function shortenClause(value, maxLength = 28) {
    const normalized = cleanFragment(value);
    if (!normalized) {
        return "";
    }
    const splitters = ["：", "；", "，", ",", " - ", " — ", " vs. ", " vs ", ":"];
    for (const splitter of splitters) {
        const [head] = normalized.split(splitter);
        if (head && head.length >= 4 && head.length <= maxLength) {
            return head;
        }
    }
    return normalized.length <= maxLength ? normalized : normalized.slice(0, maxLength).trimEnd();
}
function stripLeadingQuestionWords(value) {
    return cleanFragment(value)
        .replace(/^(为什么|如何|是否|什么|哪些|谁|何时|哪里|在什么条件下|若)\s*/u, "")
        .replace(/[？?]+$/u, "");
}
function makePoint(label, value, maxLength = 24) {
    const compact = shortenClause(value, maxLength);
    return compact ? `${label}：${compact}` : "";
}
function pickTagCandidates(values) {
    const preferredWords = ["环境", "选择", "关系", "影响", "限制", "能动", "反抗", "塑造", "语境", "结构"];
    const scored = values
        .map((value) => humanizeTag(value))
        .filter(Boolean)
        .sort((left, right) => {
        const leftPreferred = preferredWords.findIndex((word) => left.includes(word));
        const rightPreferred = preferredWords.findIndex((word) => right.includes(word));
        if (leftPreferred !== rightPreferred) {
            return (leftPreferred === -1 ? 999 : leftPreferred) - (rightPreferred === -1 ? 999 : rightPreferred);
        }
        return left.length - right.length;
    });
    const picked = [];
    for (const value of scored) {
        if (picked.some((item) => item.includes(value) || value.includes(item))) {
            continue;
        }
        picked.push(value);
        if (picked.length === 3) {
            break;
        }
    }
    return picked;
}
function humanizeTag(value) {
    return trimSentence(value).replace(/[_-]+/g, " ");
}
function getTensionDescription(tension) {
    return typeof tension === "string" ? tension : tension.description || "";
}
function summarizeTension(value) {
    const normalized = trimSentence(value)
        .replace(/\s+vs\.\s+/giu, "与")
        .replace(/\s+vs\s+/giu, "与");
    if (!normalized) {
        return "";
    }
    const match = normalized.match(/^(.+?)之间的(.+)$/u);
    if (match) {
        return `${shortenClause(match[1], 10)}与${shortenClause(match[2], 10)}`;
    }
    return shortenClause(normalized, 22);
}
function summarizeQuestion(value) {
    const normalized = stripLeadingQuestionWords(value)
        .replace(/^这句话/u, "")
        .replace(/^历史记录中/u, "")
        .replace(/^与历史记录的关联/u, "和历史记录的关联");
    const compact = shortenClause(normalized, 20);
    if (!compact ||
        compact.length < 6 ||
        ["历史记录的关联", "和历史记录的关联", "与历史记录的关联"].includes(compact)) {
        return "";
    }
    return compact;
}
function summarizeHook(value) {
    return shortenClause(trimSentence(value).replace(/^(若|如果|当|在|把|从|继续看|继续追问|进一步看)\s*/u, ""), 20);
}
function summarizeBlindSpot(value) {
    const compact = shortenClause(cleanFragment(value)
        .replace(/^输入文本提到了/u, "")
        .replace(/^从/u, "")
        .replace(/的推论链$/u, "")
        .replace(/^与/u, ""), 24);
    if (!compact || compact.length < 8) {
        return "";
    }
    return compact;
}
function choosePrimaryQuestion(questions) {
    const candidates = questions
        .map((item) => summarizeQuestion(item))
        .filter((item) => item.length >= 6)
        .sort((left, right) => left.length - right.length);
    return candidates[0] || "";
}
function severityRank(value) {
    switch (value) {
        case "critical":
            return 4;
        case "high":
            return 3;
        case "medium":
            return 2;
        case "low":
            return 1;
        default:
            return 0;
    }
}
async function pathExists(targetPath) {
    try {
        await node_fs_1.promises.access(targetPath);
        return true;
    }
    catch {
        return false;
    }
}
async function isHwpRepoRoot(candidate) {
    const runScript = node_path_1.default.join(candidate, "runs", "run_sequential.sh");
    const specFile = node_path_1.default.join(candidate, "spec", "hwp_turn_prompt.txt");
    return (await pathExists(runScript)) && (await pathExists(specFile));
}
function ancestorCandidates(startPath, maxDepth = 5) {
    const resolved = node_path_1.default.resolve(startPath);
    const candidates = [];
    let current = resolved;
    for (let depth = 0; depth <= maxDepth; depth += 1) {
        candidates.push(current);
        const parent = node_path_1.default.dirname(current);
        if (parent === current) {
            break;
        }
        current = parent;
    }
    return candidates;
}
function buildHwpInputLine(input) {
    const history = input.history && input.history.length > 0 ? input.history.join(" | ") : "无";
    const feeling = input.feeling ?? "无";
    const context = input.context?.trim() || "无";
    return [
        "TASK=reading_note",
        "LANGUAGE=zh-CN",
        `TEXT=${oneLine(input.text)}`,
        `HISTORY=${oneLine(history)}`,
        `FEELING=${oneLine(feeling)}`,
        `CONTEXT=${oneLine(context)}`,
        "INSTRUCTION=请按 HWP 协议持续展开，不要给最终答案；问题、变量、路径、张力尽量使用中文；重点围绕句子理解、关键观点、与历史记录的关联和可能的盲点。",
    ].join(" ; ");
}
async function resolveHwpRepoPath() {
    const envRepoPath = process.env.HWP_REPO_PATH;
    const candidates = envRepoPath
        ? [envRepoPath]
        : uniqueNonEmpty([
            ...ancestorCandidates(process.cwd(), 5),
            ...ancestorCandidates(__dirname, 6),
            node_path_1.default.resolve(process.cwd(), "../HWP"),
            node_path_1.default.resolve(process.cwd(), "../../HWP"),
            node_path_1.default.resolve(process.cwd(), "../../../HWP"),
        ]);
    for (const candidate of candidates) {
        if (await isHwpRepoRoot(candidate)) {
            return candidate;
        }
    }
    throw new Error("HWP repository not found. Set HWP_REPO_PATH to your local halfway-lab/HWP checkout.");
}
function parseHwpLog(logText) {
    return logText
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean)
        .map((line) => {
        const outer = JSON.parse(line);
        const innerText = outer.payloads?.[0]?.text;
        if (!innerText) {
            throw new Error("HWP log entry did not include payload text");
        }
        return JSON.parse(innerText);
    });
}
function findNewLogFile(filesBefore, filesAfter, logDir) {
    const added = filesAfter.filter((file) => !filesBefore.has(file)).sort().reverse();
    if (added.length > 0) {
        return node_path_1.default.join(logDir, added[0]);
    }
    return null;
}
async function runHwpChain(input) {
    const repoPath = await resolveHwpRepoPath();
    const inputDir = await node_fs_1.promises.mkdtemp(node_path_1.default.join(node_os_1.default.tmpdir(), "reading-note-hwp-"));
    const inputPath = node_path_1.default.join(inputDir, "input.txt");
    const logDir = node_path_1.default.join(repoPath, "logs");
    const filesBefore = new Set((await node_fs_1.promises.readdir(logDir).catch(() => [])));
    try {
        await node_fs_1.promises.writeFile(inputPath, `${buildHwpInputLine(input)}\n`, "utf8");
        const { stdout, stderr } = await execFileAsync("bash", [node_path_1.default.join(repoPath, "runs", "run_sequential.sh"), inputPath], {
            cwd: repoPath,
            env: {
                ...process.env,
                HWP_ROUND_SLEEP_SEC: process.env.HWP_ROUND_SLEEP_SEC || "0",
            },
        });
        const combinedOutput = `${stdout}\n${stderr}`;
        const sessionMatch = combinedOutput.match(/开始链:\s*([^，,\s]+)/u);
        const sessionId = sessionMatch?.[1];
        const filesAfter = (await node_fs_1.promises.readdir(logDir).catch(() => []));
        const logPath = (sessionId && node_path_1.default.join(logDir, `chain_${sessionId}.jsonl`)) ||
            findNewLogFile(filesBefore, filesAfter, logDir);
        if (!logPath || !(await pathExists(logPath))) {
            throw new Error("HWP runner completed but no chain log was found");
        }
        const logText = await node_fs_1.promises.readFile(logPath, "utf8");
        const rounds = parseHwpLog(logText);
        if (rounds.length === 0) {
            throw new Error("HWP chain log was empty");
        }
        return rounds;
    }
    finally {
        await node_fs_1.promises.rm(inputDir, { recursive: true, force: true });
    }
}
function deriveReadingNoteOutput(input, rounds) {
    const latestFirst = [...rounds].reverse();
    const questions = uniqueNonEmpty(latestFirst.flatMap((round) => round.questions || []));
    const primaryQuestion = choosePrimaryQuestion(questions);
    const tensions = uniqueNonEmpty(latestFirst.flatMap((round) => (round.tensions || []).map(getTensionDescription)));
    const hooks = uniqueNonEmpty(latestFirst.flatMap((round) => (round.paths || []).map((item) => item.continuation_hook)));
    const blindSpotPaths = latestFirst.flatMap((round) => round.paths || []);
    const blindSpotSignals = latestFirst.flatMap((round) => round.blind_spot_signals || []);
    const tags = pickTagCandidates(uniqueNonEmpty(latestFirst.flatMap((round) => round.variables || [])));
    const summaryCore = summarizeTension(tensions[0] || "") ||
        primaryQuestion ||
        shortenClause(input.text, 16);
    const summary = summaryCore ? `这句话在谈${summaryCore}。` : "这句话值得继续展开理解。";
    const tensionPoint = tensions[0] ? `核心张力：${summarizeTension(tensions[0])}` : undefined;
    const conceptPoint = primaryQuestion ? `核心观点：${primaryQuestion}` : undefined;
    const hookPoint = hooks[0] ? `延展路径：${summarizeHook(hooks[0])}` : undefined;
    const points = uniqueNonEmpty([
        conceptPoint,
        conceptPoint && tensionPoint && summaryCore === summarizeTension(tensions[0] || "")
            ? hookPoint
            : tensionPoint,
        hookPoint,
        questions[0] ? makePoint("继续追问", questions[0]) : undefined,
        questions[1] ? makePoint("补充追问", questions[1]) : undefined,
    ])
        .filter((item) => item && !item.endsWith("："))
        .slice(0, 2);
    const strongestSignal = [...blindSpotSignals].sort((left, right) => severityRank(right.severity) - severityRank(left.severity))[0];
    const blindSpotRaw = strongestSignal?.description ||
        blindSpotPaths.find((item) => item.blind_spot?.description)?.blind_spot?.description ||
        latestFirst.map((round) => round.blind_spot_reason).find(Boolean) ||
        "";
    const blindSpot = blindSpotRaw
        ? (() => {
            const compact = blindSpotRaw.startsWith("可能")
                ? summarizeBlindSpot(blindSpotRaw.replace(/^可能/u, ""))
                : summarizeBlindSpot(blindSpotRaw);
            return compact ? `可能${compact}` : "";
        })()
        : "";
    const historySnippet = input.history && input.history.length > 0 ? trimSentence(input.history[0]) : "";
    const connection = historySnippet
        ? `它和“${historySnippet}”能互相印证，都在谈${summaryCore || "环境与选择的关系"}。`
        : "";
    return {
        summary,
        points: points.length > 0 ? points : ["继续追问这句话还遗漏了哪些条件"],
        connection,
        blindSpot,
        tags,
    };
}
