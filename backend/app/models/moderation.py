from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ContentModerationLog(Base):
    __tablename__ = "content_moderation_log"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    session_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    stage: Mapped[str] = mapped_column(String(40), nullable=False)
    verdict: Mapped[str] = mapped_column(String(20), nullable=False)  # allow | block
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
