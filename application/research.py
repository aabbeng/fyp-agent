"""Live scholarly metadata search backed by the Crossref REST API."""

from __future__ import annotations

import html
import os
import re
from typing import Any

import httpx

CROSSREF_WORKS_URL = "https://api.crossref.org/works"


class ResearchSearchError(RuntimeError):
    pass


def _first(value: Any, default: str = "") -> str:
    if isinstance(value, list) and value:
        return str(value[0])
    return default


def _year(item: dict[str, Any]) -> int | None:
    for field in ("published-print", "published-online", "published", "issued"):
        parts = item.get(field, {}).get("date-parts", [])
        if parts and parts[0]:
            return int(parts[0][0])
    return None


def _authors(item: dict[str, Any]) -> list[str]:
    names = []
    for author in item.get("author", []):
        name = " ".join(
            part for part in (author.get("given", ""), author.get("family", "")) if part
        ).strip()
        if name:
            names.append(name)
    return names


def _plain_text(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", html.unescape(without_tags)).strip()


def normalize_crossref_item(item: dict[str, Any]) -> dict[str, Any] | None:
    doi = str(item.get("DOI", "")).strip().lower()
    title = _plain_text(_first(item.get("title")))
    if not doi or not title:
        return None
    return {
        "doi": doi,
        "title": title,
        "authors": _authors(item),
        "year": _year(item),
        "venue": _plain_text(_first(item.get("container-title"))),
        "url": item.get("URL") or f"https://doi.org/{doi}",
        "abstract": _plain_text(item.get("abstract", "")),
        "paper_type": item.get("type", ""),
        "citation_count": int(item.get("is-referenced-by-count", 0) or 0),
        "score": round(float(item.get("score", 0) or 0), 2),
        "source": "Crossref",
    }


def search_papers(query: str, rows: int = 8) -> list[dict[str, Any]]:
    query = query.strip()
    if len(query) < 3:
        raise ResearchSearchError("Enter at least three characters")
    rows = max(1, min(rows, 20))
    email = os.getenv("CROSSREF_MAILTO", "").strip()
    params: dict[str, Any] = {
        "query.bibliographic": query,
        "rows": rows,
        "select": "DOI,title,author,published,published-print,published-online,issued,container-title,URL,abstract,type,is-referenced-by-count,score",
    }
    if email:
        params["mailto"] = email
    headers = {"User-Agent": f"fyp-agent/0.3 ({email or 'academic research prototype'})"}
    try:
        with httpx.Client(timeout=15, follow_redirects=True, headers=headers) as client:
            response = client.get(CROSSREF_WORKS_URL, params=params)
            response.raise_for_status()
            items = response.json()["message"]["items"]
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        raise ResearchSearchError(f"Paper search failed: {exc}") from exc

    papers = []
    seen: set[str] = set()
    for item in items:
        paper = normalize_crossref_item(item)
        if paper and paper["doi"] not in seen:
            papers.append(paper)
            seen.add(paper["doi"])
    return papers
