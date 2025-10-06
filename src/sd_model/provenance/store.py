from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Iterable


def init_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS artifacts (
                id INTEGER PRIMARY KEY,
                kind TEXT NOT NULL,
                path TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS connections (
                id INTEGER PRIMARY KEY,
                artifact_id INTEGER NOT NULL,
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                sign TEXT NOT NULL,
                FOREIGN KEY(artifact_id) REFERENCES artifacts(id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS loops (
                id INTEGER PRIMARY KEY,
                artifact_id INTEGER NOT NULL,
                nodes_json TEXT NOT NULL,
                loop_type TEXT NOT NULL,
                length INTEGER NOT NULL,
                FOREIGN KEY(artifact_id) REFERENCES artifacts(id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS evidence (
                id INTEGER PRIMARY KEY,
                item_type TEXT NOT NULL, -- 'connection' | 'loop' | 'artifact'
                item_id INTEGER NOT NULL,
                source TEXT NOT NULL,    -- 'parser_llm' | 'interpret_llm' | 'theory_validation_llm' | 'reviewer' | 'simulation'
                ref TEXT,
                confidence REAL,
                note TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def add_artifact(db_path: Path, kind: str, path: str, sha256: str) -> int:
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO artifacts(kind, path, sha256) VALUES (?, ?, ?)", (kind, path, sha256))
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def record_connections(db_path: Path, artifact_id: int, connections: Iterable[dict]) -> None:
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        rows = [(artifact_id, c.get("from", ""), c.get("to", ""), c.get("relationship", "")) for c in connections]
        cur.executemany("INSERT INTO connections(artifact_id, source, target, sign) VALUES (?, ?, ?, ?)", rows)
        conn.commit()
    finally:
        conn.close()


def record_loops(db_path: Path, artifact_id: int, loops: Iterable[dict]) -> None:
    import json as _json
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        rows = [(artifact_id, _json.dumps(l.get("nodes", [])), l.get("type", ""), int(l.get("length", 0))) for l in loops]
        cur.executemany("INSERT INTO loops(artifact_id, nodes_json, loop_type, length) VALUES (?, ?, ?, ?)", rows)
        conn.commit()
    finally:
        conn.close()


def add_evidence(db_path: Path, item_type: str, item_id: int, source: str, ref: str | None, confidence: float | None, note: str | None) -> int:
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO evidence(item_type, item_id, source, ref, confidence, note) VALUES (?, ?, ?, ?, ?, ?)",
            (item_type, item_id, source, ref, confidence, note),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()

