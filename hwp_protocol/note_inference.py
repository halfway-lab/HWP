#!/usr/bin/env python3
import datetime as dt
from typing import Any


def _ensure_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _ensure_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _clip_score(value: float) -> float:
    return max(0.0, min(1.0, round(value, 2)))


def _note_map(graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    notes = _ensure_list(graph.get("notes"))
    return {
        str(note.get("id")): _ensure_dict(note)
        for note in notes
        if isinstance(note, dict) and note.get("id")
    }


def _shared_tags(left: dict[str, Any], right: dict[str, Any]) -> list[str]:
    left_tags = {str(tag) for tag in _ensure_list(left.get("tags")) if str(tag).strip()}
    right_tags = {str(tag) for tag in _ensure_list(right.get("tags")) if str(tag).strip()}
    return sorted(left_tags & right_tags)


def _title_for(note: dict[str, Any], fallback: str) -> str:
    title = str(note.get("title") or "").strip()
    return title or fallback


def _build_relation(
    focus_note: dict[str, Any],
    other_note: dict[str, Any],
    shared_tags: list[str],
    score: float,
) -> dict[str, Any]:
    focus_id = str(focus_note["id"])
    other_id = str(other_note["id"])
    tag_label = " / ".join(shared_tags[:2]) if shared_tags else "history resonance"
    return {
        "id": f"inferred-relation-{focus_id}-{other_id}",
        "kind": "inferred_relation",
        "sourceNoteId": focus_id,
        "targetNoteId": other_id,
        "label": f"{tag_label} bridge",
        "explanation": {
            "summary": f"{_title_for(focus_note, focus_id)} and {_title_for(other_note, other_id)} share contextual structure.",
            "evidenceNoteIds": [focus_id, other_id],
            "rationaleSteps": [
                "Read explicit graph neighborhood around the focus note.",
                "Compare explicit tags and contextual linkage.",
                "Surface a candidate inferred relation for app-side inspection.",
            ],
        },
        "confidence": {
            "score": _clip_score(score),
            "status": "supported" if shared_tags else "candidate",
            "uncertainty": "" if shared_tags else "Relation is based on explicit neighborhood more than shared tags.",
        },
    }


def _build_bridge(note_ids: list[str], bridge_concept: str, score: float) -> dict[str, Any]:
    return {
        "id": f"latent-bridge-{'-'.join(note_ids[:3])}",
        "kind": "latent_bridge",
        "noteIds": note_ids,
        "bridgeConcept": bridge_concept,
        "explanation": {
            "summary": f"These notes may cluster around {bridge_concept}.",
            "evidenceNoteIds": note_ids,
            "rationaleSteps": [
                "Inspect overlapping note tags.",
                "Collapse repeated themes into a bridge concept.",
            ],
        },
        "confidence": {
            "score": _clip_score(score),
            "status": "candidate",
            "uncertainty": "Bridge concept is heuristic and should be reviewed in the UI.",
        },
    }


def _build_thematic_path(
    focus_id: str,
    target_id: str,
    theme: str,
    score: float,
) -> dict[str, Any]:
    return {
        "id": f"thematic-path-{focus_id}-{target_id}",
        "kind": "thematic_path",
        "steps": [
            {"noteId": focus_id, "theme": theme},
            {"noteId": target_id, "theme": theme},
        ],
        "explanation": {
            "summary": f"The focus note can be explored toward {target_id} through the theme {theme}.",
            "evidenceNoteIds": [focus_id, target_id],
            "rationaleSteps": [
                "Start from the focus note.",
                "Follow the strongest explicit or contextual neighbor.",
                "Expose the shared theme as a path candidate.",
            ],
        },
        "confidence": {
            "score": _clip_score(score),
            "status": "candidate",
            "uncertainty": "Path is a suggested exploration route, not a definitive cluster.",
        },
    }


def infer_note_relations(payload: dict[str, Any]) -> dict[str, Any]:
    graph = _ensure_dict(payload.get("graph"))
    notes = _note_map(graph)
    focus_ids = [str(item) for item in _ensure_list(payload.get("focusNoteIds")) if str(item).strip()]
    if not focus_ids:
      raise ValueError("focusNoteIds must contain at least one note id")

    focus_id = focus_ids[0]
    focus_note = notes.get(focus_id)
    if not focus_note:
        raise ValueError(f"focus note not found in graph: {focus_id}")

    context_window = _ensure_dict(payload.get("contextWindow"))
    candidate_ids = [
        str(item)
        for item in _ensure_list(context_window.get("neighborNoteIds")) + _ensure_list(context_window.get("historyNoteIds"))
        if str(item).strip() and str(item) != focus_id
    ]

    ordered_candidate_ids: list[str] = []
    for note_id in candidate_ids:
        if note_id not in ordered_candidate_ids:
            ordered_candidate_ids.append(note_id)

    max_inferences = int(payload.get("maxInferences") or 8)
    inferences: list[dict[str, Any]] = []
    bridge_note_ids = [focus_id]
    bridge_tags: list[str] = []

    for candidate_id in ordered_candidate_ids:
        other_note = notes.get(candidate_id)
        if not other_note:
            continue
        shared_tags = _shared_tags(focus_note, other_note)
        score = 0.55 + min(len(shared_tags), 3) * 0.1
        inferences.append(_build_relation(focus_note, other_note, shared_tags, score))
        bridge_note_ids.append(candidate_id)
        bridge_tags.extend(shared_tags)
        if len(inferences) >= max_inferences:
            break

    if len(bridge_note_ids) >= 3 and len(inferences) < max_inferences:
        concept = bridge_tags[0] if bridge_tags else "shared context"
        inferences.append(_build_bridge(bridge_note_ids[:3], concept, 0.62))

    if ordered_candidate_ids and len(inferences) < max_inferences:
        first_target = ordered_candidate_ids[0]
        first_note = notes.get(first_target, {})
        theme_candidates = _shared_tags(focus_note, first_note)
        theme = theme_candidates[0] if theme_candidates else "contextual continuation"
        inferences.append(_build_thematic_path(focus_id, first_target, theme, 0.58))

    return {
        "focusNoteIds": focus_ids,
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "inferences": inferences[:max_inferences],
    }
