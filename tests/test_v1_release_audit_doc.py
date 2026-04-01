import unittest
from pathlib import Path


class V1ReleaseAuditDocTests(unittest.TestCase):
    def test_release_audit_doc_mentions_audit_date_and_matrix(self) -> None:
        doc = (Path(__file__).resolve().parent.parent / "docs" / "V1_RELEASE_AUDIT_2026-04-01.md").read_text(encoding="utf-8")
        self.assertIn("2026-04-01", doc)
        self.assertIn("## Validation Matrix", doc)
        self.assertIn("python3 -m unittest", doc)

    def test_release_audit_doc_mentions_report_path_fix_commit(self) -> None:
        doc = (Path(__file__).resolve().parent.parent / "docs" / "V1_RELEASE_AUDIT_2026-04-01.md").read_text(encoding="utf-8")
        self.assertIn("ba57ee9", doc)
        self.assertIn("report directories now use `<timestamp>__<pid>`", doc)


if __name__ == "__main__":
    unittest.main()
