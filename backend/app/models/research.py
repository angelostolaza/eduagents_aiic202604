from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ResearchForm(Base, TimestampMixin):
    """Structured research output from the Research Agent.

    ``fields`` is a JSONB object where each key maps to::

        {
            "value": <any>,
            "confidence": "verified" | "approximated" | "speculative",
            "sources": [{"url": str, "accessed": str, "note": str}]
        }
    """

    __tablename__ = "research_form"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("project_session.id"), nullable=False, unique=True
    )
    fields: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    report_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    session: Mapped[Any] = relationship(
        "ProjectSession", back_populates="research_form", lazy="noload"
    )
