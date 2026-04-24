from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DB
from app.api.sessions import _get_owned_session
from app.models import ProjectSession, SessionState, Storyboard
from app.queue.jobs import enqueue_agent
from app.schemas.storyboard import StoryboardOut, StoryboardRevise

router = APIRouter(prefix="/sessions/{session_id}/storyboard", tags=["storyboard"])


@router.post("/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_storyboard(
    session_id: str,
    current_user: CurrentUser,
    db: DB,
) -> dict:
    session = await _get_owned_session(session_id, current_user.id, db)
    _assert_state(session, SessionState.storyboard_generating, SessionState.storyboard_review)

    session.state = SessionState.storyboard_generating.value
    await db.flush()

    job_id = enqueue_agent("storyboard", session_id)
    return {"job_id": job_id, "session_id": session_id}


@router.get("", response_model=StoryboardOut)
async def get_storyboard(
    session_id: str,
    current_user: CurrentUser,
    db: DB,
) -> StoryboardOut:
    await _get_owned_session(session_id, current_user.id, db)
    sb = await _get_storyboard(session_id, db)
    return StoryboardOut.model_validate(sb)


@router.get("/frames/{idx}")
async def get_frame(
    session_id: str,
    idx: int,
    current_user: CurrentUser,
    db: DB,
) -> dict:
    await _get_owned_session(session_id, current_user.id, db)
    sb = await _get_storyboard(session_id, db)
    matching = [s for s in sb.shots if s.get("idx") == idx]
    if not matching:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": f"Frame {idx} not found."})
    return matching[0]


@router.post("/approve", status_code=status.HTTP_202_ACCEPTED)
async def approve_storyboard(
    session_id: str,
    current_user: CurrentUser,
    db: DB,
) -> dict:
    from datetime import datetime, timezone

    session = await _get_owned_session(session_id, current_user.id, db)
    _assert_state(session, SessionState.storyboard_review)

    sb = await _get_storyboard(session_id, db)
    sb.approved_at = datetime.now(timezone.utc)
    session.state = SessionState.voice_generating.value
    await db.flush()

    job_id = enqueue_agent("voice", session_id)
    return {"job_id": job_id, "session_id": session_id}


@router.post("/revise", status_code=status.HTTP_202_ACCEPTED)
async def revise_storyboard(
    session_id: str,
    body: StoryboardRevise,
    current_user: CurrentUser,
    db: DB,
) -> dict:
    session = await _get_owned_session(session_id, current_user.id, db)
    _assert_state(session, SessionState.storyboard_review)

    session.state = SessionState.storyboard_generating.value
    await db.flush()

    job_id = enqueue_agent("storyboard", session_id, revision_notes=body.model_dump())
    return {"job_id": job_id, "session_id": session_id}


def _assert_state(session: ProjectSession, *allowed: SessionState) -> None:
    if session.state not in [s.value for s in allowed]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "invalid_state", "message": f"Not valid in state '{session.state}'."},
        )


async def _get_storyboard(session_id: str, db: DB) -> Storyboard:
    result = await db.execute(
        select(Storyboard).where(Storyboard.session_id == session_id)
    )
    sb = result.scalar_one_or_none()
    if sb is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "not_ready", "message": "Storyboard not yet generated."},
        )
    return sb
