from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import UXChoices


class SessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    speech_id: str = Field(..., min_length=1, max_length=128)
    accuracy_tier: int = Field(2, ge=1, le=4)
    ux_choices: UXChoices = Field(default_factory=UXChoices)


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    speech_id: str
    state: str
    accuracy_tier: int
    ux_choices: dict[str, Any]
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class CostProjection(BaseModel):
    session_id: str
    current_state: str
    spent_cents: int
    projected_remaining_cents: int
    projected_total_cents: int
    currency: str = "USD"
    breakdown: list[dict[str, Any]] = []
