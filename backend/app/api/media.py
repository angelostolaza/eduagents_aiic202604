from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import CurrentUser, DB
from app.api.sessions import _get_owned_session
from app.models import VideoRender, VoiceTrack

router = APIRouter(tags=["voice-video"])


# ── Voice ─────────────────────────────────────────────────────────────────────

@router.get("/sessions/{session_id}/voice")
async def get_voice(
    session_id: str,
    current_user: CurrentUser,
    db: DB,
) -> dict:
    await _get_owned_session(session_id, current_user.id, db)
    result = await db.execute(
        select(VoiceTrack).where(VoiceTrack.session_id == session_id)
    )
    track = result.scalar_one_or_none()
    if track is None:
        raise HTTPException(404, {"code": "not_ready", "message": "Voice not yet generated."})
    return {
        "id": track.id,
        "asset_url": track.asset_url,
        "method": track.method,
        "manifest": track.manifest,
        "confidence_summary": track.confidence_summary,
    }


# ── Video ─────────────────────────────────────────────────────────────────────

@router.get("/sessions/{session_id}/video")
async def get_video(
    session_id: str,
    current_user: CurrentUser,
    db: DB,
) -> dict:
    await _get_owned_session(session_id, current_user.id, db)
    result = await db.execute(
        select(VideoRender).where(VideoRender.session_id == session_id)
    )
    render = result.scalar_one_or_none()
    if render is None:
        raise HTTPException(404, {"code": "not_ready", "message": "Video not yet rendered."})
    return {
        "id": render.id,
        "asset_url": render.asset_url,
        "final_confidence": render.final_confidence,
        "manifest": render.manifest,
        "rendered_at": render.rendered_at,
    }


@router.get("/sessions/{session_id}/video/clips")
async def list_video_clips(
    session_id: str,
    current_user: CurrentUser,
    db: DB,
) -> list:
    await _get_owned_session(session_id, current_user.id, db)
    result = await db.execute(
        select(VideoRender).where(VideoRender.session_id == session_id)
    )
    render = result.scalar_one_or_none()
    if render is None:
        raise HTTPException(404, {"code": "not_ready", "message": "Video not yet rendered."})
    return render.manifest.get("clips", [])


@router.get("/sessions/{session_id}/video/clips/{idx}")
async def get_video_clip(
    session_id: str,
    idx: int,
    current_user: CurrentUser,
    db: DB,
) -> dict:
    await _get_owned_session(session_id, current_user.id, db)
    result = await db.execute(
        select(VideoRender).where(VideoRender.session_id == session_id)
    )
    render = result.scalar_one_or_none()
    if render is None:
        raise HTTPException(404, {"code": "not_ready", "message": "Video not yet rendered."})
    clips = render.manifest.get("clips", [])
    matching = [c for c in clips if c.get("idx") == idx]
    if not matching:
        raise HTTPException(404, {"code": "not_found", "message": f"Clip {idx} not found."})
    return matching[0]
