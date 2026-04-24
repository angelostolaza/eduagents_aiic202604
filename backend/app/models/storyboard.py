from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Storyboard(Base, TimestampMixin):
    """Ordered shot series expanding the seed image via the Shot List.

    ``shots`` is a JSONB array; each element::

        {
            "idx": int,
            "prompt": str,
            "asset_url": str,
            "confidence": "verified" | "approximated" | "speculative",
            "period_source": str | null,
            "timing_start_s": float,
            "timing_end_s": float
        }
    """

    __tablename__ = "storyboard"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("project_session.id"), nullable=False, unique=True
    )
    shots: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    session: Mapped[Any] = relationship(
        "ProjectSession", back_populates="storyboard", lazy="noload"
    )
