from __future__ import annotations

import redis.asyncio as aioredis

from app.config import get_settings

settings = get_settings()

_pool: aioredis.ConnectionPool | None = None


def get_pool() -> aioredis.ConnectionPool:
    global _pool
    if _pool is None:
        _pool = aioredis.ConnectionPool.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=50,
        )
    return _pool


def get_redis() -> aioredis.Redis:  # type: ignore[type-arg]
    return aioredis.Redis(connection_pool=get_pool())


async def publish_event(session_id: str, event_type: str, data: dict) -> None:
    """Publish a pipeline event to a Redis pub/sub channel for SSE."""
    import json

    r = get_redis()
    payload = json.dumps({"type": event_type, "session_id": session_id, **data})
    await r.publish(f"session:{session_id}:events", payload)
