import assert from "node:assert/strict";
import { chmodSync, mkdirSync, mkdtempSync, readFileSync, realpathSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  processReadingNote,
  processReadingNoteFromRounds,
  processReadingNoteGraph,
  processReadingNoteGraphFromRounds,
} from "../src";
import { ReadingNoteHwpRunner } from "../src/types";
import {
  buildHwpInputLine,
  buildHwpNoteAnalysisInput,
  buildReadingNoteGraph,
  createDefaultReadingNoteHwpRunner,
  deriveReadingNoteOutput,
  runHwpChain,
  resolveHwpRepoPath,
} from "../src/hwp";

function createFakeHwpRepo(): string {
  const repoPath = mkdtempSync(path.join(os.tmpdir(), "fake-hwp-repo-"));
  mkdirSync(path.join(repoPath, "runs"), { recursive: true });
  mkdirSync(path.join(repoPath, "logs"), { recursive: true });
  mkdirSync(path.join(repoPath, "spec"), { recursive: true });

  writeFileSync(path.join(repoPath, "spec", "hwp_turn_prompt.txt"), "PROMPT_FINGERPRINT: fake\n");

  const round1 = JSON.stringify({
    payloads: [
      {
        text: JSON.stringify({
          round: 1,
          questions: ["这句话如何影响人的选择？"],
          variables: ["环境塑造", "情境判断", "主动性"],
          paths: [
            {
              continuation_hook: "继续看环境怎样改变人的决策边界",
              blind_spot: {
                description: "忽略人的主动调整能力",
              },
            },
          ],
          tensions: [{ description: "环境塑造 vs 主动选择" }],
          blind_spot_signals: [
            {
              type: "assumption_conflict",
              description: "把人完全看成被环境推着走",
              severity: "high",
            },
          ],
        }),
      },
    ],
  });
  const round2 = JSON.stringify({
    payloads: [
      {
        text: JSON.stringify({
          round: 2,
          questions: ["过去经验会不会放大这种环境影响？", "人在什么条件下能反过来塑造环境？"],
          variables: ["环境塑造", "过往经验", "行动空间"],
          paths: [
            {
              continuation_hook: "把当前句子和过往记录放在一起比较",
              blind_spot: {
                description: "没有区分不同环境对人的作用强度",
              },
            },
          ],
          tensions: [{ description: "环境塑造 vs 主动选择" }],
          blind_spot_reason: "把环境影响说得太满，可能遮住人的能动性",
        }),
      },
    ],
  });

  const script = `#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
INPUT_FILE="\${@: -1}"
line="$(cat "$INPUT_FILE")"
session_id="hwp_fake_123"
echo "$line" > "$ROOT_DIR/received_input.txt"
cat > "$ROOT_DIR/logs/chain_\${session_id}.jsonl" <<'EOF'
${round1}
${round2}
EOF
printf '开始链: %s，输入: %s\n' "$session_id" "$line"
`;

  writeFileSync(path.join(repoPath, "runs", "run_sequential.sh"), script);
  chmodSync(path.join(repoPath, "runs", "run_sequential.sh"), 0o755);

  return repoPath;
}

async function testProcessReadingNoteThroughHwp() {
  const fakeRepo = createFakeHwpRepo();
  const previousRepo = process.env.HWP_REPO_PATH;
  process.env.HWP_REPO_PATH = fakeRepo;

  try {
    const result = await processReadingNote({
      text: "人是被环境塑造的",
      history: ["选择往往受环境影响"],
      feeling: "insight",
      context: "在读书会里看到这句话",
    });

    assert.deepEqual(result, {
      summary: "这句话在谈环境塑造与主动选择。",
      points: ["核心观点：如何影响人的选择", "延展路径：当前句子和过往记录放在一起比较"],
      connection: "它和“选择往往受环境影响”能互相印证，都在谈环境塑造与主动选择。",
      blindSpot: "可能把人完全看成被环境推着走",
      tags: ["环境塑造", "主动性", "过往经验"],
    });

    const receivedInput = readFileSync(path.join(fakeRepo, "received_input.txt"), "utf8");
    assert.match(receivedInput, /TASK=reading_note/);
    assert.match(receivedInput, /TEXT=人是被环境塑造的/);
    assert.match(receivedInput, /HISTORY=选择往往受环境影响/);
    assert.doesNotMatch(receivedInput, /\n.*TEXT=/);
    assert.ok(result.summary.length <= 18);
    assert.ok(result.points.every((item) => item.length <= 32));
    assert.ok(result.tags.every((item) => item.length <= 8));
    assert.notEqual(result.points[0], result.points[1]);
  } finally {
    if (previousRepo) {
      process.env.HWP_REPO_PATH = previousRepo;
    } else {
      delete process.env.HWP_REPO_PATH;
    }
    rmSync(fakeRepo, { recursive: true, force: true });
  }
}

async function testRunHwpChainReturnsStableRoundsInterface() {
  const fakeRepo = createFakeHwpRepo();
  const previousRepo = process.env.HWP_REPO_PATH;
  process.env.HWP_REPO_PATH = fakeRepo;

  try {
    const rounds = await runHwpChain({
      text: "人是被环境塑造的",
      history: ["选择往往受环境影响"],
      feeling: "insight",
    });

    assert.equal(rounds.length, 2);
    assert.match(rounds[0].questions?.[0] || "", /如何影响人的选择/);
    assert.match(rounds[1].blind_spot_reason || "", /把环境影响说得太满/);
  } finally {
    if (previousRepo) {
      process.env.HWP_REPO_PATH = previousRepo;
    } else {
      delete process.env.HWP_REPO_PATH;
    }
    rmSync(fakeRepo, { recursive: true, force: true });
  }
}

async function testProcessReadingNoteSupportsInjectedRunner() {
  const injectedRunner: ReadingNoteHwpRunner = {
    async run() {
      return [
        {
          questions: ["这句话如何影响人的选择？"],
          variables: ["环境塑造", "主动性"],
          paths: [{ continuation_hook: "继续比较历史记录和当前句子" }],
          tensions: [{ description: "环境塑造 vs 主动选择" }],
        },
      ];
    },
  };

  const result = await processReadingNote(
    {
      text: "人是被环境塑造的",
      history: ["选择往往受环境影响"],
      feeling: "insight",
    },
    { hwpRunner: injectedRunner }
  );

  assert.equal(result.summary, "这句话在谈环境塑造与主动选择。");
}

function testProcessReadingNoteFromRounds() {
  const rounds = [
    {
      questions: ["这句话如何影响人的选择？"],
      variables: ["环境塑造", "主动性"],
      paths: [{ continuation_hook: "继续比较历史记录和当前句子" }],
      tensions: [{ description: "环境塑造 vs 主动选择" }],
    },
  ];

  const result = processReadingNoteFromRounds(
    {
      text: "人是被环境塑造的",
      history: ["选择往往受环境影响"],
      feeling: "insight",
    },
    rounds
  );

  assert.deepEqual(result, {
    summary: "这句话在谈环境塑造与主动选择。",
    points: ["核心观点：如何影响人的选择", "延展路径：继续比较历史记录和当前句子"],
    connection: "它和“选择往往受环境影响”能互相印证，都在谈环境塑造与主动选择。",
    blindSpot: "",
    tags: ["环境塑造", "主动性"],
  });
}

async function testProcessReadingNoteGraphSupportsInjectedRunner() {
  const injectedRunner: ReadingNoteHwpRunner = {
    async run() {
      return [
        {
          questions: ["这句话如何影响人的选择？"],
          variables: ["环境塑造", "主动性"],
          paths: [{ continuation_hook: "继续比较历史记录和当前句子" }],
          tensions: [{ description: "环境塑造 vs 主动选择" }],
        },
      ];
    },
  };

  const result = await processReadingNoteGraph(
    {
      text: "人是被环境塑造的",
      history: ["选择往往受环境影响"],
      feeling: "insight",
    },
    { hwpRunner: injectedRunner }
  );

  assert.equal(result.graph.notes.length, 2);
  assert.equal(result.analysisInput.focusNoteIds[0], result.note.id);
}

function testProcessReadingNoteGraphFromRounds() {
  const rounds = [
    {
      questions: ["这句话如何影响人的选择？"],
      variables: ["环境塑造", "主动性"],
      paths: [{ continuation_hook: "继续比较历史记录和当前句子" }],
      tensions: [{ description: "环境塑造 vs 主动选择" }],
    },
  ];

  const result = processReadingNoteGraphFromRounds(
    {
      text: "人是被环境塑造的",
      history: ["选择往往受环境影响"],
      feeling: "insight",
    },
    rounds
  );

  assert.equal(result.graph.notes.length, 2);
  assert.equal(result.note.id, result.analysisInput.focusNoteIds[0]);
  assert.equal(result.note.excerpt, "这句话在谈环境塑造与主动选择。");
  assert.deepEqual(result.analysisInput.contextWindow?.historyNoteIds, [result.graph.notes[1].id]);
}

async function testMissingHwpRepo() {
  const previousRepo = process.env.HWP_REPO_PATH;
  process.env.HWP_REPO_PATH = path.join(os.tmpdir(), "missing-hwp-repo");

  try {
    await assert.rejects(
      () => processReadingNote({ text: "test" }),
      /HWP repository not found/
    );
  } finally {
    if (previousRepo) {
      process.env.HWP_REPO_PATH = previousRepo;
    } else {
      delete process.env.HWP_REPO_PATH;
    }
  }
}

async function testResolveHwpRepoPathFromWorkspacePackage() {
  const previousRepo = process.env.HWP_REPO_PATH;
  const originalCwd = process.cwd();
  const packageDir = path.resolve(__dirname, "..");

  delete process.env.HWP_REPO_PATH;
  process.chdir(packageDir);

  try {
    const resolved = await resolveHwpRepoPath();
    assert.equal(resolved, path.resolve(packageDir, "../.."));
  } finally {
    process.chdir(originalCwd);
    if (previousRepo) {
      process.env.HWP_REPO_PATH = previousRepo;
    } else {
      delete process.env.HWP_REPO_PATH;
    }
  }
}

async function testResolveHwpRepoPathFromMonorepoPackageShape() {
  const fakeMonorepoRoot = mkdtempSync(path.join(os.tmpdir(), "fake-hwp-monorepo-"));
  const packageDir = path.join(fakeMonorepoRoot, "packages", "reading-note");
  const previousRepo = process.env.HWP_REPO_PATH;
  const originalCwd = process.cwd();

  mkdirSync(packageDir, { recursive: true });
  mkdirSync(path.join(fakeMonorepoRoot, "runs"), { recursive: true });
  mkdirSync(path.join(fakeMonorepoRoot, "spec"), { recursive: true });
  writeFileSync(path.join(fakeMonorepoRoot, "spec", "hwp_turn_prompt.txt"), "PROMPT_FINGERPRINT: fake\n");
  writeFileSync(path.join(fakeMonorepoRoot, "runs", "run_sequential.sh"), "#!/usr/bin/env bash\n");

  delete process.env.HWP_REPO_PATH;
  process.chdir(packageDir);

  try {
    const resolved = await resolveHwpRepoPath();
    assert.equal(realpathSync(resolved), realpathSync(fakeMonorepoRoot));
  } finally {
    process.chdir(originalCwd);
    if (previousRepo) {
      process.env.HWP_REPO_PATH = previousRepo;
    } else {
      delete process.env.HWP_REPO_PATH;
    }
    rmSync(fakeMonorepoRoot, { recursive: true, force: true });
  }
}

function testAvoidBrokenFragments() {
  const result = deriveReadingNoteOutput(
    {
      text: "人是被环境塑造的",
      history: ["选择往往受环境影响"],
    },
    [
      {
        questions: ["与历史记录的关联？", "历史记录中？", "个体能如何反抗环境设定？"],
        tensions: ["'个体能动性'的宣称与持续拉扯"],
        paths: [{ continuation_hook: "若引入神经可塑性作为环境塑造的生理中介" }],
        blind_spot_signals: [
          {
            description: "'与历史记录的关联'",
            severity: "high",
          },
        ],
        variables: ["环境塑造", "环境叙事竞争", "环境反馈循环"],
      },
    ]
  );

  assert.equal(result.summary, "这句话在谈个体能动性的宣称与持续拉扯。");
  assert.deepEqual(result.points, [
    "核心观点：个体能如何反抗环境设定",
    "延展路径：引入神经可塑性作为环境塑造的生理中介",
  ]);
  assert.equal(result.connection, "它和“选择往往受环境影响”能互相印证，都在谈个体能动性的宣称与持续拉扯。");
  assert.equal(result.blindSpot, "");
}

function testSanitizeStructuredInputLine() {
  const line = buildHwpInputLine({
    text: "A ; CONTEXT=evil",
    history: ["x | y", "k ; FEELING=bad"],
    feeling: "insight",
    context: "z ; HISTORY=oops",
  });

  assert.match(line, /^TASK=reading_note ; LANGUAGE=zh-CN ; TEXT=/);
  assert.match(line, /TEXT=A；CONTEXT=evil/);
  assert.match(line, /HISTORY=x｜y｜k；FEELING=bad/);
  assert.match(line, /CONTEXT=z；HISTORY=oops/);
  assert.doesNotMatch(line, /TEXT=.* ; CONTEXT=evil/);
  assert.doesNotMatch(line, /HISTORY=.* ; FEELING=bad/);
  assert.equal((line.match(/ ; /g) || []).length, 6);
}

function testBuildReadingNoteGraph() {
  const output = deriveReadingNoteOutput(
    {
      text: "人是被环境塑造的",
      history: ["选择往往受环境影响"],
      feeling: "insight",
    },
    [
      {
        questions: ["这句话如何影响人的选择？"],
        variables: ["环境塑造", "主动性"],
        paths: [{ continuation_hook: "继续比较历史记录和当前句子" }],
        tensions: [{ description: "环境塑造 vs 主动选择" }],
      },
    ]
  );

  const graph = buildReadingNoteGraph(
    {
      text: "人是被环境塑造的",
      history: ["选择往往受环境影响"],
      feeling: "insight",
    },
    output
  );

  assert.equal(graph.notes.length, 2);
  assert.equal(graph.links.length, 1);
  assert.equal(graph.edges.length, 1);
  assert.equal(graph.nodes[0]?.id, graph.notes[0]?.id);
  assert.equal(graph.relationScores[0]?.relationId, graph.links[0]?.id);

  const analysisInput = buildHwpNoteAnalysisInput(graph);
  assert.deepEqual(analysisInput.focusNoteIds, [graph.notes[0].id]);
  assert.deepEqual(analysisInput.contextWindow?.historyNoteIds, [graph.notes[1].id]);
  assert.deepEqual(analysisInput.contextWindow?.neighborNoteIds, [graph.notes[1].id]);
  assert.match(graph.notes[0].id, /^note-.*-[a-z0-9]{6}$/);
  assert.match(graph.notes[1].id, /^history-.*-\d+-[a-z0-9]{6}$/);
}

function testBuildHwpNoteAnalysisInputCollectsIncomingNeighbors() {
  const focusNoteId = "note-focus";
  const graph = {
    notes: [
      { id: focusNoteId, title: "Focus", body: "Focus", tags: [] },
      { id: "note-a", title: "A", body: "A", tags: [] },
      { id: "note-b", title: "B", body: "B", tags: [] },
    ],
    links: [
      {
        id: "link-a",
        sourceNoteId: "note-a",
        targetNoteId: focusNoteId,
        direction: "forward" as const,
      },
      {
        id: "link-b",
        sourceNoteId: focusNoteId,
        targetNoteId: "note-b",
        direction: "forward" as const,
      },
    ],
    backlinks: [],
    relationScores: [],
    nodes: [],
    edges: [],
  };

  const analysisInput = buildHwpNoteAnalysisInput(graph);
  assert.deepEqual(analysisInput.contextWindow?.neighborNoteIds, ["note-a", "note-b"]);
}

async function testProcessReadingNoteGraph() {
  const fakeRepo = createFakeHwpRepo();
  const previousRepo = process.env.HWP_REPO_PATH;
  process.env.HWP_REPO_PATH = fakeRepo;

  try {
    const result = await processReadingNoteGraph({
      text: "人是被环境塑造的",
      history: ["选择往往受环境影响"],
      feeling: "insight",
    });

    assert.equal(result.graph.notes.length, 2);
    assert.equal(result.analysisInput.graph.nodes.length, 2);
    assert.equal(result.note.id, result.analysisInput.focusNoteIds[0]);
  } finally {
    if (previousRepo) {
      process.env.HWP_REPO_PATH = previousRepo;
    } else {
      delete process.env.HWP_REPO_PATH;
    }
    rmSync(fakeRepo, { recursive: true, force: true });
  }
}

function testCreateDefaultReadingNoteHwpRunnerShape() {
  const runner = createDefaultReadingNoteHwpRunner();
  assert.equal(typeof runner.run, "function");
}

function testRootExportSurfaceIsStable() {
  // Keep the local source entrypoint aligned with the published root export surface.
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const rootExports = Object.keys(require("../src")).sort();
  assert.deepEqual(rootExports, [
    "buildHwpNoteAnalysisInput",
    "buildReadingNoteGraph",
    "createDefaultReadingNoteHwpRunner",
    "processReadingNote",
    "processReadingNoteFromRounds",
    "processReadingNoteGraph",
    "processReadingNoteGraphFromRounds",
  ]);
}

async function run() {
  await testProcessReadingNoteThroughHwp();
  await testRunHwpChainReturnsStableRoundsInterface();
  await testProcessReadingNoteSupportsInjectedRunner();
  testProcessReadingNoteFromRounds();
  await testProcessReadingNoteGraphSupportsInjectedRunner();
  testProcessReadingNoteGraphFromRounds();
  await testMissingHwpRepo();
  await testResolveHwpRepoPathFromWorkspacePackage();
  await testResolveHwpRepoPathFromMonorepoPackageShape();
  testAvoidBrokenFragments();
  testSanitizeStructuredInputLine();
  testBuildReadingNoteGraph();
  testBuildHwpNoteAnalysisInputCollectsIncomingNeighbors();
  testCreateDefaultReadingNoteHwpRunnerShape();
  testRootExportSurfaceIsStable();
  await testProcessReadingNoteGraph();
  console.log("reading-note tests passed");
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});
