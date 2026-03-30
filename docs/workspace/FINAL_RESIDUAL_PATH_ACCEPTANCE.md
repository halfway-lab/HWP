# Final Residual Path Acceptance

## Goal

Record which remaining old-path references are now acceptable to keep during the observation period, and which categories would still justify future cleanup.

The old paths most often referenced are:

- `/Users/mac/Documents/HWP`
- `/Users/mac/Documents/HWP Packages`

## Final Assessment

At this stage, the remaining references to old paths are no longer concentrated in active runtime defaults or front-door daily-work guidance.

The high-risk categories have already been addressed:

- canonical protocol path has moved to `/Users/mac/Documents/Halfway-Lab/protocol/HWP`
- active workspace entry docs point to the new canonical path
- active demo defaults point to the new canonical path
- active demo adapters no longer keep `/Users/mac/Documents/HWP` as a hardcoded fallback

That means the remaining references are mostly documentation context, not operational drift.

## Residual Categories

### Acceptable To Keep During Observation

These references are acceptable for now:

- fallback/retirement-policy docs
  - `OLD_HWP_OBSERVATION_AND_RETIREMENT_PLAN.md`
  - `LEGACY_PATH_RETIREMENT_STRATEGY.md`
  - `HWP_PROTOCOL_CUTOVER_CHECKLIST.md`
- cutover/observation docs that explicitly describe the old path as fallback
- historical migration records
  - `WORKSPACE_REORG_PLAN.md`
  - `PHASED_MIGRATION_CHECKLIST.md`
  - copied project-status records under `docs/workspace/project-status/`
- app reference notes that intentionally mention the old path as fallback
  - `apps/half-note/docs/PROTOCOL_REFERENCE.md`

Why these are acceptable:

- they describe migration history, fallback policy, or rollback behavior
- they do not instruct developers to begin new work from the old path
- they do not currently drive the active toolchain back to the old path by default

### Acceptable But Potentially Nice To Clean Later

These references are lower priority and can be cleaned later if desired:

- copied historical project-status files that still describe the pre-cutover layout in detail
- migration notes that preserve old package/demo/app locations for auditability
- app/docs notes that mention the old protocol path only as observation fallback

These are documentation-polish tasks, not blockers.

### No Longer High-Risk

The following categories are no longer considered high-risk:

- active demo adapter path defaults
- active demo live/replay example defaults
- canonical protocol repo README and current-path docs
- active workspace root guidance

## Working Rule

From this point on, treat any remaining old-path reference as a problem only if it does one of these:

1. tells developers to begin new work from the old path
2. makes active tooling prefer the old path by default
3. creates ambiguity about which repo is canonical today

If a remaining reference does none of those, it is acceptable to leave it in place during the current observation window.

## Conclusion

The remaining old-path references are now mostly acceptable historical or fallback-context references.

This means the workspace has crossed from:

- active cutover cleanup

to:

- observation-period maintenance and eventual retirement cleanup

## Related Documents

- `docs/workspace/OBSERVATION_RESIDUAL_PATH_AUDIT.md`
- `docs/workspace/OLD_HWP_OBSERVATION_AND_RETIREMENT_PLAN.md`
- `docs/workspace/LEGACY_PATH_RETIREMENT_STRATEGY.md`
