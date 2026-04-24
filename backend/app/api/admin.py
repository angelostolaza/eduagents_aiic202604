from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.api.deps import AdminUser, DB
from app.models import ProjectSession, UserAccount

router = APIRouter(prefix="/admin", tags=["admin"])


class SubmissionAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(default="", max_length=500)


class KillSwitchAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    paused: bool


@router.post("/submissions/{session_id}/approve", status_code=status.HTTP_202_ACCEPTED)
async def approve_submission(
    session_id: str,
    _admin: AdminUser,
    db: DB,
) -> dict:
    from app.queue.jobs import enqueue_agent

    result = await db.execute(
        select(ProjectSession).where(ProjectSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(404, {"code": "not_found", "message": "Session not found."})

    job_id = enqueue_agent("research", session_id)
    return {"approved": True, "job_id": job_id}


@router.post("/submissions/{session_id}/reject")
async def reject_submission(
    session_id: str,
    body: SubmissionAction,
    _admin: AdminUser,
    db: DB,
) -> dict:
    result = await db.execute(
        select(ProjectSession).where(ProjectSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(404, {"code": "not_found", "message": "Session not found."})

    session.state = "failed"
    session.error_message = f"Rejected by admin: {body.reason}"
    await db.flush()
    return {"rejected": True}


@router.post("/users/{user_id}/freeze")
async def freeze_user(
    user_id: str,
    _admin: AdminUser,
    db: DB,
) -> dict:
    result = await db.execute(
        select(UserAccount).where(UserAccount.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(404, {"code": "not_found", "message": "User not found."})

    user.is_frozen = True
    await db.flush()
    return {"frozen": True, "user_id": user_id}


@router.post("/kill_switch")
async def kill_switch(
    body: KillSwitchAction,
    _admin: AdminUser,
) -> dict:
    from app.redis_client import get_redis

    r = get_redis()
    await r.set("global:kill_switch", "1" if body.paused else "0")
    return {"paused": body.paused}
