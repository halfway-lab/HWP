import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import hwp_server


class LegacyEntrypointTests(unittest.TestCase):
    def test_server_parser_supports_help_style_arguments(self) -> None:
        parser = hwp_server.build_parser()

        args = parser.parse_args(["--host", "127.0.0.1", "--port", "9090"])

        self.assertEqual(args.host, "127.0.0.1")
        self.assertEqual(args.port, 9090)

    def test_latest_chain_path_uses_repo_logs_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            logs_dir = Path(temp_dir)
            older = logs_dir / "chain_hwp_older.jsonl"
            newer = logs_dir / "chain_hwp_newer.jsonl"
            older.write_text('{"payloads":[{"text":"{}"}]}\n', encoding="utf-8")
            newer.write_text('{"payloads":[{"text":"{}"}]}\n', encoding="utf-8")
            newer.touch()
            with patch.object(hwp_server, "LOGS_DIR", logs_dir):
                self.assertEqual(hwp_server.latest_chain_path(), str(newer))

    def test_last_round_inner_json_reads_last_non_empty_line(self) -> None:
        with tempfile.NamedTemporaryFile("w+", suffix=".jsonl", delete=False) as handle:
            handle.write('{"payloads":[{"text":"{\\"round\\":1}"}]}\n\n')
            handle.write('{"payloads":[{"text":"{\\"round\\":2,\\"round_id\\":\\"round_2\\"}"}]}\n')
            path = handle.name

        try:
            result = hwp_server.last_round_inner_json(path)
            self.assertEqual(result["round"], 2)
            self.assertEqual(result["round_id"], "round_2")
        finally:
            Path(path).unlink(missing_ok=True)

    def test_replay_runner_round_one_stays_rg0_for_probe_input(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent
        replay_path = repo_root / "logs" / "chain_hwp_1774895962_11688.jsonl"
        input_path = repo_root / "inputs" / "probe.txt"

        if not replay_path.exists():
            self.skipTest(f"missing replay chain fixture: {replay_path}")

        before = {path.name for path in (repo_root / "logs").glob("chain_hwp_*.jsonl")}
        env = os.environ.copy()
        env["HWP_ROUND_SLEEP_SEC"] = "0"

        subprocess.run(
            ["bash", "runs/run_sequential.sh", "--replay-chain", str(replay_path), str(input_path)],
            cwd=repo_root,
            env=env,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        after_paths = sorted((repo_root / "logs").glob("chain_hwp_*.jsonl"), key=lambda item: item.stat().st_mtime)
        created = [path for path in after_paths if path.name not in before]
        self.assertTrue(created, "expected runner to create a replay output log")

        latest = created[-1]
        first_record = json.loads(latest.read_text(encoding="utf-8").splitlines()[0])
        inner = json.loads(first_record["payloads"][0]["text"])

        self.assertEqual(inner["round"], 1)
        self.assertEqual(inner["speed_metrics"]["mode"], "Rg0")

    def test_run_sequential_dry_run_validates_custom_provider_config(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent
        with tempfile.NamedTemporaryFile("w+", suffix=".env", delete=False) as handle:
            handle.write("HWP_PROVIDER_TYPE=openai_compatible\n")
            handle.write("HWP_PROVIDER_NAME=custom\n")
            handle.write("HWP_LLM_API_KEY=dummy\n")
            handle.write("HWP_LLM_MODEL=dummy-model\n")
            handle.write("HWP_LLM_BASE_URL=https://example.com/v1\n")
            config_path = handle.name

        try:
            result = subprocess.run(
                ["bash", "runs/run_sequential.sh", "--dry-run", "--config", config_path],
                cwd=repo_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertIn("Dry run OK", result.stdout)
            self.assertIn("provider_name: custom", result.stdout)
            self.assertIn("active_transport: agent_cmd", result.stdout)
        finally:
            Path(config_path).unlink(missing_ok=True)

    def test_run_sequential_dry_run_warns_on_placeholder_values(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent

        result = subprocess.run(
            ["bash", "runs/run_sequential.sh", "--dry-run", "--config", "config/provider.openai.env.example"],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("Warnings:", result.stdout)
        self.assertIn("HWP_LLM_API_KEY still looks like a placeholder", result.stdout)

    def test_replay_runner_writes_timing_lines_to_run_log(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent
        replay_path = repo_root / "logs" / "chain_hwp_1774895962_11688.jsonl"
        input_path = repo_root / "inputs" / "probe.txt"
        if not replay_path.exists():
            self.skipTest(f"missing replay chain fixture: {replay_path}")

        run_log = repo_root / "logs" / "run.log"
        before = run_log.read_text(encoding="utf-8") if run_log.exists() else ""
        env = os.environ.copy()
        env["HWP_ROUND_SLEEP_SEC"] = "0"

        subprocess.run(
            ["bash", "runs/run_sequential.sh", "--replay-chain", str(replay_path), str(input_path)],
            cwd=repo_root,
            env=env,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        after = run_log.read_text(encoding="utf-8")
        delta = after[len(before):]
        self.assertIn("[timing] round_sec=", delta)
        self.assertIn("[summary] session_id=", delta)
        self.assertIn("round_avg_sec=", delta)
        self.assertIn("round_max_sec=", delta)
        self.assertIn("完成链:", delta)

    def test_replay_runner_respects_chain_timeout(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent
        replay_path = repo_root / "logs" / "chain_hwp_1774895962_11688.jsonl"
        input_path = repo_root / "inputs" / "probe.txt"
        if not replay_path.exists():
            self.skipTest(f"missing replay chain fixture: {replay_path}")

        env = os.environ.copy()
        env["HWP_ROUND_SLEEP_SEC"] = "0"
        env["HWP_CHAIN_TIMEOUT_SEC"] = "0.000001"

        result = subprocess.run(
            ["bash", "runs/run_sequential.sh", "--replay-chain", str(replay_path), str(input_path)],
            cwd=repo_root,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        combined = f"{result.stdout}\n{result.stderr}"
        self.assertIn("TIMEOUT: chain", combined)
