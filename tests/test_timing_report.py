import tempfile
import unittest
from pathlib import Path

from runs.report_timing import parse_summaries, render_markdown


class TimingReportTests(unittest.TestCase):
    def test_parse_summaries_extracts_session_and_metrics(self) -> None:
        with tempfile.NamedTemporaryFile("w+", suffix=".log", delete=False) as handle:
            handle.write("开始链: hwp_1，输入: foo\n")
            handle.write("  [summary] session_id=hwp_1 rounds_completed=8 round_avg_sec=0.90 round_max_sec=1.05 chain_sec=11.37\n")
            path = Path(handle.name)

        try:
            summaries = parse_summaries(path)
            self.assertEqual(len(summaries), 1)
            self.assertEqual(summaries[0]["session_id"], "hwp_1")
            self.assertEqual(summaries[0]["rounds"], "8")
            self.assertEqual(summaries[0]["avg"], "0.90")
        finally:
            path.unlink(missing_ok=True)

    def test_parse_summaries_prefers_explicit_session_id(self) -> None:
        with tempfile.NamedTemporaryFile("w+", suffix=".log", delete=False) as handle:
            handle.write("开始链: hwp_old，输入: foo\n")
            handle.write("  [summary] session_id=hwp_new rounds_completed=8 round_avg_sec=0.90 round_max_sec=1.05 chain_sec=11.37\n")
            path = Path(handle.name)

        try:
            summaries = parse_summaries(path)
            self.assertEqual(summaries[0]["session_id"], "hwp_new")
        finally:
            path.unlink(missing_ok=True)

    def test_render_markdown_limits_to_recent_rows(self) -> None:
        markdown = render_markdown(
            [
                {"session_id": "hwp_1", "rounds": "8", "avg": "0.90", "max": "1.05", "chain": "11.37"},
                {"session_id": "hwp_2", "rounds": "4", "avg": "0.50", "max": "0.70", "chain": "2.00"},
            ],
            limit=1,
        )

        self.assertIn("| hwp_2 | 4 | 0.50 | 0.70 | 2.00 |", markdown)
        self.assertNotIn("| hwp_1 | 8 | 0.90 | 1.05 | 11.37 |", markdown)
