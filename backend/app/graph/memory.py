from __future__ import annotations

import logging

from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)

_checkpointer: MemorySaver | None = None


def get_checkpointer() -> MemorySaver:
    """Return a shared in-memory checkpointer.

    For production, replace with PostgresSaver backed by the app's async DB
    session once langgraph-checkpoint-postgres is stable.
    """
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = MemorySaver()
        logger.info("LangGraph MemorySaver checkpointer initialised")
    return _checkpointer
