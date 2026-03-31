import unittest
from pathlib import Path


class DataContractsDocTests(unittest.TestCase):
    def test_data_contracts_doc_mentions_overview_tsv_columns(self) -> None:
        doc = (Path(__file__).resolve().parent.parent / "docs" / "DATA_CONTRACTS.md").read_text(encoding="utf-8")
        self.assertIn("overview.tsv", doc)
        self.assertIn("verifier_status", doc)
        self.assertIn("chain_avg_sec", doc)

    def test_data_contracts_doc_mentions_dashboard_api_endpoints(self) -> None:
        doc = (Path(__file__).resolve().parent.parent / "docs" / "DATA_CONTRACTS.md").read_text(encoding="utf-8")
        self.assertIn("/api/dashboard", doc)
        self.assertIn("/api/chain/latest", doc)
        self.assertIn("/api/benchmark/latest", doc)
        self.assertIn("/api/multi-provider/latest", doc)


if __name__ == "__main__":
    unittest.main()
