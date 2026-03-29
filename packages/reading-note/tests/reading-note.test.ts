import assert from "node:assert/strict";
import { chmodSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { processReadingNote } from "../src";
import { deriveReadingNoteOutput, resolveHwpRepoPath } from "../src/hwp";

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

async function testResolveHwpRepoPathFromMonorepoPackage() {
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

async function run() {
  await testProcessReadingNoteThroughHwp();
  await testMissingHwpRepo();
  await testResolveHwpRepoPathFromMonorepoPackage();
  testAvoidBrokenFragments();
  console.log("reading-note tests passed");
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});
