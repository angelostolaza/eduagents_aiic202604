"""LangGraph session state TypedDict.

Every field is Optional so checkpoints can be partial.
The orchestrator writes to this dict; agents read from it.
"""
from __future__ import annotations

from typing import Any, TypedDict


class SessionState(TypedDict, total=False):
    # ── Identity ──────────────────────────────────────────────────────────────
    session_id: str
    user_id: str
    speech_id: str
    accuracy_tier: int
    ux_choices: dict[str, Any]

    # ── Pipeline state ────────────────────────────────────────────────────────
    current_state: str  # mirrors ProjectSession.state

    # ── Agent outputs ─────────────────────────────────────────────────────────
    research_form: dict[str, Any]       # {field: {value, confidence, sources}}
    research_report_url: str

    script_package: dict[str, Any]      # {visual_brief, shot_list, performance_notes, accuracy_manifest}
    script_report_url: str

    seed_image_url: str
    seed_image_version: int
    seed_revision_notes: dict[str, Any]

    storyboard_shots: list[dict[str, Any]]
    storyboard_revision_notes: dict[str, Any]

    voice_track_url: str
    voice_method: str
    voice_confidence: dict[str, Any]

    video_url: str
    video_clips: list[dict[str, Any]]
    video_final_confidence: str

    # ── Error propagation ─────────────────────────────────────────────────────
    error: str | None

    # ── Approval flags (set by human-gate API endpoints) ─────────────────────
    research_approved: bool
    script_approved: bool
    seed_approved: bool
    storyboard_approved: bool

    # ── Bust (parallel 3D pipeline) ────────────────────────────────────────────
    bust_id: str
    bust_glb_url: str
    bust_portrait_url: str
    bust_method: str

    # ── Cost tracking ─────────────────────────────────────────────────────────
    total_cost_cents: int
