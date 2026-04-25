from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BustAssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    figure_name: str
    method: str
    status: str
    confidence: str
    portrait_url: str | None
    glb_url: str | None
    error_message: str | None
    manifest: dict[str, Any]
    created_at: datetime


class BustGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    figure_name: str | None = Field(
        default=None,
        max_length=256,
        description="Override the figure name derived from the session's speech.",
    )
    physical_description: str = Field(
        default="period-accurate attire, distinguished appearance",
        max_length=512,
    )
    method: str | None = Field(
        default=None,
        description="Force 'triposr' or 'hunyuan3d'; defaults to server setting.",
    )
