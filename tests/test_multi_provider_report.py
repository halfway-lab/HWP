import tempfile
import unittest
from pathlib import Path

from runs.report_multi_provider import (
    calculate_provider_score,
    generate_benchmark_breakdown,
    generate_comparison_table,
    load_provider_results,
)


class MultiProviderReportTests(unittest.TestCase):
    def test_load_provider_results_prefers_overview_tsv(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            provider_dir = root / "deepseek"
            provider_dir.mkdir()
            (provider_dir / "overview.tsv").write_text(
                "benchmark\trun_status\tverifier_status\tduration_sec\tlog_count\ttiming_chains\ttiming_rounds\tround_avg_sec\tround_max_sec\tchain_avg_sec\tchain_max_sec\tfailure_reason\treport_dir\n"
                "probe\tpass\tpass\t12\t1\t1\t8\t0.90\t1.05\t11.37\t11.37\t\t/tmp/probe\n",
                encoding="utf-8",
            )
            (provider_dir / "results.tsv").write_text(
                "benchmark\trun_status\treport_dir\nprobe\tfail\t/tmp/probe\n",
                encoding="utf-8",
            )
            (provider_dir / "context.txt").write_text("provider_name=deepseek\n", encoding="utf-8")

            data = load_provider_results(root)
            self.assertTrue(data["deepseek"]["has_overview"])
            self.assertEqual(data["deepseek"]["rows"][0]["verifier_status"], "pass")

    def test_calculate_provider_score_uses_verifier_and_timing(self) -> None:
        score = calculate_provider_score(
            [
                {"run_status": "pass", "verifier_status": "pass", "chain_avg_sec": "10.00", "chain_max_sec": "12.00"},
                {"run_status": "pass", "verifier_status": "fail", "chain_avg_sec": "", "chain_max_sec": ""},
            ]
        )
        self.assertEqual(score["run_pass"], 2)
        self.assertEqual(score["verifier_pass"], 1)
        self.assertEqual(score["timing_coverage"], 1)
        self.assertAlmostEqual(score["avg_chain_sec"], 10.0)

    def test_render_helpers_include_timing_columns(self) -> None:
        provider_data = {
            "deepseek": {
                "provider": "deepseek",
                "has_overview": True,
                "context": {"provider_name": "deepseek"},
                "rows": [
                    {
                        "benchmark": "probe",
                        "run_status": "pass",
                        "verifier_status": "pass",
                        "duration_sec": "12",
                        "chain_avg_sec": "11.37",
                        "chain_max_sec": "11.37",
                        "failure_reason": "",
                    }
                ],
            }
        }
        comparison = "\n".join(generate_comparison_table(provider_data))
        breakdown = "\n".join(generate_benchmark_breakdown(provider_data))
        self.assertIn("| Provider | Source | Score | Run | Full Pass | Timing | Avg Chain Sec | Max Chain Sec |", comparison)
        self.assertIn("| deepseek | pass | pass | 12 | 11.37 | 11.37 |  |", breakdown)


if __name__ == "__main__":
    unittest.main()
