from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ScriptPackageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    visual_brief: dict[str, Any]
    shot_list: list[Any]
    performance_notes: dict[str, Any]
    accuracy_manifest: dict[str, Any]
    report_url: str | None
    status: str
    reviewed_at: datetime | None
    created_at: datetime


class ScriptRevise(BaseModel):
    model_config = ConfigDict(extra="forbid")

    targeted_changes: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of targeted change instructions for specific shots or sections.",
    )
    notes: str = Field(default="", max_length=2000)
