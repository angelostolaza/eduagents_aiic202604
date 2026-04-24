from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ResearchFormOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    fields: dict[str, Any]
    report_url: str | None
    status: str
    reviewed_at: datetime | None
    created_at: datetime


class ResearchRevise(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_edits: dict[str, Any] = Field(
        default_factory=dict,
        description="Partial overrides for specific research fields.",
    )
    notes: str = Field(
        default="",
        max_length=2000,
        description="Free-text notes from the reviewer.",
    )
