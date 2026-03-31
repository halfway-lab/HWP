# @halfway-lab/reading-note

Legacy note: inside the Halfway-Lab workspace, this path is retained only as historical protocol-local context.
Active package ownership lives at `/Users/mac/Documents/Halfway-Lab/packages/reading-note`.

A reading-note package backed by the local HWP protocol runner.

Within the Halfway-Lab workspace, the primary package home is `packages/reading-note`.

## Features

- Transform a sentence into structured understanding
- Extract key points
- Detect connections with past notes
- Generate blind spots
- Auto-tagging

## Usage

```ts
import { processReadingNote } from "@halfway-lab/reading-note";

const result = await processReadingNote({
  text: "People are shaped by environment",
  history: ["Choices are influenced by context"],
  feeling: "insight",
  context: "From a sociology article",
});

console.log(result);
```

The package runs a local HWP chain and then compresses the chain output into a reading-note shape.

## Public API

- `processReadingNote(input, options?)`: run the HWP chain and return the normalized reading-note result
- `processReadingNoteFromRounds(input, rounds)`: build the normalized reading-note result from already available HWP rounds
- `processReadingNoteGraph(input, options?)`: run the HWP chain and return the note, graph snapshot, and HWP analysis input
- `processReadingNoteGraphFromRounds(input, rounds)`: build the note, graph snapshot, and analysis input from already available HWP rounds
- `buildReadingNoteGraph(input, output)`: build a graph snapshot from a note input and normalized reading-note output
- `buildHwpNoteAnalysisInput(graph)`: derive the graph payload used for follow-up HWP analysis
- `createDefaultReadingNoteHwpRunner()`: create the built-in runner that resolves the local HWP repo and uses the current default execution path
- `ReadingNoteHwpRunner`: the stable interface for injecting an external rounds provider
- exported TypeScript types from `src/types.ts` are available from the package root

The package root is the supported import surface. Avoid deep imports such as `@halfway-lab/reading-note/dist/hwp` or workspace-only source imports, because internal execution details may continue changing while the root API stays stable.

## API Stability

This package is intended to be used as a public API.

- The package root export surface is the supported public contract
- `processReadingNoteFromRounds(...)` and `processReadingNoteGraphFromRounds(...)` are the most stable integration points when your app already owns HWP execution
- `processReadingNote(...)` and `processReadingNoteGraph(...)` are supported public APIs for apps that want the package to drive HWP execution
- `ReadingNoteHwpRunner` is the supported extension point for plugging in a custom execution layer
- internal implementation details such as local runner wiring, log parsing, temp-file handling, and repo path resolution are not part of the public contract

In practice, consumers should import only from `@halfway-lab/reading-note` and rely on semver-compatible updates for the root API.

## Versioning

This package follows semantic versioning for its root public API.

- patch releases may update internals, docs, tests, and bug fixes without changing the supported root contract
- minor releases may add new root exports or optional capabilities in a backward-compatible way
- major releases may change or remove public root APIs

If your integration depends on stable behavior, prefer the package root APIs described above and avoid coupling to any workspace-only or deep internal paths.

## Graph Usage

```ts
import {
  buildHwpNoteAnalysisInput,
  processReadingNote,
  processReadingNoteGraph,
} from "@halfway-lab/reading-note";

const input = {
  text: "People are shaped by environment",
  history: ["Choices are influenced by context"],
  feeling: "insight" as const,
};

const note = await processReadingNote(input);
const result = await processReadingNoteGraph({
  ...input,
});

const analysisInput = buildHwpNoteAnalysisInput(result.graph);

console.log(note.summary, result.graph.nodes.length, analysisInput.focusNoteIds);
```

## Injected Runner

`reading-note` now supports a stable injected runner interface. This lets callers such as Half Note provide their own HWP execution layer without depending on the package's current log-backed default runner.

```ts
import type {
  HwpRoundRecord,
  ReadingNoteHwpRunner,
} from "@halfway-lab/reading-note";
import { processReadingNoteGraph } from "@halfway-lab/reading-note";

const halfNoteRunner: ReadingNoteHwpRunner = {
  async run(input): Promise<HwpRoundRecord[]> {
    const response = await fetch("http://your-stable-hwp-endpoint/run-reading-note", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(input),
    });

    if (!response.ok) {
      throw new Error(`HWP request failed: ${response.status}`);
    }

    const data = (await response.json()) as { rounds: HwpRoundRecord[] };
    return data.rounds;
  },
};

const result = await processReadingNoteGraph(
  {
    text: "People are shaped by environment",
    history: ["Choices are influenced by context"],
    feeling: "insight",
  },
  {
    hwpRunner: halfNoteRunner,
  }
);

console.log(result.analysisInput.focusNoteIds);
```

If you do not pass `options.hwpRunner`, the package uses `createDefaultReadingNoteHwpRunner()` internally.

## Pure Post-Processing

If your app already has stable HWP rounds, you can skip runner integration entirely and use the pure post-processing entrypoints.

```ts
import type { HwpRoundRecord } from "@halfway-lab/reading-note";
import {
  processReadingNoteFromRounds,
  processReadingNoteGraphFromRounds,
} from "@halfway-lab/reading-note";

const rounds: HwpRoundRecord[] = [
  {
    questions: ["How does this sentence shape choice?"],
    variables: ["environment shaping", "agency"],
    paths: [{ continuation_hook: "compare the sentence with prior notes" }],
    tensions: [{ description: "环境塑造 vs 主动选择" }],
  },
];

const input = {
  text: "People are shaped by environment",
  history: ["Choices are influenced by context"],
  feeling: "insight" as const,
};

const note = processReadingNoteFromRounds(input, rounds);
const graphResult = processReadingNoteGraphFromRounds(input, rounds);

console.log(note.summary, graphResult.analysisInput.focusNoteIds);
```

## Output

```json
{
  "summary": "",
  "points": [],
  "connection": "",
  "blindSpot": "",
  "tags": []
}
```

## Requirements

- Node.js 20+
- A local checkout of `https://github.com/halfway-lab/HWP`
- A working HWP provider configuration inside that repo
- `bash` available in your runtime environment

## Install

```bash
npm install @halfway-lab/reading-note
```

If you install from GitHub Packages, make sure your npm auth and scope registry are configured for `@halfway-lab`.

## HWP Setup

This package expects a local checkout of `https://github.com/halfway-lab/HWP` and runs the HWP chain runner directly.

Inside the Halfway-Lab workspace, the package can resolve the canonical protocol repo from the workspace layout. Outside that layout, set `HWP_REPO_PATH` explicitly.

Set the HWP repo path:

```bash
export HWP_REPO_PATH=/path/to/HWP
```

Then configure your provider inside that HWP repo, for example via its `config/provider.env` or `HWP_PROVIDER_*` environment variables.

The usual HWP variables are:

```bash
export HWP_PROVIDER_TYPE=openai_compatible
export HWP_PROVIDER_NAME=deepseek
export HWP_LLM_API_KEY=your_key_here
export HWP_LLM_MODEL=your_model_here
```

If the HWP repo cannot be found, the package throws:

```text
HWP repository not found. Set HWP_REPO_PATH to your local halfway-lab/HWP checkout.
```

If the HWP provider is not configured correctly, the error will come from the underlying HWP runner or adapter.

## Build

```bash
npm run build
```

## Test

```bash
npm run test
```

## Publish Notes

- The published package ships `dist/`, `README.md`, `CHANGELOG.md`, `LICENSE`, and `package.json`
- `prepublishOnly` runs build and tests before publish
- Runtime behavior depends on the external local HWP repository, so this package is not a standalone hosted API client
