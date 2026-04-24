from __future__ import annotations

from enum import Enum

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class UserTier(str, Enum):
    public = "public"
    whitelisted = "whitelisted"
    admin = "admin"


class UserAccount(Base, TimestampMixin):
    __tablename__ = "user_account"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    email: Mapped[str] = mapped_column(
        String(320), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
    tier: Mapped[str] = mapped_column(
        String(20), nullable=False, default=UserTier.public.value
    )
    daily_cap: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    weekly_cap: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    is_frozen: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    sessions: Mapped[list[ProjectSession]] = relationship(  # noqa: F821
        "ProjectSession", back_populates="user", lazy="noload"
    )
