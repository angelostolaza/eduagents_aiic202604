from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SeedImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    asset_url: str
    manifest: dict[str, Any]
    version: int
    is_approved: bool
    approved_at: datetime | None
    created_at: datetime


class SeedRevise(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notes: str = Field(default="", max_length=2000)
    targeted_changes: str = Field(
        default="",
        max_length=2000,
        description="Plain-language description of what to change in the next generation.",
    )
