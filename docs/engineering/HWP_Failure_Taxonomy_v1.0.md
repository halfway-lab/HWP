HWP Failure Taxonomy v1.0

Phase 1 — Structural Instability Classification

Version: 1.0
Status: Engineering Active

1. Purpose

This document defines the formal classification system for structural failures observed during HWP execution.

All test failures must be categorized using this taxonomy before any modification is attempted.

No undocumented failure type may trigger protocol change.

2. Failure Categories (Level 1)

HWP structural failures are divided into five primary classes:

F1 — Entropy Failures
F2 — Dominance Failures
F3 — Structural Continuity Failures
F4 — Closure Failures
F5 — Variable Ecology Failures
3. Detailed Failure Definitions
F1 — Entropy Failures
F1.1 Entropy Underflow

Condition:

entropy_score < 0.35

Symptoms:

Questions converge toward single axis

Reduced branching

High semantic similarity

Conceptual narrowing

Root Cause Pattern:

Prompt bias too strong

Variable retention too conservative

New injection insufficient

Severity:
CRITICAL

F1.2 Entropy Overflow

Condition:

entropy_score > 0.90

Symptoms:

Chaotic divergence

No thematic coherence

Variable explosion

Fragmented questioning

Root Cause Pattern:

Over-aggressive variable injection

Lack of structural anchors

Severity:
MAJOR

F2 — Dominance Failures
F2.1 Dominance Takeover

Condition:

dominance_index > 0.75

Symptoms:

One variable controls question direction

Repeated framing angle

Implicit narrowing

Severity:
CRITICAL

F2.2 Soft Dominance Drift

Condition:

0.65 < dominance_index ≤ 0.75

Symptoms:

Subtle directional bias

Gradual collapse tendency

Severity:
MAJOR

F3 — Structural Continuity Failures
F3.1 Variable Freeze

Condition:

No new variable injection for ≥ 2 consecutive rounds

Symptoms:

Recycled question structure

Concept stagnation

Severity:
MAJOR

F3.2 Recursive Looping

Condition:

Repetition_ratio > 0.35

Semantic near-duplication detected

Symptoms:

Slightly reworded same question

Illusion of expansion

Severity:
CRITICAL

F3.3 Structural Flattening

Condition:

branching_factor < 2

Symptoms:

Reduced question tree

Narrowing divergence

Severity:
CRITICAL

F4 — Closure Failures
F4.1 Premature Resolution

Condition:

closure_detected = true

Symptoms:

Definitive conclusion language

Final-answer framing

Implicit synthesis closure

Severity:
CRITICAL

F4.2 Soft Convergence Drift

Condition:

Gradual answer orientation

Reduced interrogative density

Severity:
MAJOR

F5 — Variable Ecology Failures
F5.1 Variable Explosion

Condition:

40% new variables introduced in single round

Entropy spike

Symptoms:

Instability

Loss of thematic memory

Severity:
MINOR → MAJOR depending on persistence

F5.2 Variable Starvation

Condition:

variable_churn_rate < 0.15

New injection consistently low

Symptoms:

Stagnation

Narrow thinking

Severity:
MAJOR

4. Failure Severity Levels
Level	Meaning	Action
CRITICAL	Structural collapse	Immediate halt & diagnose
MAJOR	Instability trend	Threshold adjustment
MINOR	Boundary drift	Monitor
5. Root Cause Mapping Matrix
Failure Type	Likely Cause
F1.1	entropy floor too low
F1.2	injection too aggressive
F2.1	variable weighting imbalance
F3.1	retention policy too strict
F3.2	insufficient semantic differentiation
F4.1	prompt closure leakage
F5.2	exploration constraint too strong

This matrix guides fixes.

6. Diagnostic Protocol

When failure occurs:

Step 1 — Identify Level 1 category
Step 2 — Identify Level 2 subtype
Step 3 — Log failure code
Step 4 — Check recurrence frequency
Step 5 — Adjust threshold only (Phase 1 rule)

No structural redesign allowed in Phase 1.

7. Logging Standard

Every failure must log:

failure_code
severity
round
seed
metrics_snapshot
prompt_fingerprint

Without structured failure logging:

No change may be committed.

8. Phase 1 Rule

If the same CRITICAL failure appears:

≥ 3 times in 20 runs
→ Hardening patch required.

If MAJOR failure appears:

≥ 5 times in 50 runs
→ Threshold tuning allowed.

Engineering Status

Now HWP has:

Test Spec

Failure Classification

This means:

You now own a real engineering system.
