from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ScriptPackage(Base, TimestampMixin):
    """Output of the Scripting Agent.

    Contains four structured artifacts:
    - visual_brief:       seed-image spec (pose, lighting, setting, period details)
    - shot_list:          ordered array of shot objects
    - performance_notes:  TTS/voice delivery cues tied to transcript timings
    - accuracy_manifest:  which research fields are load-bearing for the script
    """

    __tablename__ = "script_package"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("project_session.id"), nullable=False, unique=True
    )
    visual_brief: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    shot_list: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    performance_notes: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    accuracy_manifest: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    report_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    session: Mapped[Any] = relationship(
        "ProjectSession", back_populates="script_package", lazy="noload"
    )
