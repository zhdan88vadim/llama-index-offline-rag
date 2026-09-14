import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from . import history
from .rag import build_query_engine, serialize_sources, detect_status
from .schemas import (
    AskRequest, AskResponse,
    HistoryEntry, HistoryListResponse,
    ApiError,
)

log = logging.getLogger("rag.api")
router = APIRouter()


def _engine(request: Request):
    engine = getattr(request.app.state, "engine", None)
    if engine is None:
        raise HTTPException(
            status_code=503,
            detail=ApiError(error="index_not_ready", message="Индекс не готов").model_dump(),
        )
    return engine


@router.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest, request: Request):
    engine = _engine(request)
    t0 = time.monotonic()
    try:
        response = engine.query(payload.question)
    except Exception as e:
        log.exception("query failed")
        raise HTTPException(
            status_code=500,
            detail=ApiError(error="llm_error", message=str(e)).model_dump(),
        )

    duration_ms = int((time.monotonic() - t0) * 1000)
    sources = serialize_sources(response)
    status = detect_status(response.response or "", sources)

    history_id = history.save_qa(
        question=payload.question,
        answer=response.response or "",
        sources=sources,
        model=request.app.state.model_name,
        duration_ms=duration_ms,
        status=status,
    )

    return AskResponse(
        history_id=history_id,
        question=payload.question,
        answer=response.response or "",
        status=status,
        sources=sources,
        model=request.app.state.model_name,
        duration_ms=duration_ms,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/history", response_model=HistoryListResponse)
def list_history(limit: int = 20, offset: int = 0, search: str | None = None):
    items, total = history.list_history(limit=limit, offset=offset, search=search)
    return HistoryListResponse(items=items, total=total)


@router.get("/history/{entry_id}", response_model=HistoryEntry)
def get_history(entry_id: int):
    entry = history.get_qa(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Not found")
    return entry


@router.delete("/history/{entry_id}")
def delete_history(entry_id: int):
    ok = history.delete_qa(entry_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Not found")
    return {"deleted": entry_id}


@router.delete("/history")
def clear_history():
    n = history.clear_history()
    return {"deleted": n}


@router.get("/health")
def health(request: Request):
    return {
        "status": "ok",
        "model": request.app.state.model_name,
        "index_ready": getattr(request.app.state, "engine", None) is not None,
    }
