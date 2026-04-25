from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DB
from app.api.sessions import _get_owned_session
from app.models.bust import BustAsset
from app.queue.jobs import enqueue_agent
from app.schemas.bust import BustAssetOut, BustGenerateRequest

router = APIRouter(prefix="/sessions/{session_id}/bust", tags=["bust"])


@router.post("/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_bust(
    session_id: str,
    body: BustGenerateRequest,
    current_user: CurrentUser,
    db: DB,
) -> dict:
    """Enqueue a bust generation job for this session.

    Bust generation runs independently of the main video pipeline and does not
    block or modify the session's primary state machine. Results are stored in
    the BustAsset table and can be retrieved via GET /bust.
    """
    await _get_owned_session(session_id, current_user.id, db)

    kwargs: dict = {}
    if body.figure_name:
        kwargs["figure_name"] = body.figure_name
    if body.physical_description:
        kwargs["physical_description"] = body.physical_description
    if body.method:
        if body.method not in ("triposr", "hunyuan3d"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "invalid_method",
                    "message": "method must be 'triposr' or 'hunyuan3d'.",
                    "retryable": False,
                },
            )
        kwargs["bust_method_override"] = body.method

    job_id = enqueue_agent("bust", session_id, **kwargs)
    return {"job_id": job_id, "session_id": session_id}


@router.get("", response_model=list[BustAssetOut])
async def list_busts(
    session_id: str,
    current_user: CurrentUser,
    db: DB,
) -> list[BustAssetOut]:
    """List all bust assets for this session."""
    await _get_owned_session(session_id, current_user.id, db)
    result = await db.execute(
        select(BustAsset)
        .where(BustAsset.session_id == session_id)
        .order_by(BustAsset.created_at)
    )
    return [BustAssetOut.model_validate(row) for row in result.scalars()]


@router.get("/{bust_id}", response_model=BustAssetOut)
async def get_bust(
    session_id: str,
    bust_id: str,
    current_user: CurrentUser,
    db: DB,
) -> BustAssetOut:
    """Get a single bust asset by ID."""
    await _get_owned_session(session_id, current_user.id, db)
    bust = (await db.execute(
        select(BustAsset)
        .where(BustAsset.id == bust_id)
        .where(BustAsset.session_id == session_id)
    )).scalar_one_or_none()

    if bust is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Bust asset not found.", "retryable": False},
        )
    return BustAssetOut.model_validate(bust)
