import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import hwp_server


class DashboardServerTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
