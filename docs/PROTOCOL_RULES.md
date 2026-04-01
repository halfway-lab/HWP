# HWP v0.6 RC2 — Protocol Rules (Spec Summary)

> **Note**: This document summarizes the core protocol rules. For the authoritative prompt spec, see `spec/hwp_turn_prompt.txt`.

## Output schema (top-level keys)
Required keys:
- node_id, parent_id, round
- questions (3–5)
- variables (15–30)
- paths (>=3, each includes blind_spot + continuation_hook)
- tensions (1–2)
- unfinished (>=3)
- entropy_score, novelty_rate, shared_variable_count, drift_rate
- collapse_detected, recovery_applied
- speed_metrics { mode, unfinished_inherited_count, action_taken[] }

Optional audit keys (ONLY when recovery_applied == true):
- recovery_kept_variables, recovery_new_variables

## Metrics
- variable_count = len(variables)
- shared_variable_count = |Vt ∩ V(t-1)|
- drift_rate = 1 - shared_variable_count / variable_count
- novelty_rate = |Vt \ V(t-1)| / variable_count

## Round-1 special case
If parent_id is null:
- drift_rate MUST be 0
- novelty_rate MUST be 1
- collapse_detected MUST be false
- recovery_applied MUST be false
- mode MUST be Rg0

## Collapse Detection (high sensitivity)
Set collapse_detected = true if ANY holds:
1) variable_count > 30
2) drift_rate >= 0.70
3) entropy_score >= 0.80 AND drift_rate >= 0.30
4) novelty_rate <= 0.12 AND drift_rate >= 0.30
Else collapse_detected = false.

> **Implementation Note**: The condition "drift_rate >= 0.50 for 2 consecutive rounds" from earlier specs is NOT currently implemented in `hwp_protocol/transform.py`.

## Recovery Application
If collapse_detected == true:
- recovery_applied MUST be true
- Execute R_fix:
  - Let P = parent_variables_json
  - keep = first 20 items of P (or all if P < 20)
  - new = generate at most 10 new variables
  - variables MUST begin with keep (verbatim order) then append new
  - prune/dedupe to total 30
  - shared_variable_count MUST equal len(keep)
  - drift_rate MUST equal 1 - shared/30

If collapse_detected == false:
- recovery_applied MUST be false

## Post-Recovery Stabilization Window
If parent_recovery_applied == true:
- MUST keep >= 20 parent variables (same keep rule)
- MUST add <= 10 new variables to reach total 30
- Therefore shared_variable_count MUST be >= 20 and drift_rate MUST be <= 0.34

## speed_metrics.mode selection (override-first)
- If collapse_detected == true => mode = Rg0
- Else if parent_recovery_applied == true => mode = Rg0
- Else if drift_rate < 0.30 => mode = Rg1
- Else if drift_rate > 0.70 => mode = Rg2
- Else => mode = Rg0

## Entropy Target Bands (per mode)
- Rg0 (Normal): entropy_target = [0.40, 0.79]
- Rg1 (Stable): entropy_target = [0.55, 0.85]
- Rg2 (Explore): entropy_target = [0.35, 0.65]

See `spec/hwp_turn_prompt.txt` lines 189-192 for authoritative definition.
