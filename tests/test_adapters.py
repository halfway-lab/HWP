import os
import unittest
from unittest.mock import patch

from adapters.adapter_common import extract_json_object_text
from adapters.openai_compatible_adapter import resolve_base_url


class AdapterTests(unittest.TestCase):
    def test_extract_json_object_text_recovers_json_from_fenced_output(self) -> None:
        text = '```json\n{"round":1,"node_id":"n1"}\n```'

        recovered = extract_json_object_text(text)

        self.assertEqual(recovered, '{"round":1,"node_id":"n1"}')

    def test_resolve_base_url_uses_builtin_preset(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(resolve_base_url("deepseek"), "https://api.deepseek.com/v1")

    def test_resolve_base_url_requires_explicit_url_for_custom_provider(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "HWP_LLM_BASE_URL"):
                resolve_base_url("custom")

    def test_resolve_base_url_accepts_explicit_url_for_custom_provider(self) -> None:
        with patch.dict(os.environ, {"HWP_LLM_BASE_URL": "https://example.com/v1"}, clear=True):
            self.assertEqual(resolve_base_url("custom"), "https://example.com/v1")
