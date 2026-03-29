# @halfway-lab/reading-note

A reading-note package backed by the local HWP protocol runner.

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

## HWP Setup

This package expects a local checkout of `https://github.com/halfway-lab/HWP` and runs the HWP chain runner directly.

If you are using this package outside the `HWP` monorepo, set `HWP_REPO_PATH` explicitly.
If you are using it from `HWP/packages/reading-note`, it can auto-detect the repo root.

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

- The published package ships only `dist/` and `README.md`
- `prepublishOnly` runs build and tests before publish
- Runtime behavior depends on the external local HWP repository, so this package is not a standalone hosted API client
