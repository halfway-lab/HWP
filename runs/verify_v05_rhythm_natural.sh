#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/logs"

echo "== Running v0.5.3 rhythm NATURAL (hint-aware) =="

latest_chain_file() {
  ls -1t "$LOG_DIR"/chain_hwp_*.jsonl 2>/dev/null | head -n 1
}

CHAIN="${1:-}"
if [[ -z "${CHAIN}" ]]; then
  CHAIN="$(latest_chain_file || true)"
fi
if [[ -z "${CHAIN:-}" || ! -f "$CHAIN" ]]; then
  echo "FAIL: chain file not found. Usage: bash runs/verify_v05_rhythm_natural.sh [path/to/chain.jsonl]"
  exit 1
fi
echo "Latest chain: $CHAIN"

python3 - <<'PY' "$CHAIN"
import json, sys
chain_path = sys.argv[1]

def snip(s: str, n: int = 260) -> str:
    s = s.replace("\n", "\\n")
    return (s[:n] + "...") if len(s) > n else s

def fail(msg: str, snippet=None, line_no=None):
    print(f"FAIL: {msg}")
    if line_no is not None:
        print(f"  at line: {line_no}")
    if snippet:
        print(f"  snippet: {snip(snippet)}")
    raise SystemExit(1)

def iter_payload_texts(obj):
    if isinstance(obj, dict):
        res = obj.get("result")
        if isinstance(res, dict):
            payloads = res.get("payloads")
            if isinstance(payloads, list):
                for p in payloads:
                    if isinstance(p, dict) and isinstance(p.get("text"), str):
                        yield p["text"]
        payloads = obj.get("payloads")
        if isinstance(payloads, list):
            for p in payloads:
                if isinstance(p, dict) and isinstance(p.get("text"), str):
                    yield p["text"]

def harvest_rounds_from_parsed(parsed):
    out = []
    if isinstance(parsed, dict):
        if "round" in parsed:
            out.append(parsed)
        for k in ("rounds", "items", "nodes", "events", "data"):
            v = parsed.get(k)
            if isinstance(v, list):
                for it in v:
                    if isinstance(it, dict) and "round" in it:
                        out.append(it)
    elif isinstance(parsed, list):
        for it in parsed:
            if isinstance(it, dict) and "round" in it:
                out.append(it)
    return out

def parse_text_maybe_json(text: str, line_no: int):
    t = text.strip()
    if not t:
        return []
    if "<400" in t or "DataInspectionFailed" in t:
        fail("Provider returned non-JSON error response (in payload text)", snippet=t, line_no=line_no)
    try:
        parsed = json.loads(t)
    except Exception:
        return []
    return harvest_rounds_from_parsed(parsed)

def num(x, name):
    if x is None:
        fail(f"Missing numeric field: {name}")
    try:
        return float(x)
    except Exception:
        fail(f"Non-numeric field: {name}", snippet=str(x))

def deep_equal(a, b):
    return json.dumps(a, sort_keys=True, ensure_ascii=False) == json.dumps(b, sort_keys=True, ensure_ascii=False)

rounds = []
with open(chain_path, "r", encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        raw = line.strip()
        if not raw:
            continue
        if "<400" in raw or "DataInspectionFailed" in raw:
            fail("Provider returned non-JSON error response (raw line)", snippet=raw, line_no=i)
        try:
            obj = json.loads(raw)
        except Exception:
            fail("Non-JSON line encountered in chain file", snippet=raw, line_no=i)

        if isinstance(obj, dict) and "round" in obj:
            rounds.append(obj)
            continue

        for t in iter_payload_texts(obj):
            rounds.extend(parse_text_maybe_json(t, i))

if not rounds:
    fail("No round objects found in chain file")

# Require a complete chain with exactly one round object per expected round.
expected_rounds = list(range(1, 9))
round_map = {}
for r in rounds:
    rd_raw = r.get("round")
    if rd_raw is None:
        continue
    try:
        rd = int(rd_raw)
    except Exception:
        fail("Invalid round field", snippet=str(rd_raw))

    if rd in round_map:
        fail("Duplicate round object found in chain", snippet=f"round={rd}")
    round_map[rd] = r

if sorted(round_map.keys()) != expected_rounds:
    fail("Expected exactly rounds 1..8", snippet=f"found={sorted(round_map.keys())}")

rounds = [round_map[rd] for rd in expected_rounds]

valid_modes = {"Rg0","Rg1","Rg2"}
mode_seq = []

for r in rounds:
    sm = r.get("speed_metrics") or {}
    sm_mode = sm.get("mode")
    if sm_mode not in valid_modes:
        fail("Missing/invalid speed_metrics.mode", snippet=json.dumps(sm, ensure_ascii=False))

    rhythm = r.get("rhythm")
    if not isinstance(rhythm, dict):
        fail("Missing rhythm object (v0.6 required)", snippet=json.dumps(r, ensure_ascii=False))

    mode = rhythm.get("mode")
    if mode not in valid_modes:
        fail("Invalid rhythm.mode", snippet=str(mode))

    if sm_mode != mode:
        fail("speed_metrics.mode must equal rhythm.mode", snippet=f"speed={sm_mode}, rhythm={mode}")

    vars_all = r.get("variables")
    if not isinstance(vars_all, list):
        fail("variables must be an array", snippet=json.dumps(r, ensure_ascii=False))
    svc = r.get("shared_variable_count")
    if not isinstance(svc, int) or svc < 0 or svc > len(vars_all):
        fail("shared_variable_count out of valid range", snippet=f"shared={svc}, total={len(vars_all)}")

    hint = rhythm.get("hint")
    if hint is None:
        fail("Missing rhythm.hint (v0.5.3 required)", snippet=json.dumps(rhythm, ensure_ascii=False))
    if rhythm.get("hint_applied") is not True:
        fail("rhythm.hint_applied must be true (v0.5.3 required)", snippet=json.dumps(rhythm, ensure_ascii=False))
    if not isinstance(hint, dict):
        fail("rhythm.hint must be an object", snippet=json.dumps(hint, ensure_ascii=False))

    hmode = hint.get("mode")
    if hmode not in valid_modes:
        fail("Invalid hint.mode", snippet=str(hmode))
    if mode != hmode:
        fail("rhythm.mode must follow hint.mode", snippet=f"hint={hmode}, rhythm={mode}")

    ret = rhythm.get("entropy_target")
    het = hint.get("entropy_target")
    if not isinstance(het, dict):
        fail("hint.entropy_target missing/invalid", snippet=json.dumps(hint, ensure_ascii=False))
    if not isinstance(ret, dict):
        fail("rhythm.entropy_target missing/invalid", snippet=json.dumps(rhythm, ensure_ascii=False))
    if not deep_equal(ret, het):
        fail("rhythm.entropy_target must equal hint.entropy_target (exact)", snippet=json.dumps({"rhythm":ret,"hint":het}, ensure_ascii=False))

    rvp = rhythm.get("variable_policy")
    hvp = hint.get("variable_policy")
    if not isinstance(hvp, dict):
        fail("hint.variable_policy missing/invalid", snippet=json.dumps(hint, ensure_ascii=False))
    if not isinstance(rvp, dict):
        fail("rhythm.variable_policy missing/invalid", snippet=json.dumps(rhythm, ensure_ascii=False))
    if not deep_equal(rvp, hvp):
        fail("rhythm.variable_policy must equal hint.variable_policy (exact)", snippet=json.dumps({"rhythm":rvp,"hint":hvp}, ensure_ascii=False))

    et_min = num(ret.get("min"), "rhythm.entropy_target.min")
    et_max = num(ret.get("max"), "rhythm.entropy_target.max")
    entropy = num(r.get("entropy_score"), "entropy_score")
    if not (et_min <= entropy <= et_max):
        fail("entropy_score not within rhythm.entropy_target", snippet=f"entropy={entropy}, target=[{et_min},{et_max}]")

    if not isinstance(rvp, dict):
        fail("Missing rhythm.variable_policy")
    if rvp.get("keep_prefix") is not True:
        fail("rhythm.variable_policy.keep_prefix must be true", snippet=json.dumps(rvp, ensure_ascii=False))

    mode_seq.append(mode)

switches = sum(1 for i in range(1, len(mode_seq)) if mode_seq[i] != mode_seq[i-1])
if switches > 6:
    fail("Mode flapping too frequent for natural (switches > 6)", snippet=str(mode_seq))

# Recovery strict if present
recovery_round = next((r for r in rounds if r.get("recovery_applied") is True), None)
if recovery_round:
    rr = recovery_round
    parent_id = rr.get("parent_id")
    if not parent_id:
        fail("Recovery round missing parent_id")
    parent = next((r for r in rounds if r.get("node_id") == parent_id), None)
    if not parent:
        fail("Parent round for recovery not found", snippet=str(parent_id))

    vars_all = rr.get("variables")
    kept = rr.get("recovery_kept_variables")
    new = rr.get("recovery_new_variables")
    if vars_all != kept + new:
        fail("Recovery variables did not materialize as keep+new (exact order)")
    pvars = parent.get("variables")
    if pvars[:len(kept)] != kept:
        fail("recovery_kept_variables is not exact prefix of parent variables")

    total = len(vars_all)
    expected_rate = (len(new) / total) if total else 0.0
    eps = 1e-9
    if int(rr.get("shared_variable_count")) != len(kept):
        fail("shared_variable_count mismatch")
    if abs(float(rr.get("novelty_rate")) - expected_rate) > eps:
        fail("novelty_rate mismatch")
    if abs(float(rr.get("drift_rate")) - expected_rate) > eps:
        fail("drift_rate mismatch")
    print("OK: Strong recovery checks passed (natural)")
else:
    print(f"OK: No recovery_applied==true found in {len(rounds)} rounds (natural allows this)")

print("============================")
print("HWP v0.5.3 RHYTHM (NATURAL): PASS")
print("============================")
PY
