from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from sqlalchemy import select

from app.api.deps import CurrentUser, DB
from app.api.sessions import _get_owned_session
from app.models import AgentRun, ResearchForm, ScriptPackage, SeedImage, Storyboard, VideoRender, VoiceTrack
from app.receipts.generator import build_receipt, render_receipt_markdown

router = APIRouter(prefix="/sessions/{session_id}", tags=["artifacts"])


@router.get("/artifacts")
async def list_artifacts(
    session_id: str,
    current_user: CurrentUser,
    db: DB,
) -> list[dict]:
    await _get_owned_session(session_id, current_user.id, db)
    artifacts: list[dict] = []

    # Research
    rf = (await db.execute(select(ResearchForm).where(ResearchForm.session_id == session_id))).scalar_one_or_none()
    if rf:
        artifacts.append({"type": "research_form_json", "url": f"/api/v1/sessions/{session_id}/research"})
        if rf.report_url:
            artifacts.append({"type": "research_report_md", "url": rf.report_url})

    # Script
    sp = (await db.execute(select(ScriptPackage).where(ScriptPackage.session_id == session_id))).scalar_one_or_none()
    if sp:
        artifacts.append({"type": "script_package_json", "url": f"/api/v1/sessions/{session_id}/script"})
        if sp.report_url:
            artifacts.append({"type": "script_report_md", "url": sp.report_url})

    # Seed images
    seeds = (await db.execute(select(SeedImage).where(SeedImage.session_id == session_id).order_by(SeedImage.version))).scalars().all()
    for s in seeds:
        artifacts.append({"type": "seed_image", "url": s.asset_url, "version": s.version})

    # Storyboard frames
    sb = (await db.execute(select(Storyboard).where(Storyboard.session_id == session_id))).scalar_one_or_none()
    if sb:
        for shot in sb.shots:
            artifacts.append({"type": "storyboard_frame", "idx": shot.get("idx"), "url": shot.get("asset_url", "")})

    # Voice
    vt = (await db.execute(select(VoiceTrack).where(VoiceTrack.session_id == session_id))).scalar_one_or_none()
    if vt:
        artifacts.append({"type": "voice_track", "url": vt.asset_url})

    # Video
    vr = (await db.execute(select(VideoRender).where(VideoRender.session_id == session_id))).scalar_one_or_none()
    if vr:
        artifacts.append({"type": "final_video", "url": vr.asset_url})
        for clip in vr.manifest.get("clips", []):
            artifacts.append({"type": "video_clip", "idx": clip.get("idx"), "url": clip.get("url", "")})

    return artifacts


@router.get("/research/report")
async def get_research_report(
    session_id: str,
    current_user: CurrentUser,
    db: DB,
) -> Response:
    await _get_owned_session(session_id, current_user.id, db)
    rf = (await db.execute(select(ResearchForm).where(ResearchForm.session_id == session_id))).scalar_one_or_none()
    if not rf or not rf.report_url:
        raise HTTPException(404, {"code": "not_ready", "message": "Research report not available."})
    # In production, redirect to signed URL; here return the URL
    return Response(content=rf.report_url, media_type="text/plain")


@router.get("/script/report")
async def get_script_report(
    session_id: str,
    current_user: CurrentUser,
    db: DB,
) -> Response:
    await _get_owned_session(session_id, current_user.id, db)
    sp = (await db.execute(select(ScriptPackage).where(ScriptPackage.session_id == session_id))).scalar_one_or_none()
    if not sp or not sp.report_url:
        raise HTTPException(404, {"code": "not_ready", "message": "Script report not available."})
    return Response(content=sp.report_url, media_type="text/plain")


@router.get("/receipt")
async def get_receipt(
    session_id: str,
    current_user: CurrentUser,
    db: DB,
    format: str = "md",
) -> Response:
    session = await _get_owned_session(session_id, current_user.id, db)
    runs_result = await db.execute(select(AgentRun).where(AgentRun.session_id == session_id))
    runs = runs_result.scalars().all()

    receipt = await build_receipt(session, runs, db)

    if format == "json":
        return Response(
            content=receipt.model_dump_json(indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="receipt-{session_id}.json"'},
        )

    md = render_receipt_markdown(receipt)
    return Response(
        content=md,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="receipt-{session_id}.md"'},
    )


@router.get("/audit")
async def get_audit(
    session_id: str,
    current_user: CurrentUser,
    db: DB,
) -> list[dict]:
    from app.api.deps import require_admin
    from app.models import UserTier

    # Admin-only
    if current_user.tier != UserTier.admin.value:
        raise HTTPException(403, {"code": "forbidden", "message": "Admin access required."})

    await _get_owned_session(session_id, current_user.id, db)
    runs_result = await db.execute(
        select(AgentRun).where(AgentRun.session_id == session_id).order_by(AgentRun.started_at)
    )
    return [
        {
            "id": r.id,
            "agent": r.agent,
            "model": r.model,
            "started_at": r.started_at,
            "ended_at": r.ended_at,
            "status": r.status,
            "cost_cents": r.cost_cents,
            "tokens_in": r.tokens_in,
            "tokens_out": r.tokens_out,
            "notes": r.notes,
            "extras": r.extras,
        }
        for r in runs_result.scalars()
    ]
