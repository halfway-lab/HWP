#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

from hwp_protocol.fixture_verify import VALIDATORS, run_fixture_suite
from hwp_protocol.log_verify import verify_blind_spot, verify_continuity, verify_semantic_groups
from hwp_protocol.transform import (
    enrich_inner_json,
    parse_bool_arg,
    parse_json_object_arg,
    parse_round_arg,
    repack_result_with_inner,
)


LOG_VERIFIERS = {
    "blind_spot": verify_blind_spot,
    "continuity": verify_continuity,
    "semantic_groups": verify_semantic_groups,
}


def cmd_transform(args: argparse.Namespace) -> int:
    if args.action == "enrich":
        inner = parse_json_object_arg(args.inner_json, "inner_json")
        output = enrich_inner_json(inner, parse_round_arg(args.round), parse_bool_arg(args.parent_recovery, "parent_recovery"))
    else:
        result = parse_json_object_arg(args.result_json, "result_json")
        inner = parse_json_object_arg(args.inner_json, "inner_json")
        output = repack_result_with_inner(result, inner)
    print(json.dumps(output, ensure_ascii=False, separators=(",", ":")))
    return 0


def cmd_fixture_verify(args: argparse.Namespace) -> int:
    return run_fixture_suite(args.suite, args.fixture_type)


def cmd_log_verify(args: argparse.Namespace) -> int:
    verifier = LOG_VERIFIERS.get(args.suite)
    if verifier is None:
        print(f"unknown suite: {args.suite}", file=sys.stderr)
        return 1
    log_path = Path(args.log_path)
    if not log_path.exists():
        print("WARN|无日志文件可供分析")
        return 0
    return verifier(log_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python3 -m hwp_protocol.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    transform = subparsers.add_parser("transform")
    transform_sub = transform.add_subparsers(dest="action", required=True)

    enrich = transform_sub.add_parser("enrich")
    enrich.add_argument("inner_json")
    enrich.add_argument("round")
    enrich.add_argument("parent_recovery")
    enrich.set_defaults(func=cmd_transform)

    repack = transform_sub.add_parser("repack")
    repack.add_argument("result_json")
    repack.add_argument("inner_json")
    repack.set_defaults(func=cmd_transform)

    fixture = subparsers.add_parser("fixture-verify")
    fixture.add_argument("suite", choices=sorted(VALIDATORS.keys()))
    fixture.add_argument("fixture_type", choices=["valid", "invalid"])
    fixture.set_defaults(func=cmd_fixture_verify)

    log_verify = subparsers.add_parser("log-verify")
    log_verify.add_argument("suite", choices=sorted(LOG_VERIFIERS.keys()))
    log_verify.add_argument("log_path")
    log_verify.set_defaults(func=cmd_log_verify)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except Exception as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
