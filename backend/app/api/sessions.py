from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DB
from app.ids import make_id
from app.models import ProjectSession, SessionState
from app.queue.jobs import enqueue_agent
from app.schemas.session import CostProjection, SessionCreate, SessionOut

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: SessionCreate,
    current_user: CurrentUser,
    db: DB,
) -> SessionOut:
    from app.speeches.catalog import get_speech_by_id

    if get_speech_by_id(body.speech_id) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "unknown_speech",
                "message": f"'{body.speech_id}' is not in the supported speech catalog.",
                "retryable": False,
            },
        )

    session = ProjectSession(
        id=make_id("sess"),
        user_id=current_user.id,
        speech_id=body.speech_id,
        accuracy_tier=body.accuracy_tier,
        ux_choices=body.ux_choices.model_dump(),
        state=SessionState.created.value,
    )
    db.add(session)
    await db.flush()
    return SessionOut.model_validate(session)


@router.get("/{session_id}", response_model=SessionOut)
async def get_session(
    session_id: str,
    current_user: CurrentUser,
    db: DB,
) -> SessionOut:
    session = await _get_owned_session(session_id, current_user.id, db)
    return SessionOut.model_validate(session)


@router.get("/{session_id}/cost_projection", response_model=CostProjection)
async def cost_projection(
    session_id: str,
    current_user: CurrentUser,
    db: DB,
) -> CostProjection:
    from app.receipts.generator import compute_cost_projection

    session = await _get_owned_session(session_id, current_user.id, db)
    return await compute_cost_projection(session, db)


# ── helpers ──────────────────────────────────────────────────────────────────

async def _get_owned_session(
    session_id: str,
    user_id: str,
    db: DB,
) -> ProjectSession:
    result = await db.execute(
        select(ProjectSession).where(
            ProjectSession.id == session_id,
            ProjectSession.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "session_not_found", "message": "Session not found."},
        )
    return session
