"""Voice Agent — generates narration via ElevenLabs v3."""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent


class VoiceAgent(BaseAgent):
    agent_name = "voice"
    default_model = "eleven_multilingual_v3"

    async def _execute(self, state: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
        from app.adapters.elevenlabs import ElevenLabsAdapter
        from app.adapters.storage import StorageAdapter
        from app.ids import make_id
        from app.models.voice import VoiceTrack
        from app.speeches.catalog import get_speech_by_id

        session_id = state["session_id"]
        speech = get_speech_by_id(state["speech_id"]) or {}
        script = state.get("script_package", {})
        shot_list: list[dict] = script.get("shot_list", [])
        performance_notes: dict = script.get("performance_notes", {})

        # Stitch voiceover text from shots
        voiceover_lines = [s.get("voiceover", "") for s in sorted(shot_list, key=lambda x: x.get("idx", 0)) if s.get("voiceover")]
        full_script = " ".join(voiceover_lines)

        if not full_script.strip():
            # Fallback: use speech description
            full_script = speech.get("description", "This historical speech was pivotal in its era.")

        adapter = ElevenLabsAdapter()
        audio_bytes, cost_cents, method = await adapter.synthesize(
            text=full_script,
            performance_notes=performance_notes,
        )

        storage = StorageAdapter()
        key = f"sessions/{session_id}/voice/narration.mp3"
        asset_url = await storage.upload(key, audio_bytes, "audio/mpeg")
        content_hash = storage.content_hash(audio_bytes)

        confidence_summary = {
            "method": method,
            "verified_script_lines": sum(
                1 for s in shot_list if s.get("confidence") == "verified"
            ),
            "total_lines": len(shot_list),
        }

        db.add(VoiceTrack(
            id=make_id("vt"),
            session_id=session_id,
            asset_url=asset_url,
            content_hash=content_hash,
            method=method,
            manifest={"full_script": full_script, "performance_notes": performance_notes},
            confidence_summary=confidence_summary,
        ))

        return {
            "asset_url": asset_url,
            "method": method,
            "confidence": confidence_summary,
            "cost_cents": cost_cents,
        }
