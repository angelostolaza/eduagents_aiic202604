"""Queue helpers — enqueue RQ jobs for each agent."""
from __future__ import annotations

from functools import lru_cache
from typing import Any

import redis
from rq import Queue

from app.config import get_settings


@lru_cache(maxsize=1)
def _get_queue() -> Queue:
    settings = get_settings()
    conn = redis.Redis.from_url(settings.redis_url)
    return Queue("pipeline", connection=conn)


def enqueue_agent(agent_name: str, session_id: str, **kwargs: Any) -> str:
    """Enqueue an agent job and return the job ID."""
    q = _get_queue()
    job = q.enqueue(
        "app.queue.jobs._run_agent",
        agent_name,
        session_id,
        kwargs,
        job_timeout=600,
        result_ttl=86400,
        failure_ttl=86400,
    )
    return job.id


def _run_agent(agent_name: str, session_id: str, kwargs: dict[str, Any]) -> None:
    """RQ worker entry point — loads session state from DB and runs the agent."""
    import asyncio
    from app.queue.jobs_impl import run_agent_for_session

    asyncio.run(run_agent_for_session(agent_name, session_id, kwargs))
