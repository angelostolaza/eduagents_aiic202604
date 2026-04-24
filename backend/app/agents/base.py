"""Base agent: shared run() scaffolding, cost-cap guard, audit logging."""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


class BaseAgent(ABC):
    agent_name: str = "base"
    default_model: str = "claude-3-5-sonnet-20241022"

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute the agent and record an audit run."""
        from app.db import AsyncSessionLocal

        session_id = state.get("session_id", "")
        started_at = time.time()

        async with AsyncSessionLocal() as db:
            await self._check_cost_cap(session_id, db)
            try:
                result = await self._execute(state, db)
                status = "ok"
                error_msg = None
            except Exception as exc:
                status = "failed"
                error_msg = str(exc)
                result = {}
                raise
            finally:
                ended_at = time.time()
                await self._record_run(
                    session_id=session_id,
                    db=db,
                    status=status,
                    started_at=started_at,
                    ended_at=ended_at,
                    cost_cents=result.get("cost_cents", 0),
                    tokens_in=result.get("tokens_in", 0),
                    tokens_out=result.get("tokens_out", 0),
                    notes=error_msg,
                    extras=result.get("extras", {}),
                )
                await db.commit()

        return result

    @abstractmethod
    async def _execute(self, state: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
        """Agent-specific work. Must return a dict with at least 'cost_cents'."""
        ...

    async def _check_cost_cap(self, session_id: str, db: AsyncSession) -> None:
        """Block execution if the kill switch is set or the session has already failed."""
        from app.redis_client import get_redis

        r = get_redis()
        kill_value = await r.get("global:kill_switch")
        if kill_value == b"1":
            raise RuntimeError("Pipeline paused by admin kill switch.")

    async def _record_run(
        self,
        *,
        session_id: str,
        db: AsyncSession,
        status: str,
        started_at: float,
        ended_at: float,
        cost_cents: int = 0,
        tokens_in: int = 0,
        tokens_out: int = 0,
        notes: str | None = None,
        extras: dict | None = None,
    ) -> None:
        from datetime import datetime, timezone

        from app.ids import make_id
        from app.models.audit import AgentRun

        run = AgentRun(
            id=make_id("run"),
            session_id=session_id,
            agent=self.agent_name,
            model=self.default_model,
            started_at=datetime.fromtimestamp(started_at, tz=timezone.utc),
            ended_at=datetime.fromtimestamp(ended_at, tz=timezone.utc),
            status=status,
            cost_cents=cost_cents,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            notes=notes,
            extras=extras or {},
        )
        db.add(run)
