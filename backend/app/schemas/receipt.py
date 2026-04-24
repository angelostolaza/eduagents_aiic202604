from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ReceiptRunDetail(BaseModel):
    agent: str
    model: str
    model_version: str = ""
    started_at: datetime | None = None
    ended_at: datetime | None = None
    tokens_in: int = 0
    tokens_in_cached: int = 0
    tokens_out: int = 0
    images: int = 0
    seconds_generated: int = 0
    cost_cents: int = 0
    status: str = "ok"
    note: str = ""


class ReceiptArtifact(BaseModel):
    type: str
    url: str
    content_hash: str = ""
    size_bytes: int = 0
    duration_s: float | None = None
    version: int | None = None
    idx: int | None = None


class ReceiptTotals(BaseModel):
    gross_cents: int
    credits_cents: int = 0
    net_cents: int
    net_usd: str


class ConfidenceSummary(BaseModel):
    verified: int = 0
    approximated: int = 0
    speculative: int = 0
    highest_risk_element: str = ""


class Receipt(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: str
    user_id: str
    speech_id: str
    created_at: datetime
    completed_at: datetime | None
    ux: dict[str, Any]
    runs: list[ReceiptRunDetail]
    credits_applied: list[dict[str, Any]] = []
    totals: ReceiptTotals
    confidence_summary: ConfidenceSummary
    artifacts: list[ReceiptArtifact]
