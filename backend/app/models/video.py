from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class VideoRender(Base, TimestampMixin):
    __tablename__ = "video_render"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("project_session.id"), nullable=False, unique=True
    )
    asset_url: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Inherits the highest-risk confidence tag from any constituent shot
    final_confidence: Mapped[str] = mapped_column(
        String(20), nullable=False, default="speculative"
    )
    manifest: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    rendered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    session: Mapped[Any] = relationship(
        "ProjectSession", back_populates="video_render", lazy="noload"
    )
