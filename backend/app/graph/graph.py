from __future__ import annotations

import logging
from typing import Any, Literal

from langgraph.graph import END, StateGraph

from app.graph.memory import get_checkpointer
from app.graph.nodes import check_summarize, retrieve_node
from app.graph.state import ConversationState

logger = logging.getLogger(__name__)


def _route_after_retrieve(state: ConversationState) -> Literal["summarize_check"]:
    return "summarize_check"


def _route_summarize(state: ConversationState) -> Literal["summarize", "end"]:
    if check_summarize(state):
        return "summarize"
    return "end"


def _pass_through(state: ConversationState) -> dict[str, Any]:
    """Identity node used as a routing checkpoint after retrieve."""
    return {}


def build_graph() -> StateGraph:
    """Build and compile the conversation graph.

    Flow: retrieve -> summarize_check -> (summarize | end)

    Generation is handled via streaming outside the graph in chat_service,
    so the graph manages retrieval, context building, and summarization.
    """
    graph = StateGraph(ConversationState)

    graph.add_node("retrieve", retrieve_node)
    graph.add_node("summarize_check", _pass_through)

    # Lazy import to avoid circular dependency at module level
    from app.graph.nodes import summarize_node

    async def _sync_summarize(state: ConversationState) -> dict[str, Any]:
        return await summarize_node(state)

    graph.add_node("summarize", _sync_summarize)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "summarize_check")
    graph.add_conditional_edges(
        "summarize_check",
        _route_summarize,
        {"summarize": "summarize", "end": END},
    )
    graph.add_edge("summarize", END)

    return graph


_compiled_graph = None


def get_compiled_graph():  # type: ignore[no-untyped-def]
    """Return a compiled graph singleton with checkpointer."""
    global _compiled_graph
    if _compiled_graph is None:
        graph = build_graph()
        _compiled_graph = graph.compile(checkpointer=get_checkpointer())
        logger.info("LangGraph conversation graph compiled")
    return _compiled_graph
