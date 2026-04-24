"""Shared ID generation utilities."""
from __future__ import annotations

from ulid import ULID


def make_id(prefix: str) -> str:
    """Return a prefixed ULID string, e.g. 'sess_01HWXYZ...'."""
    return f"{prefix}_{ULID()}"
