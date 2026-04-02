from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.share import router as share_router
from app.core.config import settings

logger = logging.getLogger(__name__)

# LangSmith tracing — must be set in os.environ before LangChain is imported.
if settings.LANGCHAIN_TRACING_V2 and settings.LANGCHAIN_API_KEY:
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_API_KEY", settings.LANGCHAIN_API_KEY)
    os.environ.setdefault("LANGCHAIN_PROJECT", settings.LANGCHAIN_PROJECT)
    logger.info(f"LangSmith tracing enabled — project: {settings.LANGCHAIN_PROJECT}")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if not settings.skip_chunker_warmup:
        from app.services.chunking_service import get_semantic_chunker

        get_semantic_chunker()
    yield


app = FastAPI(
    title="Wizly",
    description="Your AI Twin",
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler — log the full error server-side, never expose details to clients."""
    logger.exception(f"Unhandled error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(share_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/debug/checkpoint/{session_id}")
async def debug_checkpoint(session_id: str) -> dict:
    """Inspect the LangGraph MemorySaver checkpoint for a given session_id (thread_id)."""
    from app.graph.graph import get_compiled_graph

    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": session_id}}
    try:
        state = await graph.aget_state(config)
        if not state or not state.values:
            return {"session_id": session_id, "checkpoint": None, "message": "No checkpoint found"}
        messages = state.values.get("messages", [])
        return {
            "session_id": session_id,
            "checkpoint_exists": True,
            "message_count": len(messages),
            "last_messages": messages[-3:] if messages else [],
            "summary": state.values.get("summary") or None,
            "retrieved_chunk_count": len(state.values.get("retrieved_chunks", [])),
        }
    except Exception as exc:
        return {"session_id": session_id, "error": str(exc)}


@app.get("/debug/qdrant")
async def debug_qdrant() -> dict:
    """Inspect Qdrant collection point counts and a sample of payload (without full text)."""
    from app.services.vector_store_service import (
        GLOBAL_COLLECTION,
        PRIVATE_COLLECTION,
        VectorStoreService,
    )

    vs = VectorStoreService()
    result: dict[str, object] = {}
    for name in (GLOBAL_COLLECTION, PRIVATE_COLLECTION):
        try:
            count = vs.collection_point_count(name)
            sample_ids, sample_metadata = vs.collection_sample_payloads(name, limit=5)
            result[name] = {
                "count": count,
                "sample_ids": sample_ids,
                "sample_metadata": sample_metadata,
            }
        except Exception as exc:
            result[name] = {"error": str(exc)}
    return result
