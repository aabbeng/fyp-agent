"""Small SQLite store for research evidence, thesis drafts, and approvals."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.getenv("FYP_AGENT_DB", REPOSITORY_ROOT / "runtime" / "fyp-agent.db"))

SECTION_TITLES = {
    "literature_review": "Literature Review",
    "methodology": "Methodology",
    "expected_results": "Expected Results",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_database() -> None:
    with connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doi TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                authors_json TEXT NOT NULL,
                year INTEGER,
                venue TEXT,
                url TEXT,
                abstract TEXT,
                paper_type TEXT,
                source TEXT NOT NULL,
                relevance TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                added_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS thesis_sections (
                section_key TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'draft',
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS methodology_gate (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                status TEXT NOT NULL DEFAULT 'locked',
                approved_at TEXT,
                notes TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent TEXT NOT NULL,
                action TEXT NOT NULL,
                details TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        for section_key, title in SECTION_TITLES.items():
            connection.execute(
                """
                INSERT OR IGNORE INTO thesis_sections
                    (section_key, title, content, status, updated_at)
                VALUES (?, ?, '', 'draft', ?)
                """,
                (section_key, title, _now()),
            )
        connection.execute(
            "INSERT OR IGNORE INTO methodology_gate (id, status) VALUES (1, 'locked')"
        )


def log_activity(agent: str, action: str, details: str) -> None:
    with connect() as connection:
        connection.execute(
            "INSERT INTO activities (agent, action, details, created_at) VALUES (?, ?, ?, ?)",
            (agent, action, details, _now()),
        )


def list_activities(limit: int = 20) -> list[dict[str, Any]]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT * FROM activities ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(row) for row in rows]


def save_paper(paper: dict[str, Any], relevance: str = "", notes: str = "") -> dict[str, Any]:
    doi = paper["doi"].strip().lower()
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO papers
                (doi, title, authors_json, year, venue, url, abstract, paper_type,
                 source, relevance, notes, added_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(doi) DO UPDATE SET
                title = excluded.title,
                authors_json = excluded.authors_json,
                year = excluded.year,
                venue = excluded.venue,
                url = excluded.url,
                abstract = excluded.abstract,
                paper_type = excluded.paper_type,
                relevance = excluded.relevance,
                notes = excluded.notes
            """,
            (
                doi,
                paper["title"],
                json.dumps(paper.get("authors", [])),
                paper.get("year"),
                paper.get("venue", ""),
                paper.get("url", ""),
                paper.get("abstract", ""),
                paper.get("paper_type", ""),
                paper.get("source", "Crossref"),
                relevance.strip(),
                notes.strip(),
                _now(),
            ),
        )
        row = connection.execute("SELECT * FROM papers WHERE doi = ?", (doi,)).fetchone()
    result = dict(row)
    result["authors"] = json.loads(result.pop("authors_json"))
    return result


def list_papers() -> list[dict[str, Any]]:
    with connect() as connection:
        rows = connection.execute("SELECT * FROM papers ORDER BY added_at DESC").fetchall()
    papers = []
    for row in rows:
        paper = dict(row)
        paper["authors"] = json.loads(paper.pop("authors_json"))
        papers.append(paper)
    return papers


def get_sections() -> list[dict[str, Any]]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT * FROM thesis_sections ORDER BY CASE section_key "
            "WHEN 'literature_review' THEN 1 WHEN 'methodology' THEN 2 ELSE 3 END"
        ).fetchall()
    return [dict(row) for row in rows]


def get_section(section_key: str) -> dict[str, Any] | None:
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM thesis_sections WHERE section_key = ?", (section_key,)
        ).fetchone()
    return dict(row) if row else None


def save_section(section_key: str, content: str, status: str = "draft") -> dict[str, Any]:
    if section_key not in SECTION_TITLES:
        raise ValueError("Unknown thesis section")
    with connect() as connection:
        connection.execute(
            """
            UPDATE thesis_sections
            SET content = ?, status = ?, updated_at = ?
            WHERE section_key = ?
            """,
            (content.strip(), status, _now(), section_key),
        )
    result = get_section(section_key)
    assert result is not None
    return result


def methodology_status() -> dict[str, Any]:
    with connect() as connection:
        row = connection.execute("SELECT * FROM methodology_gate WHERE id = 1").fetchone()
    return dict(row)


def set_methodology_status(status: str, notes: str = "") -> dict[str, Any]:
    if status not in {"locked", "approved"}:
        raise ValueError("Invalid methodology status")
    approved_at = _now() if status == "approved" else None
    with connect() as connection:
        connection.execute(
            "UPDATE methodology_gate SET status = ?, approved_at = ?, notes = ? WHERE id = 1",
            (status, approved_at, notes.strip()),
        )
    return methodology_status()


initialize_database()
