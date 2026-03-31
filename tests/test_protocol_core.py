import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from hwp_protocol.cli import main as cli_main
from hwp_protocol.fixture_verify import validate_blind_spot, validate_continuity, validate_semantic_groups
from hwp_protocol.jsonl_utils import extract_inner_object, iter_record_pairs
from hwp_protocol.log_verify import (
    collect_blind_spot_messages,
    collect_continuity_messages,
    collect_semantic_groups_messages,
    verify_blind_spot,
    verify_continuity,
    verify_semantic_groups,
)
from hwp_protocol.transform import (
    enrich_inner_json,
    parse_bool_arg,
    parse_json_object_arg,
    parse_round_arg,
    repack_result_with_inner,
)


class TransformTests(unittest.TestCase):
    def test_enrich_inner_json_materializes_v06_fields(self) -> None:
        inner = {
            "node_id": "n1",
            "parent_id": None,
            "round": 1,
            "variables": ["Alpha", "Beta"],
            "paths": [{"blind_spot": {"description": "missing evidence", "impact": "critical"}}],
            "tensions": ["tradeoff"],
            "shared_variable_count": 0,
            "drift_rate": 0.2,
        }

        enriched = enrich_inner_json(inner, round_num=1, parent_recovery_applied=False)

        self.assertEqual(enriched["round_id"], "round_1")
        self.assertEqual(enriched["blind_spot_score"], 0.3)
        self.assertEqual(enriched["group_count"], 1)
        self.assertEqual(enriched["continuity_score"], 1)
        self.assertIn("state_snapshot", enriched)
        self.assertEqual(enriched["tensions"][0]["id"], "tension_01")
        self.assertEqual(enriched["drift_rate"], 0.0)
        self.assertEqual(enriched["novelty_rate"], 1.0)
        self.assertFalse(enriched["collapse_detected"])
        self.assertFalse(enriched["recovery_applied"])
        self.assertEqual(enriched["speed_metrics"]["mode"], "Rg0")

    def test_enrich_inner_json_derives_recovery_flags_and_audit_fields(self) -> None:
        inner = {
            "node_id": "n2",
            "parent_id": "n1",
            "round": 2,
            "variables": [f"var_{idx:02d}" for idx in range(1, 6)] + [f"new_{idx:02d}" for idx in range(1, 26)],
            "paths": [],
            "tensions": ["tradeoff"],
            "shared_variable_count": 5,
            "drift_rate": 0.1,
        }

        enriched = enrich_inner_json(inner, round_num=2, parent_recovery_applied=False)

        self.assertTrue(enriched["collapse_detected"])
        self.assertTrue(enriched["recovery_applied"])
        self.assertEqual(enriched["drift_rate"], 0.83)
        self.assertEqual(enriched["novelty_rate"], 0.83)
        self.assertEqual(len(enriched["recovery_kept_variables"]), 5)
        self.assertEqual(len(enriched["recovery_new_variables"]), 25)
        self.assertEqual(enriched["speed_metrics"]["mode"], "Rg0")

    def test_semantic_group_id_is_stable_when_variable_order_changes(self) -> None:
        first = enrich_inner_json(
            {
                "node_id": "n3",
                "parent_id": "n2",
                "round": 3,
                "variables": ["Alpha", "Beta", "Gamma"],
                "paths": [],
                "tensions": ["tradeoff"],
                "shared_variable_count": 3,
            },
            round_num=3,
            parent_recovery_applied=False,
        )
        second = enrich_inner_json(
            {
                "node_id": "n4",
                "parent_id": "n3",
                "round": 4,
                "variables": ["Gamma", "Alpha", "Beta"],
                "paths": [],
                "tensions": ["tradeoff"],
                "shared_variable_count": 3,
            },
            round_num=4,
            parent_recovery_applied=False,
        )

        self.assertEqual(first["semantic_groups"][0]["group_id"], second["semantic_groups"][0]["group_id"])
        self.assertTrue(second["semantic_groups"][0]["group_metadata"]["identifier_stable"])

    def test_repack_projects_inner_fields_to_outer_log(self) -> None:
        inner = {
            "node_id": "n1",
            "round": 1,
            "round_id": "round_1",
            "blind_spot_signals": [],
            "blind_spot_score": 0,
            "blind_spot_reason": "",
            "semantic_groups": [],
            "group_count": 0,
            "continuity_score": 1,
            "state_snapshot": {},
        }
        result = {"payloads": [{"text": "{}", "mediaUrl": None}], "round": 1}

        repacked = repack_result_with_inner(result, inner)

        self.assertEqual(repacked["round_id"], "round_1")
        self.assertEqual(repacked["blind_spot_score"], 0)
        self.assertEqual(repacked["payloads"][0]["mediaUrl"], None)
        self.assertIn('"round_id":"round_1"', repacked["payloads"][0]["text"])

    def test_parse_round_arg_rejects_zero(self) -> None:
        with self.assertRaisesRegex(ValueError, "round must be >= 1"):
            parse_round_arg("0")

    def test_parse_bool_arg_rejects_non_boolean_text(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be 'true' or 'false'"):
            parse_bool_arg("yes", "parent_recovery")

    def test_parse_json_object_arg_rejects_array(self) -> None:
        with self.assertRaisesRegex(TypeError, "inner_json must be a JSON object"):
            parse_json_object_arg("[]", "inner_json")


class FixtureValidatorTests(unittest.TestCase):
    def test_blind_spot_validator_rejects_invalid_score(self) -> None:
        errors = validate_blind_spot(
            {"blind_spot_signals": [], "blind_spot_score": 1.5, "blind_spot_reason": ""},
            {},
        )
        self.assertTrue(any("out of range" in error for error in errors))

    def test_continuity_validator_accepts_valid_round_two(self) -> None:
        errors = validate_continuity(
            {
                "node_id": "node_002",
                "parent_id": "node_001",
                "variables": [f"var_{idx:02d}" for idx in range(1, 21)] + [f"new_var_{idx:02d}" for idx in range(1, 11)],
                "shared_variable_count": 20,
                "drift_rate": 0.33,
                "tensions": [{"id": "tension_01"}],
                "collapse_detected": False,
            },
            {"round": 2},
        )
        self.assertEqual(errors, [])

    def test_semantic_validator_rejects_contamination(self) -> None:
        errors = validate_semantic_groups(
            {
                "semantic_groups": [
                    {
                        "group_id": "sg_ethics",
                        "coherence_score": 0.8,
                        "nodes": [{"node_id": "n1", "contamination_flag": True}],
                        "expansion_path": ["n1"],
                        "contaminated_domains": ["technical"],
                    }
                ],
                "cross_domain_contamination": True,
            },
            {},
        )
        self.assertTrue(any("contamination" in error for error in errors))


class LogVerifierTests(unittest.TestCase):
    def _write_log(self, record: dict) -> Path:
        temp = tempfile.NamedTemporaryFile("w+", delete=False, suffix=".jsonl")
        with temp:
            temp.write(json.dumps(record) + "\n")
        return Path(temp.name)

    def _capture(self, fn, path: Path) -> str:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            fn(path)
        return buffer.getvalue()

    def test_blind_spot_log_verifier_reports_passes(self) -> None:
        inner = {
            "round": 1,
            "blind_spot_signals": [],
            "blind_spot_score": 0.4,
            "blind_spot_reason": "",
        }
        record = {
            "payloads": [{"text": json.dumps(inner), "mediaUrl": None}],
            "blind_spot_signals": [],
            "blind_spot_score": 0.4,
            "blind_spot_reason": "",
        }
        path = self._write_log(record)
        output = self._capture(verify_blind_spot, path)
        self.assertIn("PASS|日志包含 blind_spot_score 字段", output)
        self.assertIn("PASS|blind_spot_reason 为字符串类型", output)

    def test_blind_spot_message_collector_returns_structured_results(self) -> None:
        record = {"blind_spot_score": 2, "blind_spot_reason": ""}
        path = self._write_log(record)

        messages = collect_blind_spot_messages(path)

        self.assertTrue(any(item.status == "FAIL" for item in messages))
        self.assertTrue(any("blind_spot_score" in item.message for item in messages))

    def test_blind_spot_message_collector_reads_inner_payload_fields(self) -> None:
        inner = {"blind_spot_signals": [], "blind_spot_score": 0.4, "blind_spot_reason": ""}
        path = self._write_log({"payloads": [{"text": json.dumps(inner), "mediaUrl": None}]})

        messages = collect_blind_spot_messages(path)

        self.assertTrue(any(item.status == "PASS" and "blind_spot_score" in item.message for item in messages))
        self.assertTrue(any(item.status == "PASS" and "blind_spot_reason" in item.message for item in messages))

    def test_continuity_log_verifier_reports_round_and_state(self) -> None:
        inner = {"round": 2, "continuity_score": 0.66, "state_snapshot": {}}
        record = {"payloads": [{"text": json.dumps(inner), "mediaUrl": None}], "round": 2}
        path = self._write_log(record)
        output = self._capture(verify_continuity, path)
        self.assertIn("PASS|日志包含轮次信息", output)
        self.assertIn("PASS|日志包含状态/上下文字段", output)

    def test_continuity_message_collector_returns_warn_for_missing_fields(self) -> None:
        path = self._write_log({"payloads": [{"text": json.dumps({"node_id": "n1"}), "mediaUrl": None}]})

        messages = collect_continuity_messages(path)

        self.assertEqual([item.status for item in messages], ["WARN", "WARN"])

    def test_semantic_log_verifier_detects_contamination(self) -> None:
        inner = {
            "semantic_groups": [
                {
                    "group_id": "sg_1",
                    "nodes": [{"node_id": "n1", "contamination_flag": True}],
                    "contaminated_domains": ["other"],
                }
            ],
            "cross_domain_contamination": True,
        }
        record = {"payloads": [{"text": json.dumps(inner), "mediaUrl": None}]}
        path = self._write_log(record)
        output = self._capture(verify_semantic_groups, path)
        self.assertIn("FAIL|检测到", output)
        self.assertIn("跨域污染标记", output)

    def test_semantic_message_collector_returns_structured_failures(self) -> None:
        path = self._write_log(
            {
                "payloads": [
                    {
                        "text": json.dumps({"semantic_groups": [{"group_id": None, "nodes": []}]}),
                        "mediaUrl": None,
                    }
                ]
            }
        )

        messages = collect_semantic_groups_messages(path)

        self.assertTrue(any(item.status == "FAIL" for item in messages))
        self.assertTrue(any("group_id: null" in item.message for item in messages))

    def test_record_pairs_preserve_outer_records_without_inner_json(self) -> None:
        records = [
            {"round": 1},
            {"payloads": [{"text": json.dumps({"round": 2}), "mediaUrl": None}]},
        ]

        pairs = iter_record_pairs(records)

        self.assertEqual(len(pairs), 2)
        self.assertEqual(pairs[0][0]["round"], 1)
        self.assertEqual(pairs[0][1], {})
        self.assertEqual(pairs[1][1]["round"], 2)

    def test_extract_inner_object_returns_empty_dict_for_invalid_payload(self) -> None:
        self.assertEqual(extract_inner_object({"payloads": [{"text": "not-json"}]}), {})


class CliTests(unittest.TestCase):
    def _run_cli(self, argv: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch.object(sys, "argv", argv):
            with redirect_stdout(stdout), patch("sys.stderr", stderr):
                exit_code = cli_main()
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def test_cli_transform_enrich_outputs_json(self) -> None:
        inner = json.dumps(
            {
                "node_id": "n1",
                "parent_id": None,
                "round": 1,
                "variables": ["Alpha"],
                "paths": [],
                "tensions": [],
                "shared_variable_count": 0,
                "drift_rate": 0.2,
            }
        )
        exit_code, stdout, _ = self._run_cli(["cli", "transform", "enrich", inner, "1", "false"])

        self.assertEqual(exit_code, 0)
        self.assertIn('"round_id":"round_1"', stdout)

    def test_cli_rejects_unknown_fixture_type(self) -> None:
        stderr = io.StringIO()
        with patch.object(sys, "argv", ["cli", "fixture-verify", "blind_spot", "all"]):
            with redirect_stdout(io.StringIO()), patch("sys.stderr", stderr):
                with self.assertRaises(SystemExit) as exc_info:
                    cli_main()

        self.assertEqual(exc_info.exception.code, 2)

    def test_cli_transform_enrich_rejects_invalid_json(self) -> None:
        exit_code, _, stderr = self._run_cli(["cli", "transform", "enrich", "{not-json", "1", "false"])

        self.assertEqual(exit_code, 1)
        self.assertIn("FATAL:", stderr)

    def test_cli_transform_repack_rejects_invalid_json(self) -> None:
        exit_code, _, stderr = self._run_cli(["cli", "transform", "repack", "{}", "{not-json"])

        self.assertEqual(exit_code, 1)
        self.assertIn("FATAL:", stderr)

    def test_cli_transform_enrich_rejects_non_object_json(self) -> None:
        exit_code, _, stderr = self._run_cli(["cli", "transform", "enrich", "[]", "1", "false"])

        self.assertEqual(exit_code, 1)
        self.assertIn("inner_json must be a JSON object", stderr)

    def test_cli_transform_enrich_rejects_invalid_parent_recovery(self) -> None:
        inner = json.dumps({"node_id": "n1", "parent_id": None, "round": 1, "variables": [], "paths": [], "tensions": []})
        exit_code, _, stderr = self._run_cli(["cli", "transform", "enrich", inner, "1", "yes"])

        self.assertEqual(exit_code, 1)
        self.assertIn("parent_recovery must be 'true' or 'false'", stderr)

    def test_cli_log_verify_missing_path_warns_in_stdout(self) -> None:
        exit_code, stdout, stderr = self._run_cli(
            ["cli", "log-verify", "blind_spot", "/tmp/definitely_missing_hwp_log.jsonl"]
        )

        self.assertEqual(exit_code, 0)
        self.assertIn("WARN|无日志文件可供分析", stdout)
        self.assertEqual(stderr, "")


if __name__ == "__main__":
    unittest.main()
