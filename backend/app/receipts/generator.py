"""Receipt generator — builds structured Receipt, Markdown, and CostProjection."""
from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from app.models import AgentRun, ProjectSession
    from sqlalchemy.ext.asyncio import AsyncSession


async def build_receipt(
    session: "ProjectSession",
    runs: Sequence["AgentRun"],
    db: "AsyncSession",
) -> "Receipt":
    from app.schemas.receipt import (
        Receipt,
        ReceiptArtifact,
        ReceiptRunDetail,
        ReceiptTotals,
        ConfidenceSummary,
    )
    from app.speeches.catalog import get_speech_by_id

    speech = get_speech_by_id(session.speech_id) or {}

    run_details: list[ReceiptRunDetail] = []
    total_cost = 0
    total_tokens_in = 0
    total_tokens_out = 0

    for r in runs:
        run_details.append(ReceiptRunDetail(
            agent=r.agent,
            model=r.model,
            status=r.status,
            cost_cents=r.cost_cents or 0,
            tokens_in=r.tokens_in or 0,
            tokens_out=r.tokens_out or 0,
            seconds_generated=r.seconds_generated,
            started_at=r.started_at,
            ended_at=r.ended_at,
        ))
        total_cost += r.cost_cents or 0
        total_tokens_in += r.tokens_in or 0
        total_tokens_out += r.tokens_out or 0

    artifacts = _gather_artifacts(session, runs)
    confidence = _compute_confidence(runs)

    return Receipt(
        session_id=session.id,
        speech_id=session.speech_id,
        speech_title=speech.get("title", ""),
        historical_figure=speech.get("figure", ""),
        accuracy_tier=session.accuracy_tier,
        ux_choices=session.ux_choices or {},
        runs=run_details,
        artifacts=artifacts,
        totals=ReceiptTotals(
            total_cost_cents=total_cost,
            total_tokens_in=total_tokens_in,
            total_tokens_out=total_tokens_out,
        ),
        confidence_summary=confidence,
        completed_at=session.completed_at,
    )


def render_receipt_markdown(receipt: "Receipt") -> str:
    lines = [
        f"# Production Receipt — {receipt.historical_figure}: {receipt.speech_title}",
        f"**Session:** `{receipt.session_id}`  |  **Accuracy tier:** {receipt.accuracy_tier}",
        "",
        "## Agent Runs",
        "| Agent | Model | Status | Cost (¢) | Tokens In | Tokens Out |",
        "|-------|-------|--------|-----------|-----------|------------|",
    ]
    for r in receipt.runs:
        lines.append(
            f"| {r.agent} | {r.model} | {r.status} | {r.cost_cents} | {r.tokens_in} | {r.tokens_out} |"
        )
    lines += [
        "",
        "## Artifacts",
    ]
    for a in receipt.artifacts:
        lines.append(f"- **{a.type}**: [{a.label}]({a.url})")
    lines += [
        "",
        "## Totals",
        f"- **Total cost:** {receipt.totals.total_cost_cents}¢",
        f"- **Total tokens in:** {receipt.totals.total_tokens_in:,}",
        f"- **Total tokens out:** {receipt.totals.total_tokens_out:,}",
        "",
        "## Confidence Summary",
        f"- Verified: {receipt.confidence_summary.verified}",
        f"- Approximated: {receipt.confidence_summary.approximated}",
        f"- Speculative: {receipt.confidence_summary.speculative}",
        f"- Highest risk element: {receipt.confidence_summary.highest_risk_element}",
    ]
    return "\n".join(lines)


async def compute_cost_projection(
    session: "ProjectSession",
    db: "AsyncSession",
) -> "CostProjection":
    from sqlalchemy import select, func
    from app.models import AgentRun
    from app.schemas.session import CostProjection

    result = await db.execute(
        select(func.sum(AgentRun.cost_cents)).where(AgentRun.session_id == session.id)
    )
    spent = result.scalar() or 0

    # Very rough per-agent estimates for remaining stages
    stage_estimates: dict[str, int] = {
        "research": 5,
        "scripting": 8,
        "seed_image": 3,
        "storyboard": 30,
        "voice": 4,
        "video": 80,
    }

    # Determine which agents have already run
    run_result = await db.execute(
        select(AgentRun.agent).where(AgentRun.session_id == session.id, AgentRun.status == "ok")
    )
    completed_agents = {row[0] for row in run_result}

    remaining = sum(v for k, v in stage_estimates.items() if k not in completed_agents)
    projected_total = spent + remaining

    breakdown = [
        {"stage": k, "estimated_cents": v, "completed": k in completed_agents}
        for k, v in stage_estimates.items()
    ]

    return CostProjection(
        spent_cents=spent,
        projected_remaining_cents=remaining,
        projected_total_cents=projected_total,
        breakdown=breakdown,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _gather_artifacts(session: "ProjectSession", runs: Sequence["AgentRun"]) -> list:
    from app.schemas.receipt import ReceiptArtifact

    artifacts: list[ReceiptArtifact] = []
    base = f"/api/v1/sessions/{session.id}"
    artifacts.append(ReceiptArtifact(type="research_json", label="Research Form", url=f"{base}/research"))
    artifacts.append(ReceiptArtifact(type="script_json", label="Script Package", url=f"{base}/script"))
    artifacts.append(ReceiptArtifact(type="seed_image", label="Seed Image", url=f"{base}/seed"))
    artifacts.append(ReceiptArtifact(type="storyboard", label="Storyboard", url=f"{base}/storyboard"))
    artifacts.append(ReceiptArtifact(type="voice", label="Narration", url=f"{base}/voice"))
    artifacts.append(ReceiptArtifact(type="video", label="Final Video", url=f"{base}/video"))
    return artifacts


def _compute_confidence(runs: Sequence["AgentRun"]) -> "ConfidenceSummary":
    from app.schemas.receipt import ConfidenceSummary

    # Confidence data would come from the video render manifest in a full implementation
    return ConfidenceSummary(
        verified=0,
        approximated=0,
        speculative=0,
        highest_risk_element="N/A",
    )
