"""Video Agent — generates final video via ElevenLabs (placeholder) adapter."""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent


class VideoAgent(BaseAgent):
    agent_name = "video"
    default_model = "elevenlabs-video"

    async def _execute(self, state: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
        from app.adapters.elevenlabs import ElevenLabsAdapter
        from app.adapters.storage import StorageAdapter
        from app.ids import make_id
        from app.models.video import VideoRender

        session_id = state["session_id"]
        storyboard_shots: list[dict] = state.get("storyboard_shots", [])
        voice_url: str = state.get("voice_track_url", "")

        adapter = ElevenLabsAdapter()
        storage = StorageAdapter()

        clips: list[dict] = []
        total_cost = 0

        for shot in sorted(storyboard_shots, key=lambda x: x.get("idx", 0)):
            idx = shot.get("idx", 0)
            video_bytes, cost_cents = await adapter.generate_clip(
                image_url=shot.get("asset_url", ""),
                prompt=shot.get("prompt", shot.get("description", "")),
                duration_s=int(shot.get("timing_end_s", 4) - shot.get("timing_start_s", 0)) or 4,
            )
            total_cost += cost_cents
            key = f"sessions/{session_id}/video/clips/{idx:03d}.mp4"
            clip_url = await storage.upload(key, video_bytes, "video/mp4")
            clips.append({"idx": idx, "url": clip_url, "start_s": shot.get("timing_start_s", 0)})

        # Composite: in production this would call a video-stitching service.
        # For now the "final video" URL is just the first clip.
        final_url = clips[0]["url"] if clips else ""

        # Worst confidence from all shots
        confidences = [s.get("confidence", "speculative") for s in storyboard_shots]
        tier_rank = {"verified": 0, "approximated": 1, "speculative": 2}
        final_confidence = max(confidences, key=lambda c: tier_rank.get(c, 2), default="speculative")

        db.add(VideoRender(
            id=make_id("vr"),
            session_id=session_id,
            asset_url=final_url,
            content_hash="",
            final_confidence=final_confidence,
            manifest={"clips": clips, "voice_url": voice_url},
        ))

        return {
            "asset_url": final_url,
            "clips": clips,
            "final_confidence": final_confidence,
            "cost_cents": total_cost,
        }
