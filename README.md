# Sploink — AI Agent Monitor

A real-time telemetry and behavioral analysis system for AI agents.

---

## Quick Start

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
python main.py
# → http://localhost:8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

### 3. Run a Simulation

```bash
cd backend

# Single scenarios
python backend/agent.py --scenario normal
python backend/agent.py --scenario loop
python backend/agent.py --scenario drift
python backend/agent.py --scenario failure

# All scenarios interleaved concurrently
python backend/agent.py --scenario mixed

# Custom session ID
python backend/agent.py --scenario loop --session my-debug-session

# Custom backend URL
python backend/agent.py --scenario normal --url http://localhost:8000
```

---

## Architecture Overview

```
┌──────────────┐     POST /events      ┌────────────────┐
│ Agent / CLI  │ ──────────────────►   │  FastAPI        │
│ (agent.py)   │                       │  (main.py)      │
└──────────────┘                       │                 │
                                       │  ┌───────────┐  │
                                       │  │ Detection  │  │
                                       │  │ (detection │  │
                                       │  │  .py)      │  │
                                       │  └───────────┘  │
                                       │                 │
                                       │  ┌───────────┐  │
                                       │  │  SQLite   │  │
                                       │  │ (storage  │  │
                                       │  │  .py)     │  │
                                       │  └───────────┘  │
                                       └────────────────┘
                                                │
                                         GET /sessions
                                                │
                                       ┌────────────────┐
                                       │  Next.js UI    │
                                       │  (port 3000)   │
                                       └────────────────┘
```

### Component Breakdown

| File | Role |
|---|---|
| `backend/main.py` | FastAPI app, REST endpoints |
| `backend/models.py` | Pydantic data models with validation |
| `backend/storage.py` | SQLite persistence, deduplication |
| `backend/detection.py` | Loop / drift / failure detection |
| `backend/agent.py` | CLI simulator (4 scenarios) |
| `frontend/app/page.tsx` | Session list with live polling |
| `frontend/app/sessions/[id]/page.tsx` | Session detail + timeline |

---

## Detection Logic

### Loop Detection

**Algorithm**: Sliding window (last 8 events) pairwise similarity.

For each pair of same-action-type events, compute:
```
similarity = 0.4 × (action_type_match) + 0.6 × jaccard(input_tokens_A, input_tokens_B)
```

**Thresholds**:
- Average same-type similarity > **0.55**
- Most-repeated action appears **≥ 3×** in the window

**Why 0.55?** Pure string equality misses real loops with parameter variation (e.g., `--depth 800` vs `--depth 1000`). Jaccard on token sets catches semantic repetition. 0.55 balances sensitivity vs false positives from legitimate repeated file reads.

---

### Drift Detection

**Algorithm**: Compare both semantic content *and* workspace context between the first and second halves of a session.
```
token_overlap = jaccard(tokens(first_half), tokens(second_half))
path_overlap = jaccard(path_roots(first_half), path_roots(second_half))
```
- **Tokens** are extracted from `input + output` (stop-words removed).
- **Path roots** are extracted from file paths (e.g., `auth/... → auth`, `pipeline/... → pipeline`).

---

**Detection Logic**

Drift is flagged only when **semantic shift AND contextual shift** are present:

- **Strong Drift**
  - `token_overlap < 0.10`
  - `path_overlap < 0.25`

- **Moderate Drift**
  - `token_overlap < 0.15`
  - `path_overlap < 0.20`
  - dominant action type changes (e.g., `read_file → write_file`)
  - action distribution overlap is low

---

**Why This Change?**

Earlier logic used only token overlap (`< 0.20`), which caused **false positives**:
- Normal workflows (setup → coding → testing → commit) naturally change vocabulary
- This incorrectly flagged healthy sessions as drifting

---

**Final Rationale**

- **Token overlap** captures *semantic intent change*
- **Path overlap** captures *context / project shift*
- Combining both ensures:
  - ✅ Real drift is detected (e.g., `auth/ → pipeline/`)
  - ❌ Normal task progression is NOT flagged as drift

- This makes drift detection more aligned with real-world agent behavior.
---

### Failure Detection

Two independent signals (either triggers):

1. **Consecutive failures ≥ 3** — tail-scan from most recent event
2. **Failure rate > 60%** over the last 10 events (min 5 events required)

**Why 3 consecutive?** A single retry is normal; two can be a transient error. Three consecutive failures signals the agent is stuck in a retry loop without backoff.

**Why 60% / 10 events?** Prevents noise from a single bad step. 60% is materially above random failure rate for a healthy agent (~5-15%).

---

## Data Storage Choice

**SQLite** — rationale:
- No external dependencies, works on any machine
- Handles concurrent writes via threading lock
- UNIQUE constraint on `event_hash` provides automatic deduplication
- Survives process restarts (unlike pure in-memory)
- Performant for the event volumes typical of single-host agent monitoring

---

## Real-time vs Batch Processing

**Hybrid approach**:
- Events are ingested and stored immediately (real-time)
- Detection runs on-demand at query time (batch over session history)

**Why not streaming detection?** For behavioral patterns like drift and loops, you need a window of context. Streaming detection would require maintaining rolling state per session, adding complexity without significant benefit for the latency requirements of a monitoring dashboard.

---

## Edge Cases Handled

| Case | Handling |
|---|---|
| Duplicate events | MD5 hash on `session_id + step + action + input[:80]`, UNIQUE constraint rejects duplicates |
| Out-of-order events | Stored by insert order, queried `ORDER BY timestamp ASC, step ASC` |
| Missing fields | All fields optional in `EventRequest`, defaults applied in `_build_event()` |
| Partial metadata | `EventMetadata` only extracts known fields, ignores unknown |
| High-frequency bursts | SQLite write lock + batch endpoint `/events/batch` |
| Concurrent sessions | Session-scoped queries, no cross-session state |
| Very fast bursts | Small random jitter in simulator; batch endpoint available |
| Mixed session streams | All events partitioned by `session_id` |

---

## API Reference

```
POST /events           Ingest single event
POST /events/batch     Ingest multiple events
GET  /sessions         List all sessions with status
GET  /sessions/{id}    Full session detail + detection results
GET  /health           Health check
```

---

## Trade-offs (Time Constraints)

- SQLite used instead of a full database for simplicity
- Polling used instead of real-time streaming
- Heuristic-based detection instead of ML models
---
