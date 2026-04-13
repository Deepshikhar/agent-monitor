import sqlite3
import json
import hashlib
import threading
from typing import List, Optional

from models import Event


class EventStorage:
    def __init__(self, db_path: str = "events.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    step INTEGER,
                    action TEXT,
                    input TEXT,
                    output TEXT,
                    metadata TEXT,
                    event_hash TEXT UNIQUE
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_session ON events(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp)")

    def _conn(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _event_hash(self, event: Event) -> str:
        inp = (event.input or "")[:80]
        key = f"{event.session_id}:{event.step}:{event.action}:{inp}"
        return hashlib.md5(key.encode()).hexdigest()

    def store_event(self, event: Event) -> bool:
        """Store event, returns False if duplicate"""
        event_hash = self._event_hash(event)
        with self.lock:
            with self._conn() as conn:
                try:
                    conn.execute(
                        """INSERT INTO events
                           (session_id, timestamp, step, action, input, output, metadata, event_hash)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            event.session_id,
                            event.timestamp,
                            event.step,
                            event.action,
                            event.input,
                            event.output,
                            json.dumps(event.metadata.dict() if event.metadata else {}),
                            event_hash,
                        ),
                    )
                    return True
                except sqlite3.IntegrityError:
                    return False  # Duplicate

    def get_session_events(self, session_id: str) -> List[dict]:
        with self._conn() as conn:
            cursor = conn.execute(
                """SELECT session_id, timestamp, step, action, input, output, metadata
                   FROM events WHERE session_id = ?
                   ORDER BY step ASC, timestamp ASC""",
                (session_id,),
            )
            rows = cursor.fetchall()

        events = []
        for row in rows:
            events.append({
                "session_id": row["session_id"],
                "timestamp": row["timestamp"],
                "step": row["step"],
                "action": row["action"],
                "input": row["input"] or "",
                "output": row["output"] or "",
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
            })
        return events

    def get_all_sessions(self) -> List[str]:
        with self._conn() as conn:
            cursor = conn.execute(
                "SELECT DISTINCT session_id FROM events GROUP BY session_id ORDER BY MAX(timestamp) DESC"
            )
            return [row["session_id"] for row in cursor.fetchall()]

    def get_session_last_updated(self, session_id: str) -> float:
        with self._conn() as conn:
            cursor = conn.execute(
                "SELECT MAX(timestamp) as ts FROM events WHERE session_id = ?",
                (session_id,),
            )
            row = cursor.fetchone()
            return row["ts"] if row and row["ts"] else 0.0
