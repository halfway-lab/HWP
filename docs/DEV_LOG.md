# HWP Development Log

## Current Snapshot

- Canonical protocol source repo confirmed
- Provider abstraction and live adapter support added
- Benchmark automation established
- v0.6 replay baseline passing
- v0.6 live targeted regression passing after retry hardening

## Recent Important Changes

- Added pluggable provider setup and adapter workflow
- Enabled OpenAI-compatible and Ollama adapter paths
- Hardened live provider env export and adapter invocation
- Added benchmark reporting, regression reporting, and session-based log collection
- Tightened semantic group prompt guidance
- Added bounded retry/backoff for long-batch live provider calls
- Added workspace reorganization planning docs and migration templates

## Open Engineering Themes

- Continue observing long-batch live stability on real providers
- Keep protocol source-of-truth boundaries clear across downstream copies
- Prepare phased workspace reorganization without breaking path assumptions

## Migration Reminder

- This repo is upstream for protocol work.
- Any copied protocol tree should be treated as downstream, not peer source.
