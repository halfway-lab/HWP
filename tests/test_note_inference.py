import json
import unittest
from unittest.mock import patch

from hwp_protocol.cli import main as cli_main
from hwp_protocol.note_inference import infer_note_relations


SAMPLE_INPUT = {
    "graph": {
        "notes": [
            {
                "id": "note-focus",
                "title": "环境塑造",
                "body": "人是被环境塑造的",
                "tags": ["环境塑造", "主动性", "过往经验"],
            },
            {
                "id": "note-history-1",
                "title": "环境影响选择",
                "body": "选择往往受环境影响",
                "tags": ["环境塑造", "过往经验"],
            },
            {
                "id": "note-history-2",
                "title": "行动空间",
                "body": "行动空间会影响人的判断",
                "tags": ["主动性", "行动空间"],
            },
        ],
        "links": [],
        "backlinks": [],
        "relationScores": [],
        "nodes": [],
        "edges": [],
    },
    "focusNoteIds": ["note-focus"],
    "contextWindow": {
        "focusNoteId": "note-focus",
        "neighborNoteIds": ["note-history-1"],
        "historyNoteIds": ["note-history-2"],
    },
    "maxInferences": 4,
}


class NoteInferenceTests(unittest.TestCase):
    def test_infer_note_relations_returns_bundle(self) -> None:
        bundle = infer_note_relations(SAMPLE_INPUT)

        self.assertEqual(bundle["focusNoteIds"], ["note-focus"])
        self.assertTrue(bundle["generatedAt"])
        self.assertGreaterEqual(len(bundle["inferences"]), 2)
        self.assertEqual(bundle["inferences"][0]["kind"], "inferred_relation")

    def test_infer_note_relations_requires_focus_note(self) -> None:
        with self.assertRaisesRegex(ValueError, "focusNoteIds"):
            infer_note_relations({"graph": {"notes": []}, "focusNoteIds": []})

    def test_cli_note_infer(self) -> None:
        argv = [
            "python3",
            "note-infer",
            json.dumps(SAMPLE_INPUT, ensure_ascii=False),
        ]
        with patch("sys.argv", argv):
            self.assertEqual(cli_main(), 0)
