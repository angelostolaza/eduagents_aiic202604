from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class AgentRun(Base):
    """Per-agent run record — the audit log and the source of truth for the receipt."""

    __tablename__ = "agent_run"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("project_session.id"), nullable=False, index=True
    )
    agent: Mapped[str] = mapped_column(String(40), nullable=False)
    model: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    model_version: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="running"
    )  # running | ok | failed | fallback
    tokens_in: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_in_cached: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    images: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    seconds_generated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Extra JSON bag: characters generated (voice), notes, fallback info, etc.
    extras: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    session: Mapped[Any] = relationship(
        "ProjectSession", back_populates="agent_runs", lazy="noload"
    )
