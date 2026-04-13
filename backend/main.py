from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import time

from models import Event, EventMetadata
from storage import EventStorage
from detection import (
    compute_session_status,
    compute_session_metrics,
    generate_insights,
)

app = FastAPI(title="Sploink Agent Monitor", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

storage = EventStorage()


# ---------------------------------------------------------------------------
# Request schema (more lenient than the internal Event model)
# ---------------------------------------------------------------------------

class EventRequest(BaseModel):
    session_id: Optional[str] = "default"
    timestamp: Optional[float] = None
    step: Optional[int] = None
    action: Optional[str] = None
    input: Optional[str] = ""
    output: Optional[str] = ""
    metadata: Optional[Dict[str, Any]] = None


def _build_event(req: EventRequest) -> Event:
    meta = req.metadata or {}
    return Event(
        session_id=req.session_id or "default",
        timestamp=req.timestamp or time.time(),
        step=req.step,
        action=req.action or "unknown",
        input=req.input or "",
        output=req.output or "",
        metadata=EventMetadata(
            file=meta.get("file"),
            status=meta.get("status", "success"),
        ),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/events", summary="Ingest a single agent event")
async def ingest_event(event_req: EventRequest):
    event = _build_event(event_req)
    stored = storage.store_event(event)
    return {
        "status": "accepted" if stored else "duplicate",
        "session_id": event.session_id,
        "step": event.step,
    }


@app.post("/events/batch", summary="Ingest multiple events")
async def ingest_batch(events: List[EventRequest]):
    results = []
    for req in events:
        event = _build_event(req)
        stored = storage.store_event(event)
        results.append({
            "session_id": event.session_id,
            "step": event.step,
            "status": "accepted" if stored else "duplicate",
        })
    return {"results": results, "count": len(events)}


@app.get("/sessions", summary="List all sessions with status")
async def list_sessions():
    session_ids = storage.get_all_sessions()
    sessions = []
    for sid in session_ids:
        events = storage.get_session_events(sid)
        if not events:
            continue
        metrics = compute_session_metrics(events)
        status, issues = compute_session_status(events)
        sessions.append({
            "session_id": sid,
            "status": status,
            "total_steps": metrics["total_steps"],
            "success_count": metrics["success_count"],
            "failure_count": metrics["failure_count"],
            "success_rate": round(metrics["success_rate"], 3),
            "action_distribution": metrics["action_distribution"],
            "issues": issues,
            "last_updated": storage.get_session_last_updated(sid),
        })
    return {"sessions": sessions}


@app.get("/sessions/{session_id}", summary="Get full session detail")
async def get_session(session_id: str):
    events = storage.get_session_events(session_id)
    if not events:
        raise HTTPException(status_code=404, detail="Session not found")

    metrics = compute_session_metrics(events)
    status, issues = compute_session_status(events)
    insights = generate_insights(events, status, issues)

    return {
        "session_id": session_id,
        "status": status,
        **metrics,
        "events": events,
        "issues": issues,
        "insights": insights,
        "last_updated": storage.get_session_last_updated(session_id),
    }


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": time.time()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
