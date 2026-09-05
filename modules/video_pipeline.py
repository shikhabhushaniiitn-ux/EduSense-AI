"""Scene planning and local/mock composition for interactive teaching lessons.

This module intentionally creates *segments*, never an uninterrupted lesson
movie. A question scene is a hard pause boundary so the existing assessment
and re-teaching engine remains in control of lesson progression.
"""

from __future__ import annotations

import hashlib
import shutil
from typing import Any

from modules.avatar_provider import AvatarProvider, get_avatar_provider


def _scene_id(event: dict[str, Any], ordinal: int) -> str:
    raw = f"{event.get('event_id', '')}:{ordinal}"
    return f"scene_{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:12]}"


def _on_screen_text(event: dict[str, Any]) -> dict[str, Any]:
    visual = event.get("visual") or {}
    text = event.get("text", "")
    return {
        "title": event.get("concept_id", "Lesson"),
        "key_text": visual.get("equation") or visual.get("title") or text[:180],
        "caption": text if event.get("event_type") == "question" else "",
    }


def build_video_scenes(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map timeline events one-to-one to independently playable scenes."""
    scenes = []
    for ordinal, event in enumerate(events):
        event_type = event.get("event_type", "explanation")
        scenes.append({
            "scene_id": _scene_id(event, ordinal),
            "event_id": event.get("event_id"),
            "scene_type": event_type,
            "concept_id": event.get("concept_id"),
            "section_index": event.get("section_index"),
            "audio_id": event.get("audio_id"),
            "narration": event.get("text", ""),
            "duration_ms": event.get("duration_ms", 0),
            "duration_is_estimate": event.get("duration_is_estimate", True),
            "visual": event.get("visual"),
            "on_screen_text": _on_screen_text(event),
            "interactive_pause": event_type == "question",
        })
    return scenes


def refresh_scene_manifest(manifest: dict[str, Any], events: list[dict[str, Any]]) -> None:
    """Update cached scenes after a timeline event gains narration or audio.

    Composition (and any provider work) happens once. This lightweight
    refresh keeps the classroom display in sync without re-requesting avatar
    segments during Streamlit reruns.
    """
    refreshed_scenes = build_video_scenes(events)
    existing_by_id = {
        scene.get("scene_id"): scene
        for scene in manifest.get("scenes", [])
        if isinstance(scene, dict)
    }
    merged_scenes = []
    for scene in refreshed_scenes:
        cached_scene = existing_by_id.get(scene["scene_id"], {})
        cached_scene.update(scene)
        merged_scenes.append(cached_scene)
    manifest["scenes"] = merged_scenes


def next_playback_segment(scenes: list[dict[str, Any]], start_index: int = 0) -> list[dict[str, Any]]:
    """Return scenes through the next question, inclusive, then pause."""
    segment = []
    for scene in scenes[start_index:]:
        segment.append(scene)
        if scene["interactive_pause"]:
            break
    return segment


def compose_segment(scenes: list[dict[str, Any]], provider: AvatarProvider | None = None) -> dict[str, Any]:
    """Prepare a render manifest and avatar requests without hiding failures.

    FFmpeg is deliberately optional in this repository. Without it (and
    without an avatar vendor adapter), the returned mock manifest powers the
    local Streamlit presentation rather than pretending an MP4 was rendered.
    """
    provider = provider or get_avatar_provider()
    avatar_segments = [provider.generate_segment(scene).__dict__ for scene in scenes if not scene["interactive_pause"]]
    ffmpeg_available = bool(shutil.which("ffmpeg"))
    return {
        "status": "render_ready" if ffmpeg_available else "mock_ready",
        "renderer": "ffmpeg" if ffmpeg_available else "local_mock",
        "interactive": any(scene["interactive_pause"] for scene in scenes),
        "scenes": scenes,
        "avatar_segments": avatar_segments,
        "message": (
            "Scene manifest is ready for an FFmpeg adapter."
            if ffmpeg_available else
            "FFmpeg and an avatar adapter are not configured; local segment playback remains available."
        )
    }
