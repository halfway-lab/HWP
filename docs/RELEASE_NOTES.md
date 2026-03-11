# HWP Release Notes

## v0.6 (Current)

### Version
- Name: **HWP v0.6 — RHYTHM_HINT Verification Hardening**
- Goal: Make v0.6 baseline **consistent, observable, and strict-pass/fail verifiable** across runner, verifier, and prompt spec.

### What changed
1) **Version alignment**
- Unified project/runtime labels to `v0.6` in README, verifier outputs, runner annotations, and prompt heading.

2) **Verifier hardening (NATURAL + PROBE)**
- Enforce exactly one round object for each expected round `1..8`.
- Reject duplicate rounds deterministically.
- Add node-chain integrity checks (`node_id` uniqueness and `parent_id` continuity).
- Keep strict checks for `rhythm.hint` mirroring (`mode`, `entropy_target`, `variable_policy`) and `hint_applied == true`.

3) **Runner ergonomics**
- Added env-based controls in runner: `HWP_ROUNDS_PER_CHAIN` and `HWP_ROUND_SLEEP_SEC`.

4) **Probe/Natural contract clarity**
- Verifier messages now consistently describe `v0.6` requirement scope.
- Prompt section title updated to match runner-injected hint contract version.

### Acceptance
This release is considered stable when:
- `bash runs/verify_v05_rhythm_probe.sh <chain.jsonl>` returns **PASS**
- `bash runs/verify_v05_rhythm_natural.sh <chain.jsonl>` returns **PASS**

---

## v0.4 Hardened

### Version
- Name: **HWP v0.4 Alpha (Frozen) — Hardened**
- Goal: Make v0.4 a **reproducible, auditable, pass/fail verifiable** minimum loop for:
  **Collapse → Recovery → Post-Recovery Stabilization → Resume**

### What changed (Hardened)
#### 1) Variables hard bounds
- `variables` MUST be **15–30**.
- If more than 30 candidates exist, MUST prune to 30 before output.

#### 2) Round-1 special case
When `parent_id == null` (Round 1):
- `shared_variable_count = 0`
- `drift_rate = 0`
- `novelty_rate = 1`
- `collapse_detected = false`
- `recovery_applied = false`
- `speed_metrics.mode = Rg0`

#### 3) Hardened collapse rules (deterministic)
`collapse_detected` MUST be set by rule (not arbitrary).
Primary triggers include:
- `drift_rate >= 0.70`
- `entropy_score >= 0.80 AND drift_rate >= 0.30`
- `novelty_rate <= 0.12 AND drift_rate >= 0.30`
- sustained drift (>=0.50) across consecutive rounds

#### 4) Recovery is enforced continuity (keep20)
If `recovery_applied == true`:
- MUST reuse **>= 20** items from `parent_variables_json` (keep list)
- MUST generate **<= 10** new variables
- `variables` MUST begin with the exact keep list (verbatim, same order)
- shared/drift MUST be consistent with keep+total (30)

#### 5) Post-Recovery Stabilization Window (critical)
If `parent_recovery_applied == true` (from Meta):
- MUST keep **>= 20** parent variables even if `collapse_detected == false`
- MUST generate <= 10 new variables to reach total 30
- Ensures `shared_variable_count >= 20` and `drift_rate <= 0.34`

#### 6) Audit keys for recovery (only on recovery rounds)
When `recovery_applied == true`, output:
- `recovery_kept_variables` (array)
- `recovery_new_variables` (array)

Do NOT output these keys when `recovery_applied == false`.

### Acceptance
This release is considered stable when:
- `runs/verify_v04_hardened.sh` returns **PASS**
