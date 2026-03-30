# HWP Project Status

## Basic Info

- Project name: HWP
- Current path: `/Users/mac/Documents/HWP`
- Repo type: standalone git repo
- Maintainer role: protocol source repo
- Relationship to HWP: canonical source of truth

## Purpose

- What this project is for:
  - canonical implementation of the HWP protocol
  - source for protocol rules, runners, adapters, verification, and benchmark flow
- Primary users:
  - protocol developers
  - integration developers
  - downstream app/demo maintainers
- Why it exists separately:
  - this is the upstream protocol repo and should remain the main source for protocol changes

## Current Scope

- Main features:
  - protocol core in `hwp_protocol/`
  - prompt/spec definitions in `spec/`
  - runner and verifier scripts in `runs/`
  - provider adapters in `adapters/`
  - benchmark, replay, reports, and docs
- Out-of-scope items:
  - end-user app UX
  - product-specific frontends
- Current maturity:
  - active development

## Entry Points

- Main README: `README.md`
- Main app/server entry: `hwp_server.py`
- Main package entry: `hwp_protocol/cli.py`
- Main test entry:
  - `tests/test_protocol_core.py`
  - `runs/verify_v06_all.sh`
  - `runs/run_benchmarks.sh`

## Directory Notes

- Important directories:
  - `hwp_protocol/`
  - `runs/`
  - `spec/`
  - `tests/`
  - `docs/`
  - `config/`
- Generated directories:
  - `logs/`
  - `reports/`
  - `__pycache__/`
- Sensitive/local-only files:
  - `config/provider.env`
  - local logs and reports

## Environment and Dependencies

- Runtime:
  - Python 3
  - shell runners
- Package manager:
  - `pip`
- Required env files or secrets:
  - provider config for live runs
  - API keys via `config/provider.env` or env vars
- External services/providers:
  - OpenAI-compatible APIs
  - Ollama
  - OpenClaw

## Current Commands

- Install:
  - `pip install -r requirements.txt`
- Dev:
  - `bash runs/run_sequential.sh inputs/probe.txt`
- Build:
  - not primary
- Test:
  - `python3 -m py_compile hwp_protocol/*.py`
  - `bash runs/verify_v06_all.sh <logs_dir>`
- Verify:
  - `bash runs/run_benchmarks.sh`

## Current Risks

- Known issues:
  - long-batch live provider stability still needs continued observation
- Migration risks:
  - many scripts assume current repo-root-relative paths
- Path or config coupling:
  - benchmark/report/log paths are root-relative
  - docs and scripts reference current directory layout

## Next Development Step

- Highest-priority next task:
  - continue stabilizing long-batch live provider behavior
- What should happen right after migration:
  - confirm all runner/spec/test paths still resolve after relocation

## Notes

- Treat this repo as the only protocol source of truth.
- Downstream copies should not become long-term parallel protocol sources.
