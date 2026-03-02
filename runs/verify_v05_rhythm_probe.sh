#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/logs"

echo "== Running v0.5.1 rhythm PROBE (hint-aware) =="

CHAIN="${1:-}"
if [ -z "$CHAIN" ]; then
  CHAIN="$(ls -1t "$LOG_DIR"/chain_hwp_*.jsonl 2>/dev/null | head -n 1 || true)"
fi

if [ -z "$CHAIN" ] || [ ! -f "$CHAIN" ]; then
  echo "FAIL: No chain file found"
  exit 1
fi

echo "Latest chain: $CHAIN"

python3 - <<'PY' "$CHAIN"
import json, sys, re

p = sys.argv[1]

def fail(msg, snippet=None):
    print(f"FAIL: {msg}")
    if snippet is not None:
        s = str(snippet)
        s = s.replace("\n", " ")
        print(f"  snippet: {s[:280]}")
    raise SystemExit(1)

def deep_equal(a, b):
    return json.dumps(a, sort_keys=True, ensure_ascii=False) == json.dumps(b, sort_keys=True, ensure_ascii=False)

def iter_payload_texts(obj):
    if isinstance(obj, dict):
        res = obj.get("result")
        if isinstance(res, dict):
            payloads = res.get("payloads")
            if isinstance(payloads, list):
                for it in payloads:
                    if isinstance(it, dict) and isinstance(it.get("text"), str):
                        yield it["text"]
        payloads = obj.get("payloads")
        if isinstance(payloads, list):
            for it in payloads:
                if isinstance(it, dict) and isinstance(it.get("text"), str):
                    yield it["text"]

rounds = []

with open(p, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        o = json.loads(line)

        # Some logs may already be inner rounds
        if isinstance(o, dict) and "round" in o:
            rounds.append(o)
            continue

        # Else: unwrap payload.text
        for t in iter_payload_texts(o):
            t = t.strip()
            if not t.startswith("{"):
                continue
            try:
                inner = json.loads(t)
            except Exception:
                continue
            if isinstance(inner, dict) and "round" in inner:
                rounds.append(inner)

if not rounds:
    fail("No round objects found in chain file")

# Sort and require 8 rounds
rounds = sorted(rounds, key=lambda r: int(r.get("round") or 0))
round_nums = sorted({int(r.get("round") or 0) for r in rounds if r.get("round") is not None})
if not round_nums:
    fail("No round numbers found")
if max(round_nums) < 8 or len(round_nums) < 8:
    fail("Incomplete chain: expected 8 rounds", snippet=f"rounds={round_nums}")

# Round1 entropy in range (probe baseline)
r1 = rounds[0]
e1 = r1.get("entropy_score")
if not isinstance(e1, (int, float)):
    fail("Round1 entropy_score missing/invalid", snippet=json.dumps(r1, ensure_ascii=False))
if not (0.40 <= float(e1) <= 0.79):
    fail("Round1 entropy_score out of range [0.40,0.79]", snippet=f"{e1}")
print(f"OK: Round1 entropy_score in range [0.40,0.79] ({float(e1):.2f})")
print("Round 1:", json.dumps(r1, ensure_ascii=False))

valid_modes = {"Rg0","Rg1","Rg2"}

# v0.5.2 requirement: rhythm + hint must exist; hint must match rhythm; rhythm.mode must match speed_metrics.mode
for r in rounds:
    rd = int(r.get("round") or 0)
    sm = r.get("speed_metrics") or {}
    mode = sm.get("mode")
    if mode not in valid_modes:
        fail("Invalid speed_metrics.mode", snippet=json.dumps(sm, ensure_ascii=False))

    rhythm = r.get("rhythm")
    if not isinstance(rhythm, dict):
        fail("Missing rhythm object (v0.5 required)", snippet=json.dumps(r, ensure_ascii=False))

    rmode = rhythm.get("mode")
    if rmode not in valid_modes:
        fail("Invalid rhythm.mode", snippet=json.dumps(rhythm, ensure_ascii=False))

    if mode != rmode:
        fail("Mirror rule violated: rhythm.mode must equal speed_metrics.mode", snippet=f"round={rd} speed={mode} rhythm={rmode}")

    hint = rhythm.get("hint")
    if hint is None:
        fail("Missing rhythm.hint (v0.5.2 required)", snippet=json.dumps(rhythm, ensure_ascii=False))
    if rhythm.get("hint_applied") is not True:
        fail("rhythm.hint_applied must be true (v0.5.2 required)", snippet=json.dumps(rhythm, ensure_ascii=False))
    if not isinstance(hint, dict):
        fail("rhythm.hint must be an object", snippet=json.dumps(hint, ensure_ascii=False))

    hmode = hint.get("mode")
    if hmode not in valid_modes:
        fail("Invalid hint.mode", snippet=str(hmode))
    if hmode != rmode:
        fail("hint.mode must equal rhythm.mode", snippet=f"round={rd} hint={hmode} rhythm={rmode}")

    # entropy target match + containment
    het = hint.get("entropy_target")
    ret = rhythm.get("entropy_target")
    if not isinstance(het, dict) or not isinstance(ret, dict):
        fail("entropy_target missing/invalid", snippet=json.dumps(rhythm, ensure_ascii=False))
    if not deep_equal(het, ret):
        fail("rhythm.entropy_target must equal hint.entropy_target (exact)", snippet=json.dumps({"hint":het,"rhythm":ret}, ensure_ascii=False))

    e = r.get("entropy_score")
    if not isinstance(e, (int, float)):
        fail("entropy_score missing/invalid", snippet=json.dumps(r, ensure_ascii=False))
    mn = float(ret.get("min"))
    mx = float(ret.get("max"))
    if not (mn <= float(e) <= mx):
        fail("entropy_score not within rhythm.entropy_target", snippet=f"round={rd} entropy={e}, target=[{mn},{mx}]")

    # variable_policy match + keep_prefix true
    hvp = hint.get("variable_policy")
    rvp = rhythm.get("variable_policy")
    if not isinstance(hvp, dict) or not isinstance(rvp, dict):
        fail("variable_policy missing/invalid", snippet=json.dumps(rhythm, ensure_ascii=False))
    if not deep_equal(hvp, rvp):
        fail("rhythm.variable_policy must equal hint.variable_policy (exact)", snippet=json.dumps({"hint":hvp,"rhythm":rvp}, ensure_ascii=False))
    if rvp.get("keep_prefix") is not True:
        fail("variable_policy.keep_prefix must be true", snippet=json.dumps(rvp, ensure_ascii=False))

# Probe requirement: must detect collapse at least once OR explicitly allow no-collapse runs?
# For hardened probe, earlier you wanted recovery if collapse detected; but v0.5.2 dynamic controller may not force collapse.
# We'll keep the existing behavior: if no collapse, that's OK (print OK line).
collapse_rounds = [r for r in rounds if r.get("collapse_detected") is True]
if not collapse_rounds:
    print(f"OK: No collapse_detected==true found in {len(rounds)} rounds; recovery not required")
else:
    # If any collapse detected, require at least one recovery_applied==true
    rec_rounds = [r for r in rounds if r.get("recovery_applied") is True]
    if not rec_rounds:
        fail("Collapse detected but no recovery_applied==true found", snippet=json.dumps(collapse_rounds[0], ensure_ascii=False))
    print("OK: Collapse/recovery observed")

print("============================")
print("HWP v0.5.2 RHYTHM (PROBE / dynamic): PASS")
print("============================")
PY
