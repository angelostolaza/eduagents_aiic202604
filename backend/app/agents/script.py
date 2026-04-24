"""Scripting Agent — produces visual_brief, shot_list, performance_notes, accuracy_manifest."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent


SCRIPT_SYSTEM_PROMPT = """You are a cinematic script writer specializing in educational historical documentaries.

Given a research form and UX choices, produce a JSON object with these top-level keys:
- visual_brief: {style, color_palette, lighting, era_indicators[], forbidden_anachronisms[]}
- shot_list: array of {idx, type, description, duration_s, voiceover, confidence, period_source}
- performance_notes: {vocal_style, pacing, emotional_arc, pronunciation_notes[]}
- accuracy_manifest: array of {element, confidence ("verified"|"approximated"|"speculative"), notes}

Target length_s should respect ux_choices.target_length_s.
shot_list should have enough shots to fill target_length_s.
Respond with ONLY the JSON object."""


class ScriptingAgent(BaseAgent):
    agent_name = "scripting"
    default_model = "claude-3-5-sonnet-20241022"

    async def _execute(self, state: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
        from app.adapters.anthropic import AnthropicAdapter
        from app.ids import make_id
        from app.models.script import ScriptPackage
        from app.speeches.catalog import get_speech_by_id
        from sqlalchemy import select

        session_id = state["session_id"]
        speech = get_speech_by_id(state["speech_id"]) or {}
        research_form = state.get("research_form", {})
        ux_choices = state.get("ux_choices", {})
        revision_notes = state.get("storyboard_revision_notes") or {}

        user_prompt = f"""Speech: {speech.get('title', '')} by {speech.get('figure', '')} ({speech.get('year', '')})
Research form: {json.dumps(research_form, indent=2)}
UX choices: {json.dumps(ux_choices, indent=2)}
"""
        if revision_notes:
            user_prompt += f"\nRevision notes:\n{json.dumps(revision_notes, indent=2)}"

        adapter = AnthropicAdapter()
        response = await adapter.complete(
            system=SCRIPT_SYSTEM_PROMPT,
            user=user_prompt,
            model=self.default_model,
            max_tokens=4096,
        )

        package_data: dict = json.loads(response["content"])

        existing = (await db.execute(
            select(ScriptPackage).where(ScriptPackage.session_id == session_id)
        )).scalar_one_or_none()

        if existing:
            existing.visual_brief = package_data.get("visual_brief", {})
            existing.shot_list = package_data.get("shot_list", [])
            existing.performance_notes = package_data.get("performance_notes", {})
            existing.accuracy_manifest = package_data.get("accuracy_manifest", [])
            existing.status = "pending_review"
        else:
            db.add(ScriptPackage(
                id=make_id("sp"),
                session_id=session_id,
                visual_brief=package_data.get("visual_brief", {}),
                shot_list=package_data.get("shot_list", []),
                performance_notes=package_data.get("performance_notes", {}),
                accuracy_manifest=package_data.get("accuracy_manifest", []),
                status="pending_review",
            ))

        return {
            "package": package_data,
            "report_url": "",
            "cost_cents": response.get("cost_cents", 0),
            "tokens_in": response.get("tokens_in", 0),
            "tokens_out": response.get("tokens_out", 0),
        }
