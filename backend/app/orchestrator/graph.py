"""LangGraph pipeline graph definition.

Each stage corresponds to one agent run. Human-approval gates are implemented
as interrupts: the graph pauses, the API endpoint sets the approval flag in the
checkpoint, and the graph resumes on the next queue job.

For the demo, agents are called synchronously inside their nodes. In production,
nodes enqueue work and check status; LangGraph's durable checkpointing means
restarts don't lose progress.
"""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.orchestrator.nodes import (
    node_bust,
    node_research,
    node_scripting,
    node_seed_image,
    node_storyboard,
    node_video,
    node_voice,
    route_after_research,
    route_after_script,
    route_after_seed,
    route_after_storyboard,
)
from app.orchestrator.state import SessionState


def build_graph() -> StateGraph:
    g = StateGraph(SessionState)

    # ── Nodes ─────────────────────────────────────────────────────────────────
    g.add_node("research",    node_research)
    g.add_node("scripting",   node_scripting)
    g.add_node("seed_image",  node_seed_image)
    g.add_node("storyboard",  node_storyboard)
    g.add_node("voice",       node_voice)
    g.add_node("video",       node_video)
    # Bust runs as a standalone parallel node; entry triggered via the API.
    g.add_node("bust",        node_bust)

    # ── Entry ─────────────────────────────────────────────────────────────────
    g.set_entry_point("research")

    # ── Edges ─────────────────────────────────────────────────────────────────
    # After research: either wait for human approval (END = checkpoint) or route
    # to scripting if already approved (resume from checkpoint).
    g.add_conditional_edges("research", route_after_research, {
        "scripting": "scripting",
        "wait":      END,
        "failed":    END,
    })

    g.add_conditional_edges("scripting", route_after_script, {
        "seed_image": "seed_image",
        "wait":       END,
        "failed":     END,
    })

    g.add_conditional_edges("seed_image", route_after_seed, {
        "storyboard": "storyboard",
        "wait":       END,
        "failed":     END,
    })

    g.add_conditional_edges("storyboard", route_after_storyboard, {
        "voice":   "voice",
        "wait":    END,
        "failed":  END,
    })

    g.add_edge("voice", "video")
    g.add_edge("video", END)

    return g


# Compiled graph singleton (no checkpointer — checkpointing is handled by the
# API layer writing state to Postgres directly for this architecture).
pipeline = build_graph().compile()
