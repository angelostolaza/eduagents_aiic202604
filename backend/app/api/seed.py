from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DB
from app.api.sessions import _get_owned_session
from app.models import SeedImage, ProjectSession, SessionState
from app.queue.jobs import enqueue_agent
from app.schemas.seed import SeedImageOut, SeedRevise

router = APIRouter(prefix="/sessions/{session_id}/seed", tags=["seed"])


@router.post("/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_seed(
    session_id: str,
    current_user: CurrentUser,
    db: DB,
) -> dict:
    session = await _get_owned_session(session_id, current_user.id, db)
    _assert_state(session, SessionState.seed_generating, SessionState.seed_review)

    session.state = SessionState.seed_generating.value
    await db.flush()

    job_id = enqueue_agent("seed_image", session_id)
    return {"job_id": job_id, "session_id": session_id}


@router.get("", response_model=SeedImageOut)
async def get_seed(
    session_id: str,
    current_user: CurrentUser,
    db: DB,
) -> SeedImageOut:
    await _get_owned_session(session_id, current_user.id, db)
    img = await _get_current_seed(session_id, db)
    return SeedImageOut.model_validate(img)


@router.get("/versions", response_model=list[SeedImageOut])
async def list_seed_versions(
    session_id: str,
    current_user: CurrentUser,
    db: DB,
) -> list[SeedImageOut]:
    await _get_owned_session(session_id, current_user.id, db)
    result = await db.execute(
        select(SeedImage)
        .where(SeedImage.session_id == session_id)
        .order_by(SeedImage.version)
    )
    return [SeedImageOut.model_validate(r) for r in result.scalars()]


@router.post("/approve", status_code=status.HTTP_202_ACCEPTED)
async def approve_seed(
    session_id: str,
    current_user: CurrentUser,
    db: DB,
) -> dict:
    from datetime import datetime, timezone

    session = await _get_owned_session(session_id, current_user.id, db)
    _assert_state(session, SessionState.seed_review)

    img = await _get_current_seed(session_id, db)
    img.is_approved = True
    img.approved_at = datetime.now(timezone.utc)
    session.state = SessionState.storyboard_generating.value
    await db.flush()

    job_id = enqueue_agent("storyboard", session_id)
    return {"job_id": job_id, "session_id": session_id}


@router.post("/revise", status_code=status.HTTP_202_ACCEPTED)
async def revise_seed(
    session_id: str,
    body: SeedRevise,
    current_user: CurrentUser,
    db: DB,
) -> dict:
    session = await _get_owned_session(session_id, current_user.id, db)
    _assert_state(session, SessionState.seed_review)

    session.state = SessionState.seed_generating.value
    await db.flush()

    job_id = enqueue_agent("seed_image", session_id, revision_notes=body.model_dump())
    return {"job_id": job_id, "session_id": session_id}


def _assert_state(session: ProjectSession, *allowed: SessionState) -> None:
    if session.state not in [s.value for s in allowed]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "invalid_state", "message": f"Not valid in state '{session.state}'."},
        )


async def _get_current_seed(session_id: str, db: DB) -> SeedImage:
    result = await db.execute(
        select(SeedImage)
        .where(SeedImage.session_id == session_id)
        .order_by(SeedImage.version.desc())
        .limit(1)
    )
    img = result.scalar_one_or_none()
    if img is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_ready", "message": "Seed image not yet generated."},
        )
    return img
