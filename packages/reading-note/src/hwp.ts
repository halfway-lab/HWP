import { execFile } from "node:child_process";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  BacklinkRecord,
  ExplicitLink,
  GraphEdge,
  GraphNode,
  HwpBlindSpotSignalRecord,
  HwpNoteAnalysisInput,
  HwpPathRecord,
  HwpRoundRecord,
  HwpTensionRecord,
  NoteGraphSnapshot,
  NoteRecord,
  ReadingNoteHwpRunner,
  ReadingNoteInput,
  ReadingNoteOutput,
  RelationScore,
} from "./types";

interface HwpExecutionContext {
  repoPath: string;
  inputPath: string;
  input: ReadingNoteInput;
}

interface HwpExecutionResult {
  rounds: HwpRoundRecord[];
}

interface HwpChainGateway {
  run(context: HwpExecutionContext): Promise<HwpExecutionResult>;
}

function execFileAsync(
  file: string,
  args: string[],
  options: {
    cwd: string;
    env: NodeJS.ProcessEnv;
  }
): Promise<{ stdout: string; stderr: string }> {
  return new Promise((resolve, reject) => {
    execFile(file, args, { ...options, encoding: "utf8" }, (error, stdout, stderr) => {
      if (error) {
        const details = [stderr, stdout].filter(Boolean).join("\n").trim();
        reject(
          new Error(details ? `HWP runner failed: ${details}` : `HWP runner failed: ${error.message}`)
        );
        return;
      }

      resolve({ stdout, stderr });
    });
  });
}

function oneLine(value: string): string {
  return value.replace(/\s+/g, " ").trim();
}

function slugify(value: string): string {
  return oneLine(value)
    .toLowerCase()
    .replace(/[^a-z0-9\u4e00-\u9fa5]+/gu, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 32);
}

function stableSuffix(value: string): string {
  let hash = 0;
  for (const char of value) {
    hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  }
  return hash.toString(36).padStart(6, "0").slice(0, 6);
}

function normalizeHwpValue(value: string): string {
  return oneLine(value)
    .replace(/\s;\s/g, "；")
    .replace(/;/g, "；")
    .replace(/\s\|\s/g, "｜")
    .replace(/\|/g, "｜");
}

function uniqueNonEmpty(values: Array<string | undefined>): string[] {
  const seen = new Set<string>();
  const result: string[] = [];

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

function trimSentence(value: string): string {
  return oneLine(value).replace(/[。！？!?]+$/u, "");
}

function cleanFragment(value: string): string {
  return trimSentence(value)
    .replace(/^[“"'`]+|[”"'`]+$/gu, "")
    .replace(/[“”"'`]/gu, "")
    .replace(/^(中|里|上|下|与|和|及)\s*/u, "")
    .replace(/\s+/g, " ")
    .trim();
}

function shortenClause(value: string, maxLength = 28): string {
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

function stripLeadingQuestionWords(value: string): string {
  return cleanFragment(value)
    .replace(/^(为什么|如何|是否|什么|哪些|谁|何时|哪里|在什么条件下|若)\s*/u, "")
    .replace(/[？?]+$/u, "");
}

function makePoint(label: string, value: string, maxLength = 24): string {
  const compact = shortenClause(value, maxLength);
  return compact ? `${label}：${compact}` : "";
}

function pickTagCandidates(values: string[]): string[] {
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

  const picked: string[] = [];
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

function humanizeTag(value: string): string {
  return trimSentence(value).replace(/[_-]+/g, " ");
}

function getTensionDescription(tension: string | HwpTensionRecord): string {
  return typeof tension === "string" ? tension : tension.description || "";
}

function summarizeTension(value: string): string {
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

function summarizeQuestion(value: string): string {
  const normalized = stripLeadingQuestionWords(value)
    .replace(/^这句话/u, "")
    .replace(/^历史记录中/u, "")
    .replace(/^与历史记录的关联/u, "和历史记录的关联");
  const compact = shortenClause(normalized, 20);
  if (
    !compact ||
    compact.length < 6 ||
    ["历史记录的关联", "和历史记录的关联", "与历史记录的关联"].includes(compact)
  ) {
    return "";
  }
  return compact;
}

function summarizeHook(value: string): string {
  return shortenClause(
    trimSentence(value).replace(/^(若|如果|当|在|把|从|继续看|继续追问|进一步看)\s*/u, ""),
    20
  );
}

function summarizeBlindSpot(value: string): string {
  const compact = shortenClause(
    cleanFragment(value)
      .replace(/^输入文本提到了/u, "")
      .replace(/^从/u, "")
      .replace(/的推论链$/u, "")
      .replace(/^与/u, ""),
    24
  );
  if (!compact || compact.length < 8) {
    return "";
  }
  return compact;
}

function makeNoteId(input: ReadingNoteInput): string {
  const seed = slugify(input.text) || "reading-note";
  const suffix = stableSuffix(
    JSON.stringify({
      text: oneLine(input.text),
      history: (input.history || []).map((item) => oneLine(item)),
      feeling: input.feeling ?? null,
      context: input.context ? oneLine(input.context) : null,
    })
  );
  return `note-${seed}-${suffix}`;
}

function makeHistoryNoteId(historyItem: string, index: number): string {
  const seed = slugify(historyItem) || `history-${index + 1}`;
  const suffix = stableSuffix(`${index}:${oneLine(historyItem)}`);
  return `history-${seed}-${index + 1}-${suffix}`;
}

function collectNeighborNoteIds(graph: NoteGraphSnapshot, focusNoteId: string): string[] {
  const neighborIds = new Set<string>();

  for (const link of graph.links) {
    if (link.sourceNoteId === focusNoteId && link.targetNoteId !== focusNoteId) {
      neighborIds.add(link.targetNoteId);
    }
    if (link.targetNoteId === focusNoteId && link.sourceNoteId !== focusNoteId) {
      neighborIds.add(link.sourceNoteId);
    }
  }

  return [...neighborIds];
}

function choosePrimaryQuestion(questions: string[]): string {
  const candidates = questions
    .map((item) => summarizeQuestion(item))
    .filter((item) => item.length >= 6)
    .sort((left, right) => left.length - right.length);
  return candidates[0] || "";
}

function severityRank(value?: string): number {
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

async function pathExists(targetPath: string): Promise<boolean> {
  try {
    await fs.access(targetPath);
    return true;
  } catch {
    return false;
  }
}

async function isHwpRepoRoot(candidate: string): Promise<boolean> {
  const runScript = path.join(candidate, "runs", "run_sequential.sh");
  const specFile = path.join(candidate, "spec", "hwp_turn_prompt.txt");
  return (await pathExists(runScript)) && (await pathExists(specFile));
}

function ancestorCandidates(startPath: string, maxDepth = 5): string[] {
  const resolved = path.resolve(startPath);
  const candidates: string[] = [];
  let current = resolved;

  for (let depth = 0; depth <= maxDepth; depth += 1) {
    candidates.push(current);
    const parent = path.dirname(current);
    if (parent === current) {
      break;
    }
    current = parent;
  }

  return candidates;
}

function pushCandidate(candidates: string[], candidate: string) {
  const resolved = path.resolve(candidate);
  if (!candidates.includes(resolved)) {
    candidates.push(resolved);
  }
}

function collectHwpRepoCandidates(startPath: string, maxDepth: number, candidates: string[]) {
  for (const ancestor of ancestorCandidates(startPath, maxDepth)) {
    pushCandidate(candidates, ancestor);
    pushCandidate(candidates, path.join(ancestor, "protocol", "HWP"));
    pushCandidate(candidates, path.join(ancestor, "HWP"));
  }
}

export function buildHwpInputLine(input: ReadingNoteInput): string {
  const history = input.history && input.history.length > 0 ? input.history.join(" | ") : "无";
  const feeling = input.feeling ?? "无";
  const context = input.context?.trim() || "无";

  return [
    "TASK=reading_note",
    "LANGUAGE=zh-CN",
    `TEXT=${normalizeHwpValue(input.text)}`,
    `HISTORY=${normalizeHwpValue(history)}`,
    `FEELING=${normalizeHwpValue(feeling)}`,
    `CONTEXT=${normalizeHwpValue(context)}`,
    "INSTRUCTION=请按 HWP 协议持续展开，不要给最终答案；问题、变量、路径、张力尽量使用中文；重点围绕句子理解、关键观点、与历史记录的关联和可能的盲点。",
  ].join(" ; ");
}

export async function resolveHwpRepoPath(): Promise<string> {
  const envRepoPath = process.env.HWP_REPO_PATH;
  const candidates: string[] = [];

  if (envRepoPath) {
    pushCandidate(candidates, envRepoPath);
  } else {
    collectHwpRepoCandidates(process.cwd(), 5, candidates);
    collectHwpRepoCandidates(__dirname, 6, candidates);
    pushCandidate(candidates, path.resolve(process.cwd(), "../HWP"));
    pushCandidate(candidates, path.resolve(process.cwd(), "../../HWP"));
    pushCandidate(candidates, path.resolve(process.cwd(), "../../../HWP"));
    pushCandidate(candidates, path.resolve(process.cwd(), "../../protocol/HWP"));
    pushCandidate(candidates, path.resolve(__dirname, "../../protocol/HWP"));
    pushCandidate(candidates, path.resolve(__dirname, "../../../protocol/HWP"));
  }

  for (const candidate of candidates) {
    if (await isHwpRepoRoot(candidate)) {
      return candidate;
    }
  }

  throw new Error(
    "HWP repository not found. Set HWP_REPO_PATH to your local halfway-lab/HWP checkout."
  );
}

function parseHwpLog(logText: string): HwpRoundRecord[] {
  return logText
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const outer = JSON.parse(line) as { payloads?: Array<{ text?: string }> };
      const innerText = outer.payloads?.[0]?.text;
      if (!innerText) {
        throw new Error("HWP log entry did not include payload text");
      }
      return JSON.parse(innerText) as HwpRoundRecord;
    });
}

function findNewLogFile(filesBefore: Set<string>, filesAfter: string[], logDir: string): string | null {
  const added = filesAfter.filter((file) => !filesBefore.has(file)).sort().reverse();
  if (added.length > 0) {
    return path.join(logDir, added[0]);
  }
  return null;
}

function createLogBackedHwpChainGateway(): HwpChainGateway {
  return {
    async run(context: HwpExecutionContext): Promise<HwpExecutionResult> {
      const logDir = path.join(context.repoPath, "logs");
      const filesBefore = new Set<string>((await fs.readdir(logDir).catch(() => [])) as string[]);

      const { stdout, stderr } = await execFileAsync(
        "bash",
        [path.join(context.repoPath, "runs", "run_sequential.sh"), context.inputPath],
        {
          cwd: context.repoPath,
          env: {
            ...process.env,
            HWP_ROUND_SLEEP_SEC: process.env.HWP_ROUND_SLEEP_SEC || "0",
          },
        }
      );

      const combinedOutput = `${stdout}\n${stderr}`;
      const sessionMatch = combinedOutput.match(/开始链:\s*([^，,\s]+)/u);
      const sessionId = sessionMatch?.[1];
      const filesAfter = (await fs.readdir(logDir).catch(() => [])) as string[];

      const logPath =
        (sessionId && path.join(logDir, `chain_${sessionId}.jsonl`)) ||
        findNewLogFile(filesBefore, filesAfter, logDir);

      if (!logPath || !(await pathExists(logPath))) {
        throw new Error("HWP runner completed but no chain log was found");
      }

      const logText = await fs.readFile(logPath, "utf8");
      const rounds = parseHwpLog(logText);

      if (rounds.length === 0) {
        throw new Error("HWP chain log was empty");
      }

      return { rounds };
    },
  };
}

function createDefaultHwpChainGateway(): HwpChainGateway {
  return createLogBackedHwpChainGateway();
}

export function createDefaultReadingNoteHwpRunner(): ReadingNoteHwpRunner {
  return {
    async run(input: ReadingNoteInput): Promise<HwpRoundRecord[]> {
      return runHwpChain(input);
    },
  };
}

export async function runHwpChain(input: ReadingNoteInput): Promise<HwpRoundRecord[]> {
  const repoPath = await resolveHwpRepoPath();
  const inputDir = await fs.mkdtemp(path.join(os.tmpdir(), "reading-note-hwp-"));
  const inputPath = path.join(inputDir, "input.txt");

  try {
    await fs.writeFile(inputPath, `${buildHwpInputLine(input)}\n`, "utf8");
    const gateway = createDefaultHwpChainGateway();
    const result = await gateway.run({ repoPath, inputPath, input });
    return result.rounds;
  } finally {
    await fs.rm(inputDir, { recursive: true, force: true });
  }
}

export function deriveReadingNoteOutput(
  input: ReadingNoteInput,
  rounds: HwpRoundRecord[]
): ReadingNoteOutput {
  const latestFirst = [...rounds].reverse();
  const questions = uniqueNonEmpty(latestFirst.flatMap((round) => round.questions || []));
  const primaryQuestion = choosePrimaryQuestion(questions);
  const tensions = uniqueNonEmpty(
    latestFirst.flatMap((round) => (round.tensions || []).map(getTensionDescription))
  );
  const hooks = uniqueNonEmpty(
    latestFirst.flatMap((round) => (round.paths || []).map((item) => item.continuation_hook))
  );
  const blindSpotPaths = latestFirst.flatMap((round) => round.paths || []);
  const blindSpotSignals = latestFirst.flatMap((round) => round.blind_spot_signals || []);
  const tags = pickTagCandidates(
    uniqueNonEmpty(latestFirst.flatMap((round) => round.variables || []))
  );

  const summaryCore =
    summarizeTension(tensions[0] || "") ||
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

  const strongestSignal = [...blindSpotSignals].sort(
    (left, right) => severityRank(right.severity) - severityRank(left.severity)
  )[0];
  const blindSpotRaw =
    strongestSignal?.description ||
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

export function buildReadingNoteGraph(
  input: ReadingNoteInput,
  output: ReadingNoteOutput
): NoteGraphSnapshot {
  const focusNoteId = makeNoteId(input);
  const notes: NoteRecord[] = [
    {
      id: focusNoteId,
      title: shortenClause(input.text, 18) || "未命名笔记",
      body: input.text,
      excerpt: output.summary,
      tags: output.tags,
      metadata: {
        feeling: input.feeling ?? null,
        has_connection: Boolean(output.connection),
        has_blind_spot: Boolean(output.blindSpot),
      },
    },
  ];

  const links: ExplicitLink[] = [];
  const backlinks: BacklinkRecord[] = [];
  const relationScores: RelationScore[] = [];

  for (const [index, historyItem] of (input.history || []).entries()) {
    const historyNoteId = makeHistoryNoteId(historyItem, index);
    notes.push({
      id: historyNoteId,
      title: shortenClause(historyItem, 18) || `历史记录 ${index + 1}`,
      body: historyItem,
      excerpt: historyItem,
      tags: output.tags.slice(0, 2),
      metadata: {
        source: "history",
      },
    });

    const linkId = `link-${focusNoteId}-${historyNoteId}`;
    links.push({
      id: linkId,
      sourceNoteId: focusNoteId,
      targetNoteId: historyNoteId,
      direction: "bidirectional",
      label: "history_context",
      contextSnippet: output.connection,
      evidence: output.connection ? [output.connection] : undefined,
    });
    backlinks.push({
      noteId: focusNoteId,
      linkedFromNoteId: historyNoteId,
      contextSnippet: historyItem,
    });
    relationScores.push({
      relationId: linkId,
      score: 0.72,
      basis: "content_overlap",
      rationale: output.connection || "历史记录为当前笔记提供显式上下文。",
    });
  }

  const nodes: GraphNode[] = notes.map((note) => ({
    id: note.id,
    noteId: note.id,
    label: note.title,
    tags: note.tags,
    degree: links.filter(
      (link) => link.sourceNoteId === note.id || link.targetNoteId === note.id
    ).length,
    metadata: note.metadata,
  }));

  const edges: GraphEdge[] = links.map((link) => ({
    id: link.id,
    sourceNodeId: link.sourceNoteId,
    targetNodeId: link.targetNoteId,
    kind: "explicit",
    label: link.label,
    weight: relationScores.find((score) => score.relationId === link.id)?.score,
    relationScoreId: link.id,
  }));

  return {
    notes,
    links,
    backlinks,
    relationScores,
    nodes,
    edges,
  };
}

export function buildHwpNoteAnalysisInput(
  graph: NoteGraphSnapshot
): HwpNoteAnalysisInput {
  const focusNoteIds = graph.notes.length > 0 ? [graph.notes[0].id] : [];
  return {
    graph,
    focusNoteIds,
    contextWindow: focusNoteIds[0]
      ? {
          focusNoteId: focusNoteIds[0],
          neighborNoteIds: collectNeighborNoteIds(graph, focusNoteIds[0]),
          historyNoteIds: graph.notes.slice(1).map((note) => note.id),
          selectedTags: graph.notes[0]?.tags || [],
        }
      : undefined,
    objective: "Analyze explicit note structure before HWP inference overlay.",
    maxInferences: 8,
  };
}
