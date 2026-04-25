"""Research Agent — produces a ResearchForm with confidence-tagged fields and a Markdown report."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent


RESEARCH_SYSTEM_PROMPT = """You are a meticulous historical research assistant.
Given a speech (id, figure, year), produce a structured JSON object with the following top-level
keys. For each key, provide: value (string), confidence ("verified"|"approximated"|"speculative"),
and sources (array of citation strings).

Keys to populate:
- figure_name
- birth_year
- death_year
- historical_context
- speech_occasion
- speech_date
- speech_location
- primary_themes (value can be a JSON array encoded as string)
- key_quotes (value: JSON array of {quote, context} encoded as string)
- historical_accuracy_notes

Respond with ONLY the JSON object. No preamble. No markdown fences."""


class ResearchAgent(BaseAgent):
    agent_name = "research"
    default_model = "llama3.2"

    async def _execute(self, state: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
        from app.adapters.ollama import OllamaAdapter
        from app.ids import make_id
        from app.models.research import ResearchForm
        from app.speeches.catalog import get_speech_by_id
        from sqlalchemy import select

        session_id = state["session_id"]
        speech_id = state["speech_id"]
        speech = get_speech_by_id(speech_id)
        if speech is None:
            raise ValueError(f"Unknown speech_id: {speech_id}")

        revision_notes: dict = state.get("seed_revision_notes") or {}

        user_prompt = f"""Speech ID: {speech['id']}
Historical figure: {speech['figure']}
Speech title: {speech['title']}
Year: {speech['year']}
Era: {speech['era']}
Description: {speech['description']}
"""
        if revision_notes:
            user_prompt += f"\n\nRevision notes from editor:\n{json.dumps(revision_notes, indent=2)}"

        adapter = OllamaAdapter()
        response = await adapter.complete(
            system=RESEARCH_SYSTEM_PROMPT,
            user=user_prompt,
            model=self.default_model,
            max_tokens=2000,
        )

        form_data: dict = json.loads(response["content"])

        # Upsert ResearchForm
        existing = (await db.execute(
            select(ResearchForm).where(ResearchForm.session_id == session_id)
        )).scalar_one_or_none()

        if existing:
            existing.fields = form_data
            existing.status = "pending_review"
        else:
            db.add(ResearchForm(
                id=make_id("rf"),
                session_id=session_id,
                fields=form_data,
                status="pending_review",
            ))

        # Generate Markdown report
        report_md = _fields_to_markdown(speech, form_data)

        return {
            "form": form_data,
            "report_url": "",  # set by storage adapter in production
            "report_md": report_md,
            "cost_cents": response.get("cost_cents", 0),
            "tokens_in": response.get("tokens_in", 0),
            "tokens_out": response.get("tokens_out", 0),
        }


def _fields_to_markdown(speech: dict, fields: dict) -> str:
    lines = [
        f"# Research Report: {speech['figure']} — {speech['title']}",
        f"**Year:** {speech['year']}  **Era:** {speech['era']}",
        "",
    ]
    for key, fv in fields.items():
        badge = f"[{fv.get('confidence', '?')}]"
        value = fv.get("value", "")
        sources = fv.get("sources", [])
        lines.append(f"## {key.replace('_', ' ').title()} {badge}")
        lines.append(value)
        if sources:
            lines.append("")
            lines.append("**Sources:**")
            for s in sources:
                lines.append(f"- {s}")
        lines.append("")
    return "\n".join(lines)
