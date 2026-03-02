#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/logs"

ENTROPY_MIN="0.40"
ENTROPY_MAX="0.79"

echo "== Running collapse probe test =="

latest_chain_file() {
  ls -1t "$LOG_DIR"/chain_hwp_*.jsonl 2>/dev/null | head -n 1
}

CHAIN="$(latest_chain_file || true)"
if [[ -z "${CHAIN:-}" ]]; then
  echo "FAIL: No chain_hwp_*.jsonl found under $LOG_DIR"
  exit 1
fi
echo "Latest chain: $CHAIN"

python3 - <<'PY' "$CHAIN" "$ENTROPY_MIN" "$ENTROPY_MAX"
import json, sys

chain_path = sys.argv[1]
entropy_min = float(sys.argv[2])
entropy_max = float(sys.argv[3])

def snip(s: str, n: int = 240) -> str:
    s = s.replace("\n", "\\n")
    return (s[:n] + "...") if len(s) > n else s

def fail(msg: str, snippet: str | None = None, line_no: int | None = None):
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
        for k in ("output", "result"):
            v = parsed.get(k)
            if isinstance(v, dict) and "round" in v:
                out.append(v)
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

        texts = list(iter_payload_texts(obj))
        for t in texts:
            rounds.extend(parse_text_maybe_json(t, i))

if not rounds:
    fail("No round objects found in chain file (neither direct nor extracted from payload text)")

# Round 1 entropy assertion
r1 = next((r for r in rounds if r.get("round") == 1), None)
if not r1:
    fail("No round==1 found after extraction")

entropy = r1.get("entropy_score")
if entropy is None:
    fail("Round1 missing entropy_score field", snippet=json.dumps(r1, ensure_ascii=False))
try:
    entropy_val = float(entropy)
except Exception:
    fail("Round1 entropy_score not numeric", snippet=str(entropy))
if not (entropy_min <= entropy_val <= entropy_max):
    fail(f"Round1 entropy_score out of range [{entropy_min},{entropy_max}]", snippet=str(entropy_val))
print(f"OK: Round1 entropy_score in range [{entropy_min:.2f},{entropy_max:.2f}] ({entropy_val:.2f})")
print("Round 1:", json.dumps(r1, ensure_ascii=False))

# Probe semantics (stable):
# - If any collapse_detected==true occurs, then recovery_applied must appear and must satisfy strong checks.
# - If no collapse occurs, recovery is not required (PASS).
collapse_rounds = [r for r in rounds if r.get("collapse_detected") is True]
if not collapse_rounds:
    print(f"OK: No collapse_detected==true found in {len(rounds)} rounds; recovery not required for this probe run")
    print("============================")
    print("HWP v0.4 HARDENED (Canonical / PROBE): PASS")
    print("============================")
    raise SystemExit(0)

# If collapse occurred, recovery must exist
recovery_round = next((r for r in rounds if r.get("recovery_applied") is True), None)
if not recovery_round:
    fail(f"collapse_detected==true found ({len(collapse_rounds)} rounds) but no recovery_applied==true found in {len(rounds)} rounds")

rr = recovery_round
rr_round = rr.get("round")
print(f"Recovery round ({rr_round}):", json.dumps(rr, ensure_ascii=False))

parent_id = rr.get("parent_id")
if not parent_id:
    fail("Recovery round missing parent_id")

parent = next((r for r in rounds if r.get("node_id") == parent_id), None)
if not parent:
    fail("Parent round for recovery not found", snippet=str(parent_id))

vars_all = rr.get("variables")
kept = rr.get("recovery_kept_variables")
new = rr.get("recovery_new_variables")

if not isinstance(vars_all, list) or not all(isinstance(x, str) for x in vars_all):
    fail("Recovery round variables must be a list[str]")
if not isinstance(kept, list) or not all(isinstance(x, str) for x in kept):
    fail("recovery_kept_variables must be a list[str]")
if not isinstance(new, list) or not all(isinstance(x, str) for x in new):
    fail("recovery_new_variables must be a list[str]")

# 1) variables must materialize as keep + new (prefix + order)
if vars_all != kept + new:
    fail("Recovery variables did not materialize as keep+new (exact order)",
         snippet=json.dumps({"variables_head": vars_all[:12], "kept_head": kept[:12], "new_head": new[:12]}, ensure_ascii=False))

# 2) kept must be a prefix of parent's variables (same order)
pvars = parent.get("variables")
if not isinstance(pvars, list) or not all(isinstance(x, str) for x in pvars):
    fail("Parent variables missing or not list[str]")
if pvars[:len(kept)] != kept:
    fail("recovery_kept_variables is not an exact prefix of parent variables (order mismatch)",
         snippet=json.dumps({"parent_prefix": pvars[:len(kept)], "kept": kept}, ensure_ascii=False))

# 3) shared/drift/novelty must be consistent
total = len(vars_all)
shared_cnt = len(kept)
new_cnt = len(new)
expected_rate = (new_cnt / total) if total else 0.0

def fnum(v, name):
    if v is None:
        fail(f"Missing field: {name}")
    try:
        return float(v)
    except Exception:
        fail(f"Field {name} not numeric", snippet=str(v))

novelty_rate = fnum(rr.get("novelty_rate"), "novelty_rate")
drift_rate = fnum(rr.get("drift_rate"), "drift_rate")
svc = rr.get("shared_variable_count")
if svc is None:
    fail("Missing field: shared_variable_count")
try:
    svc_int = int(svc)
except Exception:
    fail("shared_variable_count not int", snippet=str(svc))

eps = 1e-9
if svc_int != shared_cnt:
    fail("shared_variable_count != len(recovery_kept_variables)", snippet=f"{svc_int} vs {shared_cnt}")
if abs(novelty_rate - expected_rate) > eps:
    fail("novelty_rate inconsistent with new/total", snippet=f"{novelty_rate} vs {expected_rate}")
if abs(drift_rate - expected_rate) > eps:
    fail("drift_rate inconsistent with new/total", snippet=f"{drift_rate} vs {expected_rate}")

print("OK: Strong recovery checks passed (collapse occurred)")
print("============================")
print("HWP v0.4 HARDENED (Canonical / PROBE): PASS")
print("============================")
PY
