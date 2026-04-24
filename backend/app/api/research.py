from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DB
from app.api.sessions import _get_owned_session
from app.models import ProjectSession, ResearchForm, SessionState
from app.queue.jobs import enqueue_agent
from app.schemas.research import ResearchFormOut, ResearchRevise

router = APIRouter(prefix="/sessions/{session_id}/research", tags=["research"])


@router.post("/start", status_code=status.HTTP_202_ACCEPTED)
async def start_research(
    session_id: str,
    current_user: CurrentUser,
    db: DB,
) -> dict:
    session = await _get_owned_session(session_id, current_user.id, db)
    _assert_state(session, SessionState.created, SessionState.research_review)

    session.state = SessionState.researching.value
    await db.flush()

    job_id = enqueue_agent("research", session_id)
    return {"job_id": job_id, "session_id": session_id}


@router.get("", response_model=ResearchFormOut)
async def get_research(
    session_id: str,
    current_user: CurrentUser,
    db: DB,
) -> ResearchFormOut:
    await _get_owned_session(session_id, current_user.id, db)
    form = await _get_form(session_id, db)
    return ResearchFormOut.model_validate(form)


@router.post("/approve", status_code=status.HTTP_202_ACCEPTED)
async def approve_research(
    session_id: str,
    current_user: CurrentUser,
    db: DB,
) -> dict:
    from datetime import datetime, timezone

    session = await _get_owned_session(session_id, current_user.id, db)
    _assert_state(session, SessionState.research_review)

    form = await _get_form(session_id, db)
    form.status = "approved"
    form.reviewed_at = datetime.now(timezone.utc)
    session.state = SessionState.scripting.value
    await db.flush()

    job_id = enqueue_agent("scripting", session_id)
    return {"job_id": job_id, "session_id": session_id}


@router.post("/revise", status_code=status.HTTP_202_ACCEPTED)
async def revise_research(
    session_id: str,
    body: ResearchRevise,
    current_user: CurrentUser,
    db: DB,
) -> dict:
    session = await _get_owned_session(session_id, current_user.id, db)
    _assert_state(session, SessionState.research_review)

    session.state = SessionState.researching.value
    await db.flush()

    job_id = enqueue_agent("research", session_id, revision_notes=body.model_dump())
    return {"job_id": job_id, "session_id": session_id}


# ── helpers ───────────────────────────────────────────────────────────────────

def _assert_state(session: ProjectSession, *allowed: SessionState) -> None:
    if session.state not in [s.value for s in allowed]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "invalid_state",
                "message": f"Action not valid in state '{session.state}'.",
                "retryable": False,
            },
        )


async def _get_form(session_id: str, db: DB) -> ResearchForm:
    result = await db.execute(
        select(ResearchForm).where(ResearchForm.session_id == session_id)
    )
    form = result.scalar_one_or_none()
    if form is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_ready", "message": "Research has not completed yet."},
        )
    return form
