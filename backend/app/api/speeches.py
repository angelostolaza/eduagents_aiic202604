from __future__ import annotations

from fastapi import APIRouter

from app.speeches.catalog import SPEECH_CATALOG

router = APIRouter(prefix="/speeches", tags=["speeches"])


@router.get("")
async def list_speeches() -> list[dict]:
    """Return the curated speech catalog. No auth required."""
    return [
        {
            "id": s["id"],
            "figure": s["figure"],
            "title": s["title"],
            "year": s["year"],
            "era": s["era"],
            "description": s["description"],
            "has_recording": s.get("has_recording", False),
        }
        for s in SPEECH_CATALOG
    ]
