"""LangGraph node functions.

Each node:
1. Reads the relevant session data from Postgres.
2. Calls the appropriate agent.
3. Writes results back to Postgres.
4. Publishes an SSE event to Redis.
5. Returns a partial SessionState update.

Nodes are designed to be idempotent: re-running the same node for the same
session_id is safe.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

log = logging.getLogger(__name__)


def _run_sync(coro: Any) -> Any:
    """Run a coroutine from a sync context (LangGraph nodes are called sync)."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


# ── Research ──────────────────────────────────────────────────────────────────

def node_research(state: dict) -> dict:
    from app.agents.research import ResearchAgent

    session_id = state["session_id"]
    log.info("node_research start", extra={"session_id": session_id})

    try:
        result = _run_sync(ResearchAgent().run(state))
        _run_sync(_publish("research_complete", session_id, {"state": "research_review"}))
        return {
            "research_form": result.get("form", {}),
            "research_report_url": result.get("report_url", ""),
            "current_state": "research_review",
            "total_cost_cents": state.get("total_cost_cents", 0) + result.get("cost_cents", 0),
        }
    except Exception as exc:
        log.exception("node_research failed", extra={"session_id": session_id})
        _run_sync(_publish("failed", session_id, {"error": str(exc)}))
        return {"error": str(exc), "current_state": "failed"}


def route_after_research(state: dict) -> str:
    if state.get("error"):
        return "failed"
    if state.get("research_approved"):
        return "scripting"
    return "wait"


# ── Scripting ─────────────────────────────────────────────────────────────────

def node_scripting(state: dict) -> dict:
    from app.agents.script import ScriptingAgent

    session_id = state["session_id"]
    log.info("node_scripting start", extra={"session_id": session_id})

    try:
        result = _run_sync(ScriptingAgent().run(state))
        _run_sync(_publish("scripting_complete", session_id, {"state": "scripting_review"}))
        return {
            "script_package": result.get("package", {}),
            "script_report_url": result.get("report_url", ""),
            "current_state": "scripting_review",
            "total_cost_cents": state.get("total_cost_cents", 0) + result.get("cost_cents", 0),
        }
    except Exception as exc:
        log.exception("node_scripting failed", extra={"session_id": session_id})
        _run_sync(_publish("failed", session_id, {"error": str(exc)}))
        return {"error": str(exc), "current_state": "failed"}


def route_after_script(state: dict) -> str:
    if state.get("error"):
        return "failed"
    if state.get("script_approved"):
        return "seed_image"
    return "wait"


# ── Seed Image ────────────────────────────────────────────────────────────────

def node_seed_image(state: dict) -> dict:
    from app.agents.seed_image import SeedImageAgent

    session_id = state["session_id"]
    log.info("node_seed_image start", extra={"session_id": session_id})

    try:
        result = _run_sync(SeedImageAgent().run(state))
        _run_sync(_publish("seed_complete", session_id, {"state": "seed_review"}))
        return {
            "seed_image_url": result.get("asset_url", ""),
            "seed_image_version": result.get("version", 1),
            "current_state": "seed_review",
            "total_cost_cents": state.get("total_cost_cents", 0) + result.get("cost_cents", 0),
        }
    except Exception as exc:
        log.exception("node_seed_image failed", extra={"session_id": session_id})
        _run_sync(_publish("failed", session_id, {"error": str(exc)}))
        return {"error": str(exc), "current_state": "failed"}


def route_after_seed(state: dict) -> str:
    if state.get("error"):
        return "failed"
    if state.get("seed_approved"):
        return "storyboard"
    return "wait"


# ── Storyboard ────────────────────────────────────────────────────────────────

def node_storyboard(state: dict) -> dict:
    from app.agents.storyboard import StoryboardAgent

    session_id = state["session_id"]
    log.info("node_storyboard start", extra={"session_id": session_id})

    try:
        result = _run_sync(StoryboardAgent().run(state))
        _run_sync(_publish("storyboard_complete", session_id, {"state": "storyboard_review"}))
        return {
            "storyboard_shots": result.get("shots", []),
            "current_state": "storyboard_review",
            "total_cost_cents": state.get("total_cost_cents", 0) + result.get("cost_cents", 0),
        }
    except Exception as exc:
        log.exception("node_storyboard failed", extra={"session_id": session_id})
        _run_sync(_publish("failed", session_id, {"error": str(exc)}))
        return {"error": str(exc), "current_state": "failed"}


def route_after_storyboard(state: dict) -> str:
    if state.get("error"):
        return "failed"
    if state.get("storyboard_approved"):
        return "voice"
    return "wait"


# ── Voice ─────────────────────────────────────────────────────────────────────

def node_voice(state: dict) -> dict:
    from app.agents.voice import VoiceAgent

    session_id = state["session_id"]
    log.info("node_voice start", extra={"session_id": session_id})

    try:
        result = _run_sync(VoiceAgent().run(state))
        _run_sync(_publish("voice_complete", session_id, {}))
        return {
            "voice_track_url": result.get("asset_url", ""),
            "voice_method": result.get("method", "description"),
            "voice_confidence": result.get("confidence", {}),
            "current_state": "video_generating",
            "total_cost_cents": state.get("total_cost_cents", 0) + result.get("cost_cents", 0),
        }
    except Exception as exc:
        log.exception("node_voice failed", extra={"session_id": session_id})
        _run_sync(_publish("failed", session_id, {"error": str(exc)}))
        return {"error": str(exc), "current_state": "failed"}


# ── Video ─────────────────────────────────────────────────────────────────────

def node_video(state: dict) -> dict:
    from app.agents.video import VideoAgent

    session_id = state["session_id"]
    log.info("node_video start", extra={"session_id": session_id})

    try:
        result = _run_sync(VideoAgent().run(state))
        _run_sync(_publish("rendered", session_id, {"video_url": result.get("asset_url", "")}))
        return {
            "video_url": result.get("asset_url", ""),
            "video_clips": result.get("clips", []),
            "video_final_confidence": result.get("final_confidence", "speculative"),
            "current_state": "rendered",
            "total_cost_cents": state.get("total_cost_cents", 0) + result.get("cost_cents", 0),
        }
    except Exception as exc:
        log.exception("node_video failed", extra={"session_id": session_id})
        _run_sync(_publish("failed", session_id, {"error": str(exc)}))
        return {"error": str(exc), "current_state": "failed"}


# ── Bust (parallel 3D pipeline) ───────────────────────────────────────────────

def node_bust(state: dict) -> dict:
    """Generate a 3D GLB bust for the session's historical figure.

    Runs independently of the main video pipeline. Triggered via the
    /bust/generate API endpoint which enqueues this node directly.
    """
    from app.agents.bust import BustAgent

    session_id = state["session_id"]
    log.info("node_bust start", extra={"session_id": session_id})

    try:
        result = _run_sync(BustAgent().run(state))
        _run_sync(_publish("bust_complete", session_id, {
            "bust_id": result.get("bust_id", ""),
            "glb_url": result.get("glb_url", ""),
            "confidence": "speculative",
        }))
        return {
            "bust_id": result.get("bust_id", ""),
            "bust_glb_url": result.get("glb_url", ""),
            "bust_portrait_url": result.get("portrait_url", ""),
            "bust_method": result.get("method", "triposr"),
            "current_state": state.get("current_state", ""),
            "total_cost_cents": state.get("total_cost_cents", 0) + result.get("cost_cents", 0),
        }
    except Exception as exc:
        log.exception("node_bust failed", extra={"session_id": session_id})
        _run_sync(_publish("bust_failed", session_id, {"error": str(exc)}))
        return {"error": str(exc)}


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _publish(event_type: str, session_id: str, data: dict) -> None:
    from app.redis_client import publish_event

    await publish_event(session_id, event_type, data)
