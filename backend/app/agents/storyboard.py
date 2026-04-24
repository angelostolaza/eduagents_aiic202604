"""Storyboard Agent — generates hero + workhorse frames for each shot in the shot_list."""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent


class StoryboardAgent(BaseAgent):
    agent_name = "storyboard"
    default_model = "gemini-2.0-flash-exp"

    async def _execute(self, state: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
        from app.adapters.google import GoogleAdapter
        from app.adapters.storage import StorageAdapter
        from app.ids import make_id
        from app.models.storyboard import Storyboard
        from app.speeches.catalog import get_speech_by_id
        from sqlalchemy import select

        session_id = state["session_id"]
        speech = get_speech_by_id(state["speech_id"]) or {}
        script = state.get("script_package", {})
        shot_list: list[dict] = script.get("shot_list", [])
        visual_brief: dict = script.get("visual_brief", {})
        revision_notes: dict = state.get("storyboard_revision_notes") or {}
        seed_url: str = state.get("seed_image_url", "")

        adapter = GoogleAdapter()
        storage = StorageAdapter()

        shots_out: list[dict] = []
        total_cost = 0

        for shot in shot_list:
            idx = shot.get("idx", 0)
            description = shot.get("description", "")
            prompt = (
                f"Storyboard frame {idx} for a historical documentary. "
                f"Scene: {description}. "
                f"Style: {visual_brief.get('style', 'cinematic')}. "
                f"Era: {speech.get('year', '')}. "
                "Consistent with reference image. No anachronisms. 16:9."
            )
            if revision_notes.get("notes"):
                prompt += f" Revision: {revision_notes['notes']}"

            image_bytes, cost_cents = await adapter.generate_image(prompt=prompt, aspect_ratio="16:9")
            total_cost += cost_cents

            key = f"sessions/{session_id}/storyboard/{idx:03d}.png"
            asset_url = await storage.upload(key, image_bytes, "image/png")

            shots_out.append({
                "idx": idx,
                "prompt": prompt,
                "asset_url": asset_url,
                "confidence": shot.get("confidence", "approximated"),
                "period_source": shot.get("period_source", ""),
                "timing_start_s": shot.get("timing_start_s", 0),
                "timing_end_s": shot.get("timing_end_s", shot.get("duration_s", 4)),
                "description": description,
                "voiceover": shot.get("voiceover", ""),
            })

        # Upsert storyboard
        existing = (await db.execute(
            select(Storyboard).where(Storyboard.session_id == session_id)
        )).scalar_one_or_none()

        if existing:
            existing.shots = shots_out
        else:
            db.add(Storyboard(
                id=make_id("sb"),
                session_id=session_id,
                shots=shots_out,
            ))

        return {"shots": shots_out, "cost_cents": total_cost}
