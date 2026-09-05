"""Event-based teaching timeline for an interactive EduSense lesson.

The timeline describes presentation order; it deliberately does not own
assessment state or generate audio.  That keeps it usable by Streamlit now
and by a future scene/video composer without coupling either to the UI.
"""

from __future__ import annotations

import hashlib
from typing import Any


WORDS_PER_MINUTE = 145


def estimate_duration_ms(text: str) -> int:
    """Return a clearly approximate speech duration when audio is not ready."""
    words = len((text or "").split())
    return max(1_000, round((words / WORDS_PER_MINUTE) * 60_000))


def audio_duration_ms(word_timings: list[dict[str, Any]] | None, text: str) -> tuple[int, bool]:
    """Use Edge-TTS word timing when available; otherwise return an estimate."""
    if word_timings:
        end_times = [item.get("end_ms", 0) for item in word_timings]
        duration = max(end_times, default=0)
        if duration:
            return int(duration), False
    return estimate_duration_ms(text), True


def _event_id(section_index: int, concept_index: int, event_type: str, ordinal: int) -> str:
    raw = f"{section_index}:{concept_index}:{event_type}:{ordinal}"
    return f"event_{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:12]}"


def build_section_timeline(
    section_index: int,
    concepts: list[str],
    explanations: dict[int, str],
    visual_plan: list[dict[str, Any]] | None,
    narrations: dict[str, str] | None,
    questions: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Build ordered, serializable events for one section.

    A visual is only present when the prior planner judged it useful.  Each
    visual explanation is distinct from the concept explanation so it can be
    played/replayed as an independent Edge-TTS segment.
    """
    visual_by_concept = {
        item.get("concept_index"): item
        for item in (visual_plan or [])
        if isinstance(item, dict) and item.get("visual_required", True)
    }
    events: list[dict[str, Any]] = []
    ordinal = 0

    for concept_index, concept in enumerate(concepts):
        explanation = explanations.get(concept_index, "")
        events.append({
            "event_id": _event_id(section_index, concept_index, "explanation", ordinal),
            "event_type": "explanation",
            "section_index": section_index,
            "concept_index": concept_index,
            "concept_id": concept,
            "text": explanation,
            "visual_id": None,
            "start_ms": None,
            "duration_ms": estimate_duration_ms(explanation),
            "duration_is_estimate": True,
        })
        ordinal += 1

        visual = visual_by_concept.get(concept_index)
        if visual:
            events.append({
                "event_id": _event_id(section_index, concept_index, "visual", ordinal),
                "event_type": "visual",
                "section_index": section_index,
                "concept_index": concept_index,
                "concept_id": concept,
                "text": "",
                "visual_id": visual.get("visual_id"),
                "visual": visual,
                "start_ms": None,
                "duration_ms": 0,
                "duration_is_estimate": False,
            })
            ordinal += 1
            narration = (narrations or {}).get(visual.get("visual_id", ""), visual.get("narration", ""))
            events.append({
                "event_id": _event_id(section_index, concept_index, "visual_explanation", ordinal),
                "event_type": "visual_explanation",
                "section_index": section_index,
                "concept_index": concept_index,
                "concept_id": concept,
                "text": narration,
                "visual_id": visual.get("visual_id"),
                "visual": visual,
                "start_ms": None,
                "duration_ms": estimate_duration_ms(narration),
                "duration_is_estimate": True,
            })
            ordinal += 1

    for question_index, question in enumerate(questions or []):
        events.append({
            "event_id": _event_id(section_index, len(concepts) - 1, "question", ordinal),
            "event_type": "question",
            "section_index": section_index,
            "concept_index": len(concepts) - 1,
            "concept_id": question.get("expected_concept", question.get("concept", "")),
            "text": question.get("question", ""),
            "question_index": question_index,
            "question": question,
            "visual_id": None,
            "start_ms": None,
            "duration_ms": 0,
            "duration_is_estimate": False,
        })
        ordinal += 1

    return events


def attach_audio_metadata(event: dict[str, Any], audio_cache_key: str, word_timings: list[dict[str, Any]] | None) -> None:
    """Record the exact duration only after the mapped TTS segment exists."""
    duration_ms, is_estimate = audio_duration_ms(word_timings, event.get("text", ""))
    event["audio_id"] = audio_cache_key
    event["duration_ms"] = duration_ms
    event["duration_is_estimate"] = is_estimate


def current_event(events: list[dict[str, Any]], cursor: int) -> dict[str, Any] | None:
    if 0 <= cursor < len(events):
        return events[cursor]
    return None

