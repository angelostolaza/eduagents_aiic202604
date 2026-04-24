"""Seed Image Agent — generates the reference hero image from the visual brief."""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent


class SeedImageAgent(BaseAgent):
    agent_name = "seed_image"
    default_model = "gemini-2.0-flash-exp"

    async def _execute(self, state: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
        from app.adapters.google import GoogleAdapter
        from app.adapters.storage import StorageAdapter
        from app.ids import make_id
        from app.models.seed import SeedImage
        from app.speeches.catalog import get_speech_by_id
        from sqlalchemy import func, select

        session_id = state["session_id"]
        speech = get_speech_by_id(state["speech_id"]) or {}
        visual_brief = state.get("script_package", {}).get("visual_brief", {})
        revision_notes = state.get("seed_revision_notes") or {}

        prompt_parts = [
            f"A cinematic, photorealistic historical scene depicting {speech.get('figure', 'the historical figure')}",
            f"during {speech.get('title', 'their famous speech')} in {speech.get('year', 'the era')}.",
            f"Visual style: {visual_brief.get('style', 'period-accurate documentary')}.",
            f"Lighting: {visual_brief.get('lighting', 'natural, era-appropriate')}.",
            "No anachronisms. High detail. Aspect ratio 16:9.",
        ]
        if visual_brief.get("era_indicators"):
            prompt_parts.append(f"Include era indicators: {', '.join(visual_brief['era_indicators'][:5])}.")
        if revision_notes.get("notes"):
            prompt_parts.append(f"Revision: {revision_notes['notes']}")

        prompt = " ".join(prompt_parts)

        adapter = GoogleAdapter()
        image_bytes, cost_cents = await adapter.generate_image(prompt=prompt, aspect_ratio="16:9")

        # Determine next version number
        max_version_row = await db.execute(
            select(func.max(SeedImage.version)).where(SeedImage.session_id == session_id)
        )
        max_version = max_version_row.scalar() or 0
        version = max_version + 1

        storage = StorageAdapter()
        key = f"sessions/{session_id}/seed/v{version}.png"
        asset_url = await storage.upload(key, image_bytes, "image/png")
        content_hash = storage.content_hash(image_bytes)

        db.add(SeedImage(
            id=make_id("si"),
            session_id=session_id,
            asset_url=asset_url,
            content_hash=content_hash,
            version=version,
            is_approved=False,
            manifest={"prompt": prompt, "revision_notes": revision_notes},
        ))

        return {
            "asset_url": asset_url,
            "version": version,
            "cost_cents": cost_cents,
        }
