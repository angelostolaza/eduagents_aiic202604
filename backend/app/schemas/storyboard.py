from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StoryboardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    shots: list[Any]
    approved_at: datetime | None
    created_at: datetime


class StoryboardRevise(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shot_edits: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Per-shot revision instructions: [{idx, notes, targeted_changes}]",
    )
    notes: str = Field(default="", max_length=2000)
