"""Persistent storage for research, thesis drafts, approvals, and automation."""

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
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

SECTION_TITLES = {
    "literature_review": "Literature Review",
    "methodology": "Methodology",
    "expected_results": "Expected Results",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def backend_name() -> str:
    return "postgresql" if DATABASE_URL else "sqlite"


class DatabaseSession:
    def __init__(self, connection: Any, postgres: bool) -> None:
        self.connection = connection
        self.postgres = postgres

    def execute(self, sql: str, params: tuple[Any, ...] = ()):
        statement = sql.replace("?", "%s") if self.postgres else sql
        return self.connection.execute(statement, params)

    def executescript(self, sql: str) -> None:
        if not self.postgres:
            self.connection.executescript(sql)
            return
        for statement in (part.strip() for part in sql.split(";")):
            if statement:
                self.connection.execute(statement)


@contextmanager
def connect():
    if DATABASE_URL:
        from psycopg import connect as pg_connect
        from psycopg.rows import dict_row

        connection = pg_connect(DATABASE_URL, row_factory=dict_row, connect_timeout=12)
        try:
            with connection:
                connection.execute("CREATE SCHEMA IF NOT EXISTS xeng")
                connection.execute("SET search_path TO xeng")
                yield DatabaseSession(connection, postgres=True)
        finally:
            connection.close()
        return

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield DatabaseSession(connection, postgres=False)
    finally:
        connection.close()


def initialize_database() -> None:
    id_column = "BIGSERIAL PRIMARY KEY" if DATABASE_URL else "INTEGER PRIMARY KEY AUTOINCREMENT"
    with connect() as connection:
        connection.executescript(
            f"""
            CREATE TABLE IF NOT EXISTS papers (
                id {id_column}, doi TEXT NOT NULL UNIQUE, title TEXT NOT NULL,
                authors_json TEXT NOT NULL, year INTEGER, venue TEXT, url TEXT,
                abstract TEXT, paper_type TEXT, source TEXT NOT NULL,
                relevance TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '',
                added_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS research_candidates (
                id {id_column}, doi TEXT NOT NULL UNIQUE, title TEXT NOT NULL,
                paper_json TEXT NOT NULL, query TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending', first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS thesis_sections (
                section_key TEXT PRIMARY KEY, title TEXT NOT NULL,
                content TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'draft',
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS methodology_gate (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                status TEXT NOT NULL DEFAULT 'locked', approved_at TEXT,
                notes TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS activities (
                id {id_column}, agent TEXT NOT NULL, action TEXT NOT NULL,
                details TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS job_runs (
                id {id_column}, job_name TEXT NOT NULL, status TEXT NOT NULL,
                details TEXT NOT NULL DEFAULT '', started_at TEXT NOT NULL,
                finished_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_candidates_status_seen
                ON research_candidates (status, last_seen_at);
            CREATE INDEX IF NOT EXISTS idx_job_runs_name_started
                ON job_runs (job_name, started_at);
            CREATE INDEX IF NOT EXISTS idx_activities_created
                ON activities (created_at);
            """
        )
        for section_key, title in SECTION_TITLES.items():
            connection.execute(
                """
                INSERT INTO thesis_sections (section_key, title, content, status, updated_at)
                VALUES (?, ?, '', 'draft', ?)
                ON CONFLICT(section_key) DO NOTHING
                """,
                (section_key, title, _now()),
            )
        connection.execute(
            """
            INSERT INTO methodology_gate (id, status, notes)
            VALUES (1, 'locked', '') ON CONFLICT(id) DO NOTHING
            """
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
                title = excluded.title, authors_json = excluded.authors_json,
                year = excluded.year, venue = excluded.venue, url = excluded.url,
                abstract = excluded.abstract, paper_type = excluded.paper_type,
                relevance = excluded.relevance, notes = excluded.notes
            """,
            (
                doi, paper["title"], json.dumps(paper.get("authors", [])),
                paper.get("year"), paper.get("venue", ""), paper.get("url", ""),
                paper.get("abstract", ""), paper.get("paper_type", ""),
                paper.get("source", "Crossref"), relevance.strip(), notes.strip(), _now(),
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


def save_candidate(paper: dict[str, Any], query: str) -> tuple[dict[str, Any], bool]:
    doi = paper["doi"].strip().lower()
    now = _now()
    with connect() as connection:
        existing = connection.execute(
            "SELECT id FROM research_candidates WHERE doi = ?", (doi,)
        ).fetchone()
        connection.execute(
            """
            INSERT INTO research_candidates
                (doi, title, paper_json, query, status, first_seen_at, last_seen_at)
            VALUES (?, ?, ?, ?, 'pending', ?, ?)
            ON CONFLICT(doi) DO UPDATE SET
                title = excluded.title, paper_json = excluded.paper_json,
                query = excluded.query, last_seen_at = excluded.last_seen_at
            """,
            (doi, paper["title"], json.dumps(paper), query.strip(), now, now),
        )
        row = connection.execute(
            "SELECT * FROM research_candidates WHERE doi = ?", (doi,)
        ).fetchone()
    candidate = dict(row)
    candidate["paper"] = json.loads(candidate.pop("paper_json"))
    return candidate, existing is None


def list_candidates(status: str = "pending", limit: int = 50) -> list[dict[str, Any]]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT * FROM research_candidates WHERE status = ? "
            "ORDER BY last_seen_at DESC LIMIT ?",
            (status, limit),
        ).fetchall()
    candidates = []
    for row in rows:
        candidate = dict(row)
        candidate["paper"] = json.loads(candidate.pop("paper_json"))
        candidates.append(candidate)
    return candidates


def approve_candidate(doi: str) -> dict[str, Any]:
    normalized = doi.strip().lower()
    with connect() as connection:
        row = connection.execute(
            "SELECT paper_json FROM research_candidates WHERE doi = ? AND status = 'pending'",
            (normalized,),
        ).fetchone()
    if not row:
        raise ValueError("Pending research candidate not found")
    paper = save_paper(json.loads(dict(row)["paper_json"]))
    with connect() as connection:
        connection.execute(
            "UPDATE research_candidates SET status = 'approved', last_seen_at = ? WHERE doi = ?",
            (_now(), normalized),
        )
    return paper


def start_job(job_name: str) -> int:
    with connect() as connection:
        cursor = connection.execute(
            "INSERT INTO job_runs (job_name, status, details, started_at) "
            "VALUES (?, 'running', '', ?)",
            (job_name, _now()),
        )
        if connection.postgres:
            row = connection.execute("SELECT LASTVAL() AS id").fetchone()
            return int(dict(row)["id"])
        return int(cursor.lastrowid)


def finish_job(job_id: int, status: str, details: str) -> None:
    if status not in {"completed", "failed"}:
        raise ValueError("Invalid job status")
    with connect() as connection:
        connection.execute(
            "UPDATE job_runs SET status = ?, details = ?, finished_at = ? WHERE id = ?",
            (status, details, _now(), job_id),
        )


def list_job_runs(limit: int = 20) -> list[dict[str, Any]]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT * FROM job_runs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(row) for row in rows]


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
            "UPDATE thesis_sections SET content = ?, status = ?, updated_at = ? "
            "WHERE section_key = ?",
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
