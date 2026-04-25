"""Async implementation of agent dispatch (called from RQ worker)."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.db import async_session_factory
from app.models import ProjectSession


async def run_agent_for_session(
    agent_name: str,
    session_id: str,
    extra_kwargs: dict[str, Any],
) -> None:
    from app.agents import (
        ResearchAgent, ScriptingAgent, SeedImageAgent,
        StoryboardAgent, VoiceAgent, VideoAgent, BustAgent,
    )

    _AGENTS = {
        "research": ResearchAgent,
        "scripting": ScriptingAgent,
        "seed_image": SeedImageAgent,
        "storyboard": StoryboardAgent,
        "voice": VoiceAgent,
        "video": VideoAgent,
        "bust": BustAgent,
    }

    AgentClass = _AGENTS.get(agent_name)
    if AgentClass is None:
        raise ValueError(f"Unknown agent: {agent_name}")

    async with async_session_factory() as db:
        result = await db.execute(
            select(ProjectSession).where(ProjectSession.id == session_id)
        )
        session_row = result.scalar_one_or_none()
        if session_row is None:
            raise RuntimeError(f"Session {session_id} not found.")

        state: dict[str, Any] = {
            "session_id": session_id,
            "user_id": session_row.user_id,
            "speech_id": session_row.speech_id,
            "accuracy_tier": session_row.accuracy_tier,
            "ux_choices": session_row.ux_choices or {},
            **extra_kwargs,
        }

    agent = AgentClass()
    await agent.run(state)
