from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class VoiceTrack(Base, TimestampMixin):
    __tablename__ = "voice_track"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("project_session.id"), nullable=False, unique=True
    )
    asset_url: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # "recording" = cloned from verifiable audio; "description" = reconstructed from accounts
    method: Mapped[str] = mapped_column(String(20), nullable=False, default="description")
    manifest: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    confidence_summary: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    session: Mapped[Any] = relationship(
        "ProjectSession", back_populates="voice_track", lazy="noload"
    )
