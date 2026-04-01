"""
边界条件测试覆盖。

测试 transform.py、jsonl_utils.py、log_verify.py 的边界情况。
"""
import json
import tempfile
import unittest
from pathlib import Path

from hwp_protocol.jsonl_utils import (
    count_jsonl_lines,
    extract_inner_object,
    iter_record_pairs,
    load_jsonl,
    load_jsonl_last_n,
)
from hwp_protocol.log_verify import (
    collect_blind_spot_messages,
    collect_continuity_messages,
    collect_semantic_groups_messages,
)
from hwp_protocol.transform import (
    clamp01,
    enrich_inner_json,
    parse_round_arg,
    round_metric,
)


class TransformEdgeCaseTests(unittest.TestCase):
    """transform.py 边界条件测试。"""

    def test_empty_variables_list(self) -> None:
        """测试空 variables 列表的处理。"""
        inner = {
            "node_id": "n1",
            "parent_id": None,
            "round": 1,
            "variables": [],
            "paths": [],
            "tensions": [],
        }
        enriched = enrich_inner_json(inner, round_num=1, parent_recovery_applied=False)

        self.assertEqual(enriched["variables"], [])
        self.assertEqual(enriched["semantic_groups"], [])
        self.assertEqual(enriched["group_count"], 0)
        self.assertEqual(enriched["continuity_score"], 1)  # 根节点

    def test_empty_tensions_list(self) -> None:
        """测试空 tensions 列表的处理。"""
        inner = {
            "node_id": "n1",
            "parent_id": None,
            "round": 1,
            "variables": ["Alpha"],
            "paths": [],
            "tensions": [],
        }
        enriched = enrich_inner_json(inner, round_num=1, parent_recovery_applied=False)

        self.assertEqual(enriched["tensions"], [])
        self.assertIn("state_snapshot", enriched)
        # 继承的 tension ids 应为空
        self.assertEqual(enriched["state_snapshot"]["active_tension_ids"], [])

    def test_variables_truncated_at_30_limit(self) -> None:
        """测试 variables 超过 30 个上限时的截断行为。"""
        # 创建 35 个变量
        variables = [f"var_{idx:02d}" for idx in range(35)]
        inner = {
            "node_id": "n1",
            "parent_id": None,
            "round": 1,
            "variables": variables,
            "paths": [],
            "tensions": [],
        }
        enriched = enrich_inner_json(inner, round_num=1, parent_recovery_applied=False)

        # 变量应被截断到 30 个
        self.assertEqual(len(enriched["variables"]), 30)
        # 应记录截断操作
        self.assertTrue(
            any("Trimmed variables" in action for action in enriched["speed_metrics"].get("action_taken", []))
        )

    def test_null_field_values(self) -> None:
        """测试字段值为 null/None 的情况。"""
        inner = {
            "node_id": None,
            "parent_id": None,
            "round": 1,
            "variables": None,
            "paths": None,
            "tensions": None,
            "shared_variable_count": None,
        }
        enriched = enrich_inner_json(inner, round_num=1, parent_recovery_applied=False)

        # None 的 tensions 应被处理为空列表
        self.assertEqual(enriched["tensions"], [])
        # 即使输入 variables 为 None，enriched 结果应正常处理
        self.assertIn("round_id", enriched)

    def test_extreme_entropy_zero(self) -> None:
        """测试 entropy=0 的极端情况。"""
        inner = {
            "node_id": "n1",
            "parent_id": "p1",
            "round": 2,
            "variables": ["A", "B", "C"],
            "paths": [],
            "tensions": [],
            "shared_variable_count": 3,
            "entropy_score": 0.0,
        }
        enriched = enrich_inner_json(inner, round_num=2, parent_recovery_applied=False)

        # entropy=0 时不应触发 collapse
        self.assertFalse(enriched["collapse_detected"])

    def test_extreme_entropy_one(self) -> None:
        """测试 entropy=1 的极端情况。"""
        inner = {
            "node_id": "n1",
            "parent_id": "p1",
            "round": 2,
            "variables": ["A", "B"],
            "paths": [],
            "tensions": [],
            "shared_variable_count": 1,
            "entropy_score": 1.0,
        }
        enriched = enrich_inner_json(inner, round_num=2, parent_recovery_applied=False)

        # entropy=1 且 drift_rate >= 0.30 时应触发 collapse
        # drift_rate = 1 - (1/2) = 0.5, 满足条件
        self.assertTrue(enriched["collapse_detected"])

    def test_extreme_drift_zero(self) -> None:
        """测试 drift=0 的极端情况（完全继承）。"""
        inner = {
            "node_id": "n1",
            "parent_id": "p1",
            "round": 2,
            "variables": ["A", "B", "C"],
            "paths": [],
            "tensions": [],
            "shared_variable_count": 3,  # 全部继承
        }
        enriched = enrich_inner_json(inner, round_num=2, parent_recovery_applied=False)

        self.assertEqual(enriched["drift_rate"], 0.0)
        self.assertEqual(enriched["novelty_rate"], 0.0)
        self.assertFalse(enriched["collapse_detected"])

    def test_extreme_drift_one(self) -> None:
        """测试 drift=1 的极端情况（完全新颖）。"""
        inner = {
            "node_id": "n1",
            "parent_id": "p1",
            "round": 2,
            "variables": ["A", "B", "C"],
            "paths": [],
            "tensions": [],
            "shared_variable_count": 0,  # 完全不继承
        }
        enriched = enrich_inner_json(inner, round_num=2, parent_recovery_applied=False)

        self.assertEqual(enriched["drift_rate"], 1.0)
        self.assertEqual(enriched["novelty_rate"], 1.0)
        self.assertTrue(enriched["collapse_detected"])

    def test_round_id_zero_rejected(self) -> None:
        """测试 round_id 为 0 时被拒绝。"""
        with self.assertRaisesRegex(ValueError, "round must be >= 1"):
            parse_round_arg("0")

    def test_round_id_negative_rejected(self) -> None:
        """测试 round_id 为负数时被拒绝。"""
        with self.assertRaisesRegex(ValueError, "round must be >= 1"):
            parse_round_arg("-5")

    def test_inner_json_completely_empty(self) -> None:
        """测试 inner JSON 完全为空 {} 的情况。"""
        inner = {}
        enriched = enrich_inner_json(inner, round_num=1, parent_recovery_applied=False)

        # 应添加默认值
        self.assertEqual(enriched["round_id"], "round_1")
        self.assertIn("tensions", enriched)
        self.assertEqual(enriched["blind_spot_score"], 0.0)
        self.assertIn("state_snapshot", enriched)

    def test_clamp01_boundary_values(self) -> None:
        """测试 clamp01 对边界值的处理。"""
        self.assertEqual(clamp01(-0.5), 0.0)
        self.assertEqual(clamp01(0.0), 0.0)
        self.assertEqual(clamp01(0.5), 0.5)
        self.assertEqual(clamp01(1.0), 1.0)
        self.assertEqual(clamp01(1.5), 1.0)

    def test_round_metric_precision(self) -> None:
        """测试 round_metric 的精度处理。"""
        self.assertEqual(round_metric(0.123456), 0.12)
        self.assertEqual(round_metric(0.999), 1.0)
        self.assertEqual(round_metric(0.001), 0.0)

    def test_nested_null_in_paths(self) -> None:
        """测试 paths 中嵌套 null 的处理。"""
        inner = {
            "node_id": "n1",
            "parent_id": None,
            "round": 1,
            "variables": ["Alpha"],
            "paths": [
                None,
                {"blind_spot": None},
                {"blind_spot": {"description": None, "impact": None}},
                {"blind_spot": {"description": "valid description", "impact": "critical"}},
            ],
            "tensions": [],
        }
        enriched = enrich_inner_json(inner, round_num=1, parent_recovery_applied=False)

        # 只有最后一个 path 应生成有效 signal
        self.assertEqual(len(enriched["blind_spot_signals"]), 1)
        self.assertEqual(enriched["blind_spot_signals"][0]["severity"], "high")


class JsonlUtilsEdgeCaseTests(unittest.TestCase):
    """jsonl_utils.py 边界条件测试。"""

    def _write_temp_file(self, content: str) -> Path:
        """创建临时文件并返回路径。"""
        temp = tempfile.NamedTemporaryFile("w+", delete=False, suffix=".jsonl", encoding="utf-8")
        temp.write(content)
        temp.close()
        return Path(temp.name)

    def test_empty_jsonl_file(self) -> None:
        """测试空 JSONL 文件的处理。"""
        path = self._write_temp_file("")
        try:
            records, corrupt = load_jsonl(path)
            self.assertEqual(records, [])
            self.assertEqual(corrupt, 0)
        finally:
            path.unlink()

    def test_single_valid_jsonl_line(self) -> None:
        """测试单行有效 JSONL 的处理。"""
        path = self._write_temp_file('{"key": "value"}\n')
        try:
            records, corrupt = load_jsonl(path)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["key"], "value")
            self.assertEqual(corrupt, 0)
        finally:
            path.unlink()

    def test_all_corrupt_jsonl_lines(self) -> None:
        """测试全部损坏的 JSONL（100% 损坏行）。"""
        path = self._write_temp_file("not json at all\n{broken: json}\nanother corrupt\n")
        try:
            records, corrupt = load_jsonl(path)
            self.assertEqual(records, [])
            self.assertEqual(corrupt, 3)
        finally:
            path.unlink()

    def test_mixed_valid_and_corrupt_lines(self) -> None:
        """测试混合有效和损坏行。"""
        content = '{"valid": 1}\ncorrupt line\n{"valid": 2}\n{bad: json}\n{"valid": 3}\n'
        path = self._write_temp_file(content)
        try:
            records, corrupt = load_jsonl(path)
            self.assertEqual(len(records), 3)
            self.assertEqual(corrupt, 2)
        finally:
            path.unlink()

    def test_deeply_nested_json(self) -> None:
        """测试超大单行 JSON（嵌套很深）。"""
        # 创建深度嵌套的 JSON
        nested = {"level": 0}
        for i in range(1, 50):
            nested = {"level": i, "nested": nested}

        path = self._write_temp_file(json.dumps(nested) + "\n")
        try:
            records, corrupt = load_jsonl(path)
            self.assertEqual(len(records), 1)
            self.assertEqual(corrupt, 0)
            # 验证嵌套结构
            current = records[0]
            for i in range(49, -1, -1):
                self.assertEqual(current["level"], i)
                current = current.get("nested", {})
        finally:
            path.unlink()

    def test_load_jsonl_last_n_exceeds_actual_lines(self) -> None:
        """测试 load_jsonl_last_n 的 n 大于实际行数。"""
        path = self._write_temp_file('{"a": 1}\n{"b": 2}\n')
        try:
            records, corrupt = load_jsonl_last_n(path, 10)
            # 应返回所有可用记录（只有 2 条）
            self.assertEqual(len(records), 2)
            self.assertEqual(corrupt, 0)
        finally:
            path.unlink()

    def test_load_jsonl_last_n_zero(self) -> None:
        """测试 load_jsonl_last_n 的 n 为 0。"""
        path = self._write_temp_file('{"a": 1}\n{"b": 2}\n')
        try:
            records, corrupt = load_jsonl_last_n(path, 0)
            self.assertEqual(records, [])
            self.assertEqual(corrupt, 0)
        finally:
            path.unlink()

    def test_load_jsonl_last_n_negative(self) -> None:
        """测试 load_jsonl_last_n 的 n 为负数。"""
        path = self._write_temp_file('{"a": 1}\n{"b": 2}\n')
        try:
            records, corrupt = load_jsonl_last_n(path, -5)
            self.assertEqual(records, [])
            self.assertEqual(corrupt, 0)
        finally:
            path.unlink()

    def test_count_jsonl_lines_empty_file(self) -> None:
        """测试 count_jsonl_lines 对空文件的行为。"""
        path = self._write_temp_file("")
        try:
            count = count_jsonl_lines(path)
            self.assertEqual(count, 0)
        finally:
            path.unlink()

    def test_count_jsonl_lines_only_whitespace(self) -> None:
        """测试 count_jsonl_lines 对只含空白字符文件的行为。"""
        path = self._write_temp_file("   \n\n   \n")
        try:
            count = count_jsonl_lines(path)
            self.assertEqual(count, 0)
        finally:
            path.unlink()

    def test_extract_inner_object_empty_payloads(self) -> None:
        """测试 extract_inner_object 对空 payloads 的处理。"""
        self.assertEqual(extract_inner_object({"payloads": []}), {})
        self.assertEqual(extract_inner_object({"payloads": None}), {})
        self.assertEqual(extract_inner_object({}), {})

    def test_iter_record_pairs_empty_list(self) -> None:
        """测试 iter_record_pairs 对空列表的处理。"""
        pairs = iter_record_pairs([])
        self.assertEqual(pairs, [])


class LogVerifyEdgeCaseTests(unittest.TestCase):
    """log_verify.py 边界条件测试。"""

    def _write_temp_file(self, content: str) -> Path:
        """创建临时文件并返回路径。"""
        temp = tempfile.NamedTemporaryFile("w+", delete=False, suffix=".jsonl", encoding="utf-8")
        temp.write(content)
        temp.close()
        return Path(temp.name)

    def test_empty_log_file_blind_spot(self) -> None:
        """测试空日志文件的 blind_spot 验证。"""
        path = self._write_temp_file("")
        try:
            messages = collect_blind_spot_messages(path)
            # 应产生 WARN 消息
            self.assertTrue(any(item.status == "WARN" for item in messages))
            self.assertTrue(any("无可解析日志记录" in item.message for item in messages))
        finally:
            path.unlink()

    def test_empty_log_file_continuity(self) -> None:
        """测试空日志文件的 continuity 验证。"""
        path = self._write_temp_file("")
        try:
            messages = collect_continuity_messages(path)
            self.assertTrue(any(item.status == "WARN" for item in messages))
        finally:
            path.unlink()

    def test_empty_log_file_semantic_groups(self) -> None:
        """测试空日志文件的 semantic_groups 验证。"""
        path = self._write_temp_file("")
        try:
            messages = collect_semantic_groups_messages(path)
            self.assertTrue(any(item.status == "WARN" for item in messages))
        finally:
            path.unlink()

    def test_all_corrupt_lines_blind_spot(self) -> None:
        """测试只有损坏行的日志验证。"""
        path = self._write_temp_file("corrupt line 1\ncorrupt line 2\n")
        try:
            messages = collect_blind_spot_messages(path)
            # 应有损坏行警告
            self.assertTrue(any("损坏" in item.message for item in messages))
            # 应有无可解析记录的警告
            self.assertTrue(any("无可解析日志记录" in item.message for item in messages))
        finally:
            path.unlink()

    def test_missing_blind_spot_fields(self) -> None:
        """测试缺少关键字段 blind_spot 的记录。"""
        path = self._write_temp_file(json.dumps({"other_field": "value"}) + "\n")
        try:
            messages = collect_blind_spot_messages(path)
            # 字段缺失应为 WARN（OPTIONAL 字段）
            self.assertTrue(any(item.status == "WARN" for item in messages))
            self.assertTrue(any("未找到" in item.message for item in messages))
        finally:
            path.unlink()

    def test_missing_continuity_fields(self) -> None:
        """测试缺少关键字段 continuity 的记录。"""
        path = self._write_temp_file(json.dumps({"other_field": "value"}) + "\n")
        try:
            messages = collect_continuity_messages(path)
            self.assertTrue(any(item.status == "WARN" for item in messages))
        finally:
            path.unlink()

    def test_missing_semantic_groups_fields(self) -> None:
        """测试缺少关键字段 semantic_groups 的记录。"""
        path = self._write_temp_file(json.dumps({"other_field": "value"}) + "\n")
        try:
            messages = collect_semantic_groups_messages(path)
            self.assertTrue(any(item.status == "WARN" for item in messages))
        finally:
            path.unlink()

    def test_high_corruption_ratio_triggers_fail(self) -> None:
        """测试高损坏比例触发 FAIL。"""
        # 5 条损坏，1 条有效 -> 损坏比例 > 20%
        content = 'valid json line\n' + 'corrupt\n' * 5
        path = self._write_temp_file(content)
        try:
            messages = collect_blind_spot_messages(path)
            # 高损坏比例应产生 FAIL
            self.assertTrue(any(item.status == "FAIL" for item in messages))
            self.assertTrue(any("超过 20% 阈值" in item.message for item in messages))
        finally:
            path.unlink()

    def test_null_blind_spot_score(self) -> None:
        """测试 blind_spot_score 为 null 的情况。"""
        path = self._write_temp_file(json.dumps({"blind_spot_score": None}) + "\n")
        try:
            messages = collect_blind_spot_messages(path)
            # null 值应被检测
            self.assertTrue(any(item.status == "WARN" for item in messages))
        finally:
            path.unlink()

    def test_out_of_range_blind_spot_score(self) -> None:
        """测试 blind_spot_score 超出范围的情况。"""
        path = self._write_temp_file(json.dumps({"blind_spot_score": 2.5}) + "\n")
        try:
            messages = collect_blind_spot_messages(path)
            self.assertTrue(any(item.status == "FAIL" for item in messages))
            self.assertTrue(any("无效" in item.message or "超出" in item.message or "范围" in item.message for item in messages))
        finally:
            path.unlink()

    def test_string_blind_spot_score(self) -> None:
        """测试 blind_spot_score 为字符串的情况。"""
        path = self._write_temp_file(json.dumps({"blind_spot_score": "0.5"}) + "\n")
        try:
            messages = collect_blind_spot_messages(path)
            self.assertTrue(any(item.status == "FAIL" for item in messages))
            self.assertTrue(any("字符串" in item.message for item in messages))
        finally:
            path.unlink()

    def test_null_semantic_group_id(self) -> None:
        """测试 semantic_group 的 group_id 为 null 的情况。"""
        record = {
            "semantic_groups": [
                {"group_id": None, "nodes": []}
            ]
        }
        path = self._write_temp_file(json.dumps(record) + "\n")
        try:
            messages = collect_semantic_groups_messages(path)
            self.assertTrue(any(item.status == "FAIL" for item in messages))
            self.assertTrue(any("group_id" in item.message and "null" in item.message for item in messages))
        finally:
            path.unlink()

    def test_cross_domain_contamination_detection(self) -> None:
        """测试跨域污染检测。"""
        record = {
            "semantic_groups": [
                {
                    "group_id": "sg_1",
                    "nodes": [{"node_id": "n1", "contamination_flag": True}],
                    "contaminated_domains": ["technical"],
                }
            ],
            "cross_domain_contamination": True,
        }
        path = self._write_temp_file(json.dumps(record) + "\n")
        try:
            messages = collect_semantic_groups_messages(path)
            self.assertTrue(any(item.status == "FAIL" for item in messages))
            self.assertTrue(any("污染" in item.message for item in messages))
        finally:
            path.unlink()


if __name__ == "__main__":
    unittest.main()
