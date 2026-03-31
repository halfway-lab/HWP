#!/usr/bin/env bash
# Legacy helper entrypoint kept for backward compatibility.
# The current recommended interface is `bash runs/run_sequential.sh inputs/*.txt`
# or `python3 -m hwp_protocol.cli ...`.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE="${HWP_REPO_PATH:-$SCRIPT_DIR}"
if [ "$#" -lt 1 ]; then
  echo "Usage: $0 [--config PATH] [--provider-type TYPE] [--provider-name NAME] [--agent-bin PATH] [--agent-cmd CMD] [--replay-chain PATH] \"your input text\""
  echo "Legacy helper: uses repo root at \$HWP_REPO_PATH when set, otherwise the directory containing hwp_cli.sh."
  exit 1
fi

INPUT="${@: -1}"
RUNNER_ARGS=()
if [ "$#" -gt 1 ]; then
  RUNNER_ARGS=("${@:1:$#-1}")
fi

if [ -z "$INPUT" ]; then
  echo "Usage: $0 [--config PATH] [--provider-type TYPE] [--provider-name NAME] [--agent-bin PATH] [--agent-cmd CMD] [--replay-chain PATH] \"your input text\""
  echo "Legacy helper: uses repo root at \$HWP_REPO_PATH when set, otherwise the directory containing hwp_cli.sh."
  exit 1
fi

TMP_INPUT="$(mktemp)"
echo "$INPUT" > "$TMP_INPUT"

# Run one-chain sequential test (8 rounds) using the standard runner
bash "$BASE/runs/run_sequential.sh" "${RUNNER_ARGS[@]}" "$TMP_INPUT" >/dev/null

rm -f "$TMP_INPUT"

# Print last round inner JSON of latest chain
LATEST=$(ls -t "$BASE/logs"/chain_hwp_*.jsonl | head -n 1)
LAST_LINE=$(tail -n 1 "$LATEST")
echo "$LAST_LINE" | jq -r '.payloads[0].text'
