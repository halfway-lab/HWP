import unittest
from pathlib import Path


class V1ReleasePlanDocTests(unittest.TestCase):
    def test_v1_release_plan_mentions_release_date_and_rc2_baseline(self) -> None:
        doc = (Path(__file__).resolve().parent.parent / "docs" / "V1_RELEASE_PLAN.md").read_text(encoding="utf-8")
        self.assertIn("2026-04-20", doc)
        self.assertIn("HWP v0.6 RC2", doc)
        self.assertIn("v1.0", doc)

    def test_v1_release_plan_mentions_release_criteria_and_checklist(self) -> None:
        doc = (Path(__file__).resolve().parent.parent / "docs" / "V1_RELEASE_PLAN.md").read_text(encoding="utf-8")
        self.assertIn("## Release Criteria", doc)
        self.assertIn("## Release Checklist", doc)
        self.assertIn("python3 -m unittest", doc)


if __name__ == "__main__":
    unittest.main()
