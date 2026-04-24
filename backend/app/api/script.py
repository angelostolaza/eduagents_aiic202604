from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DB
from app.api.sessions import _get_owned_session
from app.models import ProjectSession, ScriptPackage, SessionState
from app.queue.jobs import enqueue_agent
from app.schemas.script import ScriptPackageOut, ScriptRevise

router = APIRouter(prefix="/sessions/{session_id}/script", tags=["script"])


@router.post("/start", status_code=status.HTTP_202_ACCEPTED)
async def start_scripting(
    session_id: str,
    current_user: CurrentUser,
    db: DB,
) -> dict:
    session = await _get_owned_session(session_id, current_user.id, db)
    _assert_state(session, SessionState.scripting, SessionState.scripting_review)

    session.state = SessionState.scripting.value
    await db.flush()

    job_id = enqueue_agent("scripting", session_id)
    return {"job_id": job_id, "session_id": session_id}


@router.get("", response_model=ScriptPackageOut)
async def get_script(
    session_id: str,
    current_user: CurrentUser,
    db: DB,
) -> ScriptPackageOut:
    await _get_owned_session(session_id, current_user.id, db)
    pkg = await _get_package(session_id, db)
    return ScriptPackageOut.model_validate(pkg)


@router.post("/approve", status_code=status.HTTP_202_ACCEPTED)
async def approve_script(
    session_id: str,
    current_user: CurrentUser,
    db: DB,
) -> dict:
    from datetime import datetime, timezone

    session = await _get_owned_session(session_id, current_user.id, db)
    _assert_state(session, SessionState.scripting_review)

    pkg = await _get_package(session_id, db)
    pkg.status = "approved"
    pkg.reviewed_at = datetime.now(timezone.utc)
    session.state = SessionState.seed_generating.value
    await db.flush()

    job_id = enqueue_agent("seed_image", session_id)
    return {"job_id": job_id, "session_id": session_id}


@router.post("/revise", status_code=status.HTTP_202_ACCEPTED)
async def revise_script(
    session_id: str,
    body: ScriptRevise,
    current_user: CurrentUser,
    db: DB,
) -> dict:
    session = await _get_owned_session(session_id, current_user.id, db)
    _assert_state(session, SessionState.scripting_review)

    session.state = SessionState.scripting.value
    await db.flush()

    job_id = enqueue_agent("scripting", session_id, revision_notes=body.model_dump())
    return {"job_id": job_id, "session_id": session_id}


def _assert_state(session: ProjectSession, *allowed: SessionState) -> None:
    if session.state not in [s.value for s in allowed]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "invalid_state", "message": f"Not valid in state '{session.state}'."},
        )


async def _get_package(session_id: str, db: DB) -> ScriptPackage:
    result = await db.execute(
        select(ScriptPackage).where(ScriptPackage.session_id == session_id)
    )
    pkg = result.scalar_one_or_none()
    if pkg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_ready", "message": "Scripting has not completed yet."},
        )
    return pkg
