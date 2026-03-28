#!/usr/bin/env bash
# Legacy helper entrypoint kept for backward compatibility.
# The current recommended interface is `bash runs/run_sequential.sh inputs/*.txt`
# or `python3 -m hwp_protocol.cli ...`.
set -euo pipefail

BASE="$HOME/hwp-tests"
INPUT="${1:-}"

if [ -z "$INPUT" ]; then
  echo "Usage: $0 \"your input text\""
  exit 1
fi

TMP_INPUT="$(mktemp)"
echo "$INPUT" > "$TMP_INPUT"

# Run one-chain sequential test (8 rounds) using the standard runner
bash "$BASE/runs/run_sequential.sh" "$TMP_INPUT" >/dev/null

rm -f "$TMP_INPUT"

# Print last round inner JSON of latest chain
LATEST=$(ls -t "$BASE/logs"/chain_hwp_*.jsonl | head -n 1)
LAST_LINE=$(tail -n 1 "$LATEST")
echo "$LAST_LINE" | jq -r '.payloads[0].text'
