import tempfile
import unittest
from pathlib import Path

from runs.report_regression import find_baseline_report


class ReportRegressionTests(unittest.TestCase):
    def test_find_baseline_report_supports_pid_suffixed_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            older = root / "20260401T110000__111"
            current = root / "20260401T120000__222"
            older.mkdir()
            current.mkdir()

            baseline = find_baseline_report(root, current)
            self.assertEqual(baseline, older)


if __name__ == "__main__":
    unittest.main()
