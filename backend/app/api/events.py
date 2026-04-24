from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.api.deps import CurrentUser, DB
from app.api.sessions import _get_owned_session
from app.redis_client import get_redis

router = APIRouter(prefix="/sessions/{session_id}/events", tags=["events"])


@router.get("")
async def session_events(
    session_id: str,
    current_user: CurrentUser,
    db: DB,
) -> EventSourceResponse:
    await _get_owned_session(session_id, current_user.id, db)

    async def stream() -> AsyncGenerator[dict, None]:
        r = get_redis()
        pubsub = r.pubsub()
        await pubsub.subscribe(f"session:{session_id}:events")
        try:
            # Send a heartbeat so the connection is established immediately
            yield {"event": "connected", "data": json.dumps({"session_id": session_id})}
            while True:
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=25.0)
                if msg is None:
                    # Heartbeat to keep the connection alive
                    yield {"event": "heartbeat", "data": "{}"}
                    continue
                payload = msg.get("data", "{}")
                data = json.loads(payload) if isinstance(payload, str) else {}
                yield {"event": data.get("type", "update"), "data": json.dumps(data)}
                # Terminal states: close the stream
                if data.get("type") in ("rendered", "failed"):
                    break
        finally:
            await pubsub.unsubscribe(f"session:{session_id}:events")
            await pubsub.aclose()

    return EventSourceResponse(stream())
