import tempfile
import unittest
from pathlib import Path

from runs.report_benchmark_overview import (
    build_overview_rows,
    build_timing_index,
    load_context,
    load_rows,
    render_markdown,
)


class BenchmarkOverviewTests(unittest.TestCase):
    def test_build_overview_rows_joins_results_with_timing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            report_dir = root / "probe"
            report_dir.mkdir()
            (report_dir / "session_ids.txt").write_text("hwp_1\n", encoding="utf-8")

            run_log = root / "run.log"
            run_log.write_text(
                "开始链: hwp_1，输入: foo\n"
                "  [summary] session_id=hwp_1 rounds_completed=8 round_avg_sec=0.90 round_max_sec=1.05 chain_sec=11.37\n",
                encoding="utf-8",
            )
            timing_index = build_timing_index(run_log)
            rows = [
                {
                    "benchmark": "probe",
                    "run_status": "pass",
                    "structured": "pass",
                    "blind_spot": "pass",
                    "continuity": "pass",
                    "semantic_groups": "pass",
                    "duration_sec": "12",
                    "log_count": "1",
                    "failure_reason": "",
                    "report_dir": str(report_dir),
                }
            ]

            overview_rows = build_overview_rows(rows, timing_index)
            self.assertEqual(overview_rows[0]["timing_chains"], "1")
            self.assertEqual(overview_rows[0]["timing_rounds"], "8")
            self.assertEqual(overview_rows[0]["chain_avg_sec"], "11.37")
            self.assertEqual(overview_rows[0]["verifier_status"], "pass")

    def test_render_markdown_includes_overall_and_benchmark_table(self) -> None:
        markdown = render_markdown(
            rows=[
                {
                    "benchmark": "probe",
                    "provider_type": "openai_compatible",
                    "provider_name": "deepseek",
                    "run_status": "pass",
                    "duration_sec": "12",
                }
            ],
            context={
                "provider_type": "openai_compatible",
                "provider_name": "deepseek",
                "benchmark_file": "config/benchmark_inputs.live_subset.txt",
                "report_dir": "/tmp/report",
                "started_at": "20260331T120000",
            },
            overview_rows=[
                {
                    "benchmark": "probe",
                    "run_status": "pass",
                    "verifier_status": "pass",
                    "duration_sec": "12",
                    "log_count": "1",
                    "timing_chains": "1",
                    "timing_rounds": "8",
                    "round_avg_sec": "0.90",
                    "round_max_sec": "1.05",
                    "chain_avg_sec": "11.37",
                    "chain_max_sec": "11.37",
                    "failure_reason": "",
                    "report_dir": "/tmp/report/probe",
                }
            ],
        )

        self.assertIn("# Benchmark Overview", markdown)
        self.assertIn("- Full protocol pass: 1/1", markdown)
        self.assertIn("| probe | pass | pass | 12 | 1 | 1 | 8 | 0.90 | 1.05 | 11.37 | 11.37 |  | /tmp/report/probe |", markdown)

    def test_loaders_read_context_and_tsv(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            context_path = root / "context.txt"
            context_path.write_text("provider_type=openai_compatible\nprovider_name=deepseek\n", encoding="utf-8")
            results_path = root / "results.tsv"
            results_path.write_text(
                "benchmark\trun_status\treport_dir\nprobe\tpass\t/tmp/probe\n",
                encoding="utf-8",
            )

            self.assertEqual(load_context(context_path)["provider_name"], "deepseek")
            self.assertEqual(load_rows(results_path)[0]["benchmark"], "probe")


if __name__ == "__main__":
    unittest.main()
