"""Shared Pydantic v2 types used across schemas."""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict


class ConfidenceTag(str, Enum):
    verified = "verified"
    approximated = "approximated"
    speculative = "speculative"


class ConfidenceField(BaseModel):
    """Wrapper for any research field that carries a confidence tag."""

    model_config = ConfigDict(extra="forbid")

    value: Any
    confidence: ConfidenceTag
    sources: list[dict[str, str]] = []


class UXChoices(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accuracy_tier: int = 2  # 1–4
    aspect_ratio: str = "16:9"
    perspective: str = "audience_pov"  # audience_pov | multi_shot
    target_length_s: int = 45
    color_grade: str = "natural"
    shot_rhythm: str = "moderate"  # slow | moderate | fast


class ErrorResponse(BaseModel):
    """Standard error envelope — no stack traces, no internal paths."""

    model_config = ConfigDict(extra="forbid")

    error: ErrorDetail


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str = ""
    retryable: bool = False
