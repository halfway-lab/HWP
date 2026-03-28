# HWP Release Notes

## v0.6 RC2

### Version
- Name: **HWP v0.6 RC2 - Runner Materialization and Local Replay Verification**
- Goal: Materialize v0.6 fields into runner output, harden provider preflight, and make RC2 verifiable even without a live `openclaw` provider.

### What changed
1) **Runner-side v0.6 materialization**
- `runs/run_sequential.sh` now enriches each round with:
  - `blind_spot_signals`
  - `blind_spot_score`
  - `blind_spot_reason`
  - `semantic_groups`
  - `group_count`
  - `cross_domain_contamination`
  - `round_id`
  - `continuity_score`
  - `state_snapshot`
- Enriched inner JSON is written back into `payloads[0].text`, and key fields are projected to the outer log object for verifier compatibility.

2) **Provider preflight hardening**
- Runner startup now fails fast with a clear message when `openclaw` is not available.
- `HWP_AGENT_BIN` can be used to point to a non-default agent binary path.

3) **Replay mode for local end-to-end verification**
- `HWP_REPLAY_CHAIN_PATH` allows the runner to replay an existing chain log round-by-round while preserving the same enrich/repack pipeline.
- This makes RC2 verifiable in environments without a live provider.

4) **Verifier compatibility fix**
- `runs/verify_v06_semantic_groups.sh` now treats only explicit contamination flags as failures, avoiding false positives caused by the field name `cross_domain_contamination`.

5) **Protocol-core Python packaging**
- v0.6 protocol-core helpers are now organized under `hwp_protocol/`.
- `hwp_protocol/cli.py` provides a unified command entrypoint for protocol-core operations.
- `hwp_protocol/transform.py` handles runner-side JSON enrichment and repacking.
- `hwp_protocol/fixture_verify.py` centralizes fixture rule validation across v0.6 verifiers.
- `hwp_protocol/log_verify.py` performs structured JSONL log checks, replacing fragile text-grep validation in the main verifier path.
- Shell entrypoints now invoke these helpers as Python modules (`python3 -m hwp_protocol...`) for stable package resolution.
- Minimal unit coverage now exists in `tests/test_protocol_core.py` for materialization and verifier-core behavior.

### Acceptance
This release is considered stable when:
- `HWP_REPLAY_CHAIN_PATH=<chain.jsonl> HWP_ROUND_SLEEP_SEC=0 bash runs/run_sequential.sh inputs/probe.txt` completes successfully
- `bash runs/verify_v06_all.sh logs` returns **ALL VERIFICATIONS PASSED**
- `python3 -m hwp_protocol.cli --help` exposes the unified protocol-core CLI successfully

## v0.5.3 (Current)

### Version
- Name: **HWP v0.5.3 — RHYTHM_HINT Verification Hardening**
- Goal: Make v0.5.x baseline **consistent, observable, and strict-pass/fail verifiable** across runner, verifier, and prompt spec.

### What changed
1) **Version alignment**
- Unified project/runtime labels to `v0.5.3` in README, verifier outputs, runner annotations, and prompt heading.

2) **NATURAL verifier hardening**
- Enforce exactly one round object for each expected round `1..8`.
- Reject duplicate rounds deterministically.
- Keep strict checks for `rhythm.hint` mirroring (`mode`, `entropy_target`, `variable_policy`) and `hint_applied == true`.

3) **Probe/Natural contract clarity**
- Verifier messages now consistently describe `v0.5.3` requirement scope.
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
