#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

from hwp_protocol.fixture_verify import VALIDATORS, run_fixture_suite
from hwp_protocol.log_verify import verify_blind_spot, verify_continuity, verify_semantic_groups
from hwp_protocol.note_inference import infer_note_relations
from hwp_protocol.runner import (
    ChainRunner,
    RunnerConfig,
    apply_provider_defaults,
    load_provider_config,
    resolve_provider_alias,
    run_multi_provider,
)
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


def cmd_transform_batch(args: argparse.Namespace) -> int:
    """Batch transform: enrich inner_json then repack into result_json in one call."""
    result = parse_json_object_arg(args.result_json, "result_json")
    inner = parse_json_object_arg(args.inner_json, "inner_json")
    round_num = parse_round_arg(args.round)
    parent_recovery = parse_bool_arg(args.parent_recovery, "parent_recovery")
    
    # Step 1: enrich the inner JSON
    enriched_inner = enrich_inner_json(inner, round_num, parent_recovery)
    
    # Step 2: repack the result with enriched inner
    output = repack_result_with_inner(result, enriched_inner)
    
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


def cmd_note_infer(args: argparse.Namespace) -> int:
    payload = parse_json_object_arg(args.input_json, "input_json")
    output = infer_note_relations(payload)
    print(json.dumps(output, ensure_ascii=False, separators=(",", ":")))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """run 子命令：执行 HWP 链编排"""
    root_dir = Path(__file__).resolve().parent.parent

    # Load provider configuration
    provider_config = load_provider_config(root_dir, args.config_path)

    # Apply CLI overrides
    if args.provider_type:
        provider_config["HWP_PROVIDER_TYPE"] = args.provider_type
    if args.provider_name:
        provider_config["HWP_PROVIDER_NAME"] = args.provider_name
    if args.agent_bin:
        provider_config["HWP_AGENT_BIN"] = args.agent_bin
    if args.agent_cmd:
        provider_config["HWP_AGENT_CMD"] = args.agent_cmd
    if args.replay_chain:
        provider_config["HWP_REPLAY_CHAIN_PATH"] = str(args.replay_chain)

    # Apply defaults
    provider_config = apply_provider_defaults(provider_config, root_dir)

    # Build runner config
    runner_config = RunnerConfig(
        root_dir=root_dir,
        rounds_per_chain=args.rounds,
        round_sleep_sec=args.sleep_sec,
        chain_timeout_sec=args.timeout_sec,
        replay_chain_path=args.replay_chain,
        provider_type=provider_config.get("HWP_PROVIDER_TYPE", ""),
        provider_name=provider_config.get("HWP_PROVIDER_NAME", ""),
        agent_cmd=provider_config.get("HWP_AGENT_CMD", ""),
        agent_bin=provider_config.get("HWP_AGENT_BIN", "openclaw"),
        agent_max_retries=int(provider_config.get("HWP_AGENT_MAX_RETRIES", "3")),
        agent_timeout_sec=int(provider_config.get("HWP_AGENT_TIMEOUT", "30")),
        dry_run=args.dry_run,
    )

    # Validate input file
    input_file = Path(args.input_file)
    if not input_file.exists():
        print(f"错误：输入文件不存在: {input_file}", file=sys.stderr)
        return 1

    # Dry run: just validate and print summary
    if args.dry_run:
        print("HWP Python Runner (dry-run)")
        print(f"  config: {args.config_path or root_dir / 'config' / 'provider.env'}")
        print(f"  provider_type: {runner_config.provider_type or '(unset)'}")
        print(f"  provider_name: {runner_config.provider_name or '(unset)'}")
        resolved = resolve_provider_alias(
            runner_config.provider_type, runner_config.provider_name
        )
        print(f"  resolved_type: {resolved or '(unset)'}")
        print(f"  replay_chain: {runner_config.replay_chain_path or '(none)'}")
        if runner_config.replay_chain_path:
            print("  active_transport: replay_chain")
        elif runner_config.agent_cmd:
            print("  active_transport: agent_cmd")
            print(f"  agent_cmd: {runner_config.agent_cmd}")
        else:
            print("  active_transport: agent_bin")
            print(f"  agent_bin: {runner_config.agent_bin}")
        print("Dry run OK: provider configuration is ready.")
        return 0

    # Run chains
    runner = ChainRunner(runner_config, provider_config)

    try:
        runner.run_input_file(input_file)
        print(f"输入文件 {input_file} 处理完成。")
        return 0
    except TimeoutError as exc:
        print(f"TIMEOUT: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 1


def cmd_run_multi(args: argparse.Namespace) -> int:
    """run-multi 子命令：并行调用多个 provider（benchmark/对比场景）"""
    root_dir = Path(__file__).resolve().parent.parent

    # 读取输入文本
    if args.input_text:
        input_text = args.input_text
    elif args.input_file:
        input_file = Path(args.input_file)
        if not input_file.exists():
            print(f"错误：输入文件不存在: {input_file}", file=sys.stderr)
            return 1
        input_text = input_file.read_text(encoding="utf-8")
    else:
        print("错误：必须提供 --input-text 或 input_file", file=sys.stderr)
        return 1

    # 解析 provider 列表
    # 格式: "provider1,provider2" 或从配置文件加载
    provider_names = [name.strip() for name in args.providers.split(",") if name.strip()]

    if not provider_names:
        print("错误：至少需要一个 provider", file=sys.stderr)
        return 1

    # 为每个 provider 构建配置
    providers_config: list[dict[str, str]] = []
    for name in provider_names:
        # 尝试加载该 provider 的专用配置文件
        provider_env_path = root_dir / "config" / f"provider.{name}.env"
        if provider_env_path.exists():
            provider_config = load_provider_config(root_dir, provider_env_path)
        else:
            # 使用默认配置
            provider_config = load_provider_config(root_dir, args.config_path)

        provider_config["HWP_PROVIDER_NAME"] = name
        provider_config["HWP_PROVIDER_TYPE"] = resolve_provider_alias("", name)
        provider_config = apply_provider_defaults(provider_config, root_dir)
        providers_config.append(provider_config)

    # 构建 runner config
    runner_config = RunnerConfig(
        root_dir=root_dir,
        agent_max_retries=args.max_retries,
        agent_timeout_sec=args.timeout_sec,
    )

    # Dry run: 仅显示配置
    if args.dry_run:
        print("HWP Multi-Provider Runner (dry-run)")
        print(f"  providers: {', '.join(provider_names)}")
        print(f"  max_workers: {args.max_workers or len(providers_config)}")
        print(f"  max_retries: {args.max_retries}")
        print(f"  timeout_sec: {args.timeout_sec}")
        print(f"  input_length: {len(input_text)} chars")
        print("Dry run OK: multi-provider configuration is ready.")
        return 0

    # 执行并行调用
    print(f"并行调用 {len(providers_config)} 个 provider: {', '.join(provider_names)}")
    print(f"输入文本长度: {len(input_text)} chars")
    print("-" * 50)

    try:
        results = run_multi_provider(
            input_text=input_text,
            providers=providers_config,
            runner_config=runner_config,
            max_workers=args.max_workers,
        )

        # 输出结果
        for provider_name, result in results.items():
            print(f"\n=== {provider_name} ===")
            if result.startswith("ERROR:"):
                print(f"FAILED: {result}", file=sys.stderr)
            else:
                # 尝试提取并格式化 JSON
                try:
                    parsed = json.loads(result)
                    print(json.dumps(parsed, ensure_ascii=False, indent=2))
                except json.JSONDecodeError:
                    print(result)

        return 0
    except Exception as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 1


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

    note_infer = subparsers.add_parser("note-infer")
    note_infer.add_argument("input_json")
    note_infer.set_defaults(func=cmd_note_infer)

    # transform-batch: combine enrich + repack in one call
    transform_batch = subparsers.add_parser("transform-batch")
    transform_batch.add_argument("result_json")
    transform_batch.add_argument("inner_json")
    transform_batch.add_argument("round")
    transform_batch.add_argument("parent_recovery")
    transform_batch.set_defaults(func=cmd_transform_batch)

    # run: chain runner (Python implementation of run_sequential.sh)
    run_parser = subparsers.add_parser("run", help="运行 HWP 链编排")
    run_parser.add_argument("input_file", type=Path, help="输入文件路径（每行一条测试链）")
    run_parser.add_argument(
        "--replay-chain",
        type=Path,
        dest="replay_chain",
        help="从 JSONL 文件回放链",
    )
    run_parser.add_argument(
        "--provider-type",
        dest="provider_type",
        help="Provider 类型 (openai_compatible, ollama, openclaw, custom)",
    )
    run_parser.add_argument(
        "--provider-name",
        dest="provider_name",
        help="Provider 名称 (openrouter, deepseek, moonshot, etc.)",
    )
    run_parser.add_argument(
        "--rounds",
        type=int,
        default=8,
        help="每链轮次数（默认：8）",
    )
    run_parser.add_argument(
        "--sleep",
        type=float,
        dest="sleep_sec",
        default=2.0,
        help="轮次间休眠秒数（默认：2.0）",
    )
    run_parser.add_argument(
        "--timeout",
        type=float,
        dest="timeout_sec",
        default=0.0,
        help="链超时秒数，0 表示无超时（默认：0.0）",
    )
    run_parser.add_argument(
        "--config",
        type=Path,
        dest="config_path",
        help="Provider 配置文件路径",
    )
    run_parser.add_argument(
        "--agent-bin",
        dest="agent_bin",
        help="Agent 二进制路径（用于 openclaw）",
    )
    run_parser.add_argument(
        "--agent-cmd",
        dest="agent_cmd",
        help="Agent 命令（用于 custom provider）",
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="仅验证配置，不执行",
    )
    run_parser.set_defaults(func=cmd_run)

    # run-multi: parallel multi-provider runner for benchmark/comparison
    run_multi_parser = subparsers.add_parser(
        "run-multi",
        help="并行调用多个 provider（benchmark/对比场景）",
    )
    run_multi_parser.add_argument(
        "--providers",
        required=True,
        help="逗号分隔的 provider 名称列表，如 'deepseek,moonshot'",
    )
    run_multi_parser.add_argument(
        "--input-text",
        dest="input_text",
        help="直接提供输入文本（与 input_file 二选一）",
    )
    run_multi_parser.add_argument(
        "--input-file",
        dest="input_file",
        type=Path,
        help="输入文件路径（与 --input-text 二选一）",
    )
    run_multi_parser.add_argument(
        "--config",
        type=Path,
        dest="config_path",
        help="基础 Provider 配置文件路径",
    )
    run_multi_parser.add_argument(
        "--max-workers",
        type=int,
        dest="max_workers",
        help="最大并行工作线程数（默认：provider 数量）",
    )
    run_multi_parser.add_argument(
        "--max-retries",
        type=int,
        dest="max_retries",
        default=3,
        help="每个 provider 的最大重试次数（默认：3）",
    )
    run_multi_parser.add_argument(
        "--timeout",
        type=int,
        dest="timeout_sec",
        default=30,
        help="每个 provider 的超时秒数（默认：30）",
    )
    run_multi_parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="仅验证配置，不执行",
    )
    run_multi_parser.set_defaults(func=cmd_run_multi)

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
