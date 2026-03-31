import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import hwp_server


class DashboardServerTests(unittest.TestCase):
    def test_list_helpers_return_sorted_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            logs_dir = Path(tmpdir) / "logs"
            reports_dir = Path(tmpdir) / "reports" / "benchmarks"
            logs_dir.mkdir(parents=True)
            reports_dir.mkdir(parents=True)
            older = logs_dir / "chain_hwp_a.jsonl"
            newer = logs_dir / "chain_hwp_b.jsonl"
            older.write_text("{}", encoding="utf-8")
            newer.write_text("{}", encoding="utf-8")
            os.utime(older, (1, 1))
            os.utime(newer, (2, 2))
            (reports_dir / "20260331T150000").mkdir()
            (reports_dir / "20260330T150000").mkdir()
            (reports_dir / "multi_20260331T150000").mkdir()
            with patch.object(hwp_server, "LOGS_DIR", logs_dir), patch.object(hwp_server, "REPORTS_DIR", reports_dir):
                self.assertEqual(hwp_server.list_benchmark_report_names(), ["20260331T150000", "20260330T150000"])
                self.assertEqual(hwp_server.list_multi_provider_report_names(), ["multi_20260331T150000"])
                self.assertEqual([Path(item).name for item in hwp_server.list_chain_paths()], ["chain_hwp_b.jsonl", "chain_hwp_a.jsonl"])

    def test_load_chain_snapshot_returns_latest_round_and_count(self) -> None:
        with tempfile.NamedTemporaryFile("w+", suffix=".jsonl", delete=False) as handle:
            handle.write(
                json.dumps(
                    {
                        "payloads": [
                            {
                                "text": json.dumps(
                                    {
                                        "round": 1,
                                        "speed_metrics": {"mode": "Rg0"},
                                        "continuity_score": 1.0,
                                        "blind_spot_score": 0.2,
                                        "collapse_detected": False,
                                        "recovery_applied": False,
                                    }
                                )
                            }
                        ]
                    }
                )
                + "\n"
            )
            chain_path = Path(handle.name)

        try:
            snapshot = hwp_server.load_chain_snapshot(str(chain_path))
            self.assertEqual(snapshot["round_count"], 1)
            self.assertEqual(snapshot["latest_round"]["mode"], "Rg0")
        finally:
            chain_path.unlink(missing_ok=True)

    def test_load_latest_benchmark_snapshot_reads_overview_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            reports_dir = Path(tmpdir) / "reports" / "benchmarks" / "20260331T150000"
            reports_dir.mkdir(parents=True)
            (reports_dir / "context.txt").write_text(
                "provider_type=openai_compatible\nprovider_name=deepseek\n",
                encoding="utf-8",
            )
            (reports_dir / "overview.tsv").write_text(
                "benchmark\trun_status\tverifier_status\tduration_sec\tlog_count\ttiming_chains\ttiming_rounds\tround_avg_sec\tround_max_sec\tchain_avg_sec\tchain_max_sec\tfailure_reason\treport_dir\n"
                "probe\tpass\tpass\t12\t1\t1\t8\t0.90\t1.05\t11.37\t11.37\t\t/tmp/probe\n",
                encoding="utf-8",
            )
            with patch.object(hwp_server, "REPORTS_DIR", Path(tmpdir) / "reports" / "benchmarks"):
                snapshot = hwp_server.load_latest_benchmark_snapshot()
            self.assertEqual(snapshot["context"]["provider_name"], "deepseek")
            self.assertEqual(snapshot["overview_rows"][0]["benchmark"], "probe")

    def test_load_benchmark_snapshot_can_target_named_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "reports" / "benchmarks"
            report_dir = root / "20260331T150000"
            report_dir.mkdir(parents=True)
            (report_dir / "overview.tsv").write_text(
                "benchmark\trun_status\tverifier_status\tduration_sec\tlog_count\ttiming_chains\ttiming_rounds\tround_avg_sec\tround_max_sec\tchain_avg_sec\tchain_max_sec\tfailure_reason\treport_dir\n"
                "probe\tpass\tpass\t12\t1\t1\t8\t0.90\t1.05\t11.37\t11.37\t\t/tmp/probe\n",
                encoding="utf-8",
            )
            with patch.object(hwp_server, "REPORTS_DIR", root):
                snapshot = hwp_server.load_benchmark_snapshot("20260331T150000")
            self.assertEqual(snapshot["report_name"], "20260331T150000")

    def test_load_multi_provider_snapshot_returns_provider_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "reports" / "benchmarks"
            report_dir = root / "multi_20260331T150000" / "deepseek"
            report_dir.mkdir(parents=True)
            (report_dir / "overview.tsv").write_text(
                "benchmark\trun_status\tverifier_status\tduration_sec\tlog_count\ttiming_chains\ttiming_rounds\tround_avg_sec\tround_max_sec\tchain_avg_sec\tchain_max_sec\tfailure_reason\treport_dir\n"
                "probe\tpass\tpass\t12\t1\t1\t8\t0.90\t1.05\t11.37\t11.37\t\t/tmp/probe\n",
                encoding="utf-8",
            )
            with patch.object(hwp_server, "REPORTS_DIR", root):
                snapshot = hwp_server.load_multi_provider_snapshot("multi_20260331T150000")
            self.assertEqual(snapshot["report_name"], "multi_20260331T150000")
            self.assertEqual(snapshot["providers"][0]["provider"], "deepseek")

    def test_load_chain_rounds_extracts_protocol_fields(self) -> None:
        with tempfile.NamedTemporaryFile("w+", suffix=".jsonl", delete=False) as handle:
            handle.write(
                json.dumps(
                    {
                        "payloads": [
                            {
                                "text": json.dumps(
                                    {
                                        "round": 1,
                                        "speed_metrics": {"mode": "Rg0"},
                                        "continuity_score": 1.0,
                                        "blind_spot_score": 0.2,
                                        "collapse_detected": False,
                                        "recovery_applied": False,
                                    }
                                )
                            }
                        ]
                    }
                )
                + "\n"
            )
            chain_path = Path(handle.name)

        try:
            rounds = hwp_server.load_chain_rounds(str(chain_path))
            self.assertEqual(rounds[0]["mode"], "Rg0")
            self.assertEqual(rounds[0]["continuity_score"], 1.0)
        finally:
            chain_path.unlink(missing_ok=True)

    def test_render_dashboard_html_contains_key_sections(self) -> None:
        html = hwp_server.render_dashboard_html(
            {
                "latest_chain": "/tmp/chain.jsonl",
                "latest_round": {"round": 8, "mode": "Rg1", "continuity_score": 0.9, "blind_spot_score": 0.4},
                "chain_rounds": [{"round": 1, "mode": "Rg0", "continuity_score": 1.0, "blind_spot_score": 0.0, "collapse_detected": False, "recovery_applied": False}],
                "benchmark": {
                    "report_dir": "/tmp/report",
                    "overview_rows": [
                        {
                            "benchmark": "probe",
                            "run_status": "pass",
                            "verifier_status": "pass",
                            "duration_sec": "12",
                            "chain_avg_sec": "11.37",
                            "chain_max_sec": "11.37",
                        }
                    ],
                },
                "multi_provider": {
                    "report_dir": "/tmp/multi",
                    "providers": [
                        {
                            "provider": "deepseek",
                            "source": "overview.tsv",
                            "run_pass": "3/3",
                            "full_pass": "3/3",
                            "timing": "3/3",
                            "avg_chain_sec": "7.20",
                            "max_chain_sec": "7.69",
                        }
                    ],
                },
            }
        )
        self.assertIn("HWP Benchmark And Protocol Dashboard", html)
        self.assertIn("Latest Benchmark Overview", html)
        self.assertIn("Latest Multi-Provider Overview", html)
        self.assertIn("Latest Chain Rounds", html)

    def test_api_index_snapshot_lists_json_endpoints(self) -> None:
        snapshot = hwp_server.api_index_snapshot()
        self.assertIn("/api/dashboard", snapshot["endpoints"])
        self.assertIn("/api/chain/latest", snapshot["query_params"])

    def test_dashboard_snapshot_with_selection_tracks_available_lists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            logs_dir = root / "logs"
            reports_dir = root / "reports" / "benchmarks"
            logs_dir.mkdir(parents=True)
            reports_dir.mkdir(parents=True)
            chain_path = logs_dir / "chain_hwp_demo.jsonl"
            chain_path.write_text(
                json.dumps(
                    {
                        "payloads": [
                            {
                                "text": json.dumps(
                                    {
                                        "round": 1,
                                        "speed_metrics": {"mode": "Rg0"},
                                        "continuity_score": 1.0,
                                        "blind_spot_score": 0.0,
                                        "collapse_detected": False,
                                        "recovery_applied": False,
                                    }
                                )
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            report_dir = reports_dir / "20260331T150000"
            report_dir.mkdir()
            (report_dir / "overview.tsv").write_text(
                "benchmark\trun_status\tverifier_status\tduration_sec\tlog_count\ttiming_chains\ttiming_rounds\tround_avg_sec\tround_max_sec\tchain_avg_sec\tchain_max_sec\tfailure_reason\treport_dir\n"
                "probe\tpass\tpass\t12\t1\t1\t8\t0.90\t1.05\t11.37\t11.37\t\t/tmp/probe\n",
                encoding="utf-8",
            )
            with patch.object(hwp_server, "LOGS_DIR", logs_dir), patch.object(hwp_server, "REPORTS_DIR", reports_dir):
                snapshot = hwp_server.dashboard_snapshot_with_selection(
                    chain_path=str(chain_path),
                    benchmark_report="20260331T150000",
                )
            self.assertEqual(snapshot["selected_benchmark_report"], "20260331T150000")
            self.assertTrue(snapshot["available_benchmark_reports"])
            self.assertEqual(snapshot["latest_round"]["mode"], "Rg0")

    def test_render_dashboard_html_contains_selection_controls(self) -> None:
        html = hwp_server.render_dashboard_html(
            {
                "latest_chain": "/tmp/chain.jsonl",
                "latest_round": {"round": 8, "mode": "Rg1", "continuity_score": 0.9, "blind_spot_score": 0.4},
                "chain_rounds": [{"round": 1, "mode": "Rg0", "continuity_score": 1.0, "blind_spot_score": 0.0, "collapse_detected": False, "recovery_applied": False}],
                "benchmark": {"report_name": "20260331T141118", "report_dir": "/tmp/report", "overview_rows": []},
                "multi_provider": {"report_name": "multi_20260331T141500", "report_dir": "/tmp/multi", "providers": []},
                "available_chains": ["logs/chain_hwp_demo.jsonl"],
                "available_benchmark_reports": ["20260331T141118"],
                "available_multi_provider_reports": ["multi_20260331T141500"],
                "selected_chain": "logs/chain_hwp_demo.jsonl",
                "selected_benchmark_report": "20260331T141118",
                "selected_multi_provider_report": "multi_20260331T141500",
            }
        )
        self.assertIn("Load Selection", html)
        self.assertIn("Benchmark Report", html)
        self.assertIn("Multi-Provider Report", html)


if __name__ == "__main__":
    unittest.main()
