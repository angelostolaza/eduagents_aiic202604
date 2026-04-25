from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class SessionState(str, Enum):
    created = "created"
    researching = "researching"
    research_review = "research_review"
    scripting = "scripting"
    scripting_review = "scripting_review"
    seed_generating = "seed_generating"
    seed_review = "seed_review"
    storyboard_generating = "storyboard_generating"
    storyboard_review = "storyboard_review"
    voice_generating = "voice_generating"
    video_generating = "video_generating"
    rendered = "rendered"
    failed = "failed"


class ProjectSession(Base, TimestampMixin):
    __tablename__ = "project_session"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("user_account.id"), nullable=False, index=True
    )
    speech_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    state: Mapped[str] = mapped_column(
        String(30), nullable=False, default=SessionState.created.value
    )
    accuracy_tier: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    ux_choices: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped[Any] = relationship(
        "UserAccount", back_populates="sessions", lazy="noload"
    )
    research_form: Mapped[Any | None] = relationship(
        "ResearchForm", back_populates="session", uselist=False, lazy="noload"
    )
    script_package: Mapped[Any | None] = relationship(
        "ScriptPackage", back_populates="session", uselist=False, lazy="noload"
    )
    seed_images: Mapped[list[Any]] = relationship(
        "SeedImage", back_populates="session", lazy="noload"
    )
    storyboard: Mapped[Any | None] = relationship(
        "Storyboard", back_populates="session", uselist=False, lazy="noload"
    )
    voice_track: Mapped[Any | None] = relationship(
        "VoiceTrack", back_populates="session", uselist=False, lazy="noload"
    )
    video_render: Mapped[Any | None] = relationship(
        "VideoRender", back_populates="session", uselist=False, lazy="noload"
    )
    agent_runs: Mapped[list[Any]] = relationship(
        "AgentRun", back_populates="session", lazy="noload"
    )
    bust_assets: Mapped[list[Any]] = relationship(
        "BustAsset", back_populates="session", lazy="noload"
    )
