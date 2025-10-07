from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def _ensure_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS provenance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                event TEXT NOT NULL,
                payload TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def log_event(db_path: Path, event: str, payload: Dict[str, Any] | None = None) -> None:
    _ensure_db(db_path)
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO provenance (ts, event, payload) VALUES (?, ?, ?)",
            (
                datetime.utcnow().isoformat() + "Z",
                event,
                json.dumps(payload or {}),
            ),
        )
        conn.commit()
    finally:
        conn.close()

