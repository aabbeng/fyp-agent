"""Live open-access scholarly search backed by OpenAlex and Crossref."""

from __future__ import annotations

import html
import hashlib
import os
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlparse

import httpx

CROSSREF_WORKS_URL = "https://api.crossref.org/works"
UNPAYWALL_WORK_URL = "https://api.unpaywall.org/v2"
OPENALEX_WORKS_URL = "https://api.openalex.org/works"
BING_WEB_SEARCH_URL = "https://www.bing.com/search"
MIN_PUBLICATION_YEAR = 2022
MAX_PUBLICATION_YEAR = 2026
ALLOWED_SCHOLARLY_TYPES = {
    "journal-article", "proceedings-article", "posted-content",
    "article", "preprint", "review",
    "web-article", "technical-documentation", "research-webpage",
}


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


def _openalex_abstract(inverted_index: Any) -> str:
    if not isinstance(inverted_index, dict) or not inverted_index:
        return ""
    positions = [position for values in inverted_index.values() for position in values]
    if not positions:
        return ""
    words = [""] * (max(positions) + 1)
    for word, values in inverted_index.items():
        for position in values:
            if 0 <= position < len(words):
                words[position] = word
    return " ".join(word for word in words if word).strip()


def normalize_openalex_item(item: dict[str, Any]) -> dict[str, Any] | None:
    title = _plain_text(str(item.get("title") or item.get("display_name") or ""))
    year = item.get("publication_year")
    location = item.get("best_oa_location") or item.get("primary_location") or {}
    source = location.get("source") or {}
    open_url = str(location.get("pdf_url") or location.get("landing_page_url") or "").strip()
    open_access = item.get("open_access") or {}
    raw_doi = str(item.get("doi") or "").strip()
    identifier = re.sub(r"^https?://doi\.org/", "", raw_doi, flags=re.I).lower()
    if not identifier:
        openalex_id = str(item.get("id") or "").rstrip("/").split("/")[-1].lower()
        identifier = f"openalex:{openalex_id}" if openalex_id else ""
    if not title or not identifier or not isinstance(year, int):
        return None
    authors = [
        str((authorship.get("author") or {}).get("display_name") or "").strip()
        for authorship in item.get("authorships") or []
    ]
    return {
        "doi": identifier,
        "title": title,
        "authors": [author for author in authors if author],
        "year": year,
        "venue": _plain_text(str(source.get("display_name") or "")),
        "url": open_url,
        "open_access_url": open_url,
        "is_open_access": bool(open_access.get("is_oa") and open_url),
        "abstract": _openalex_abstract(item.get("abstract_inverted_index")),
        "paper_type": str(item.get("type") or ""),
        "citation_count": int(item.get("cited_by_count") or 0),
        "score": float(item.get("relevance_score") or 0),
        "source": "OpenAlex",
    }


def _open_access_location(client: httpx.Client, doi: str, email: str) -> str:
    if not email:
        return ""
    try:
        response = client.get(f"{UNPAYWALL_WORK_URL}/{doi}", params={"email": email})
        response.raise_for_status()
        record = response.json()
    except (httpx.HTTPError, ValueError):
        return ""
    if not record.get("is_oa"):
        return ""
    location = record.get("best_oa_location") or {}
    return str(location.get("url_for_pdf") or location.get("url") or "").strip()


def meets_thesis_source_rules(paper: dict[str, Any]) -> bool:
    year = paper.get("year")
    return bool(
        isinstance(year, int)
        and MIN_PUBLICATION_YEAR <= year <= MAX_PUBLICATION_YEAR
        and paper.get("paper_type") in ALLOWED_SCHOLARLY_TYPES
        and (paper.get("is_open_access") or paper.get("source_kind") == "web")
        and str(paper.get("open_access_url", "")).startswith("https://")
    )


def _web_year(text: str, published: str = "") -> int | None:
    if published:
        try:
            year = parsedate_to_datetime(published).year
            if MIN_PUBLICATION_YEAR <= year <= MAX_PUBLICATION_YEAR:
                return year
        except (TypeError, ValueError, OverflowError):
            pass
    matches = re.findall(r"(?<!\d)(202[2-6])(?!\d)", text)
    return int(matches[0]) if matches else None


def _page_publication_year(client: httpx.Client, url: str, fallback: str) -> int | None:
    try:
        response = client.get(url, timeout=10)
        response.raise_for_status()
        sample = response.text[:500_000]
    except httpx.HTTPError:
        return _web_year(fallback)
    patterns = (
        r'"datePublished"\s*:\s*"(202[2-6])',
        r'(?:article:published_time|datePublished|publish-date)[^>]{0,160}(202[2-6])',
        r'<time[^>]+datetime=["\'](202[2-6])',
    )
    for pattern in patterns:
        match = re.search(pattern, sample, flags=re.I)
        if match:
            return int(match.group(1))
    return _web_year(f"{url} {fallback}")


def _web_result_relevant(query: str, title: str, description: str) -> bool:
    ignored = {"and", "the", "for", "with", "from", "into", "using", "multi", "step"}
    query_terms = {
        term for term in re.findall(r"[a-z0-9]+", query.lower())
        if len(term) >= 3 and term not in ignored
    }
    haystack = f"{title} {description}".lower()
    matched = {term for term in query_terms if term in haystack}
    return len(matched) >= min(2, len(query_terms))


def search_web_sources(query: str, rows: int = 2) -> list[dict[str, Any]]:
    params = {
        "q": f'{query} after:{MIN_PUBLICATION_YEAR - 1} before:{MAX_PUBLICATION_YEAR + 1}',
        "format": "rss",
        "count": max(rows * 3, 8),
    }
    headers = {"User-Agent": "Mozilla/5.0 (compatible; XENGResearch/0.4)"}
    with httpx.Client(timeout=15, follow_redirects=True, headers=headers) as client:
        response = client.get(BING_WEB_SEARCH_URL, params=params)
        response.raise_for_status()
        root = ET.fromstring(response.text)
        results = []
        for item in root.findall(".//item"):
            title = _plain_text(item.findtext("title", ""))
            url = item.findtext("link", "").strip()
            description = _plain_text(item.findtext("description", ""))
            published = item.findtext("pubDate", "")
            if (
                not title or not url.startswith("https://")
                or not _web_result_relevant(query, title, description)
            ):
                continue
            year = _page_publication_year(client, url, f"{published} {title} {description}")
            if not year:
                continue
            host = urlparse(url).netloc.lower().removeprefix("www.")
            identifier = "web:" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
            credibility = "community web article"
            if host.endswith((".edu", ".gov", ".ac.uk")):
                credibility = "institutional web source"
            elif any(marker in host for marker in ("docs.", "developer.", "research.")):
                credibility = "technical or research documentation"
            results.append({
                "doi": identifier,
                "title": title,
                "authors": [host],
                "year": year,
                "venue": host,
                "url": url,
                "open_access_url": url,
                "is_open_access": True,
                "abstract": description,
                "paper_type": "web-article",
                "citation_count": 0,
                "score": 0,
                "source": "Web discovery",
                "source_kind": "web",
                "credibility": credibility,
            })
            if len(results) >= rows:
                break
    return results


def _search_openalex(query: str, rows: int, email: str) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "search": query,
        "filter": (
            f"from_publication_date:{MIN_PUBLICATION_YEAR}-01-01,"
            f"to_publication_date:{MAX_PUBLICATION_YEAR}-12-31,is_oa:true"
        ),
        "per-page": min(rows * 2, 40),
    }
    if email:
        params["mailto"] = email
    api_key = os.getenv("OPENALEX_API_KEY", "").strip()
    if api_key:
        params["api_key"] = api_key
    headers = {"User-Agent": f"XENG/0.4 ({email or 'open-access thesis research'})"}
    with httpx.Client(timeout=20, follow_redirects=True, headers=headers) as client:
        response = client.get(OPENALEX_WORKS_URL, params=params)
        response.raise_for_status()
        items = response.json()["results"]
    papers = []
    seen: set[str] = set()
    for item in items:
        paper = normalize_openalex_item(item)
        if paper and paper["doi"] not in seen and meets_thesis_source_rules(paper):
            papers.append(paper)
            seen.add(paper["doi"])
    return papers[:rows]


def _search_crossref(query: str, rows: int, email: str) -> list[dict[str, Any]]:
    if not email:
        return []
    params: dict[str, Any] = {
        "query.bibliographic": query,
        "rows": min(rows * 2, 40),
        "filter": f"from-pub-date:{MIN_PUBLICATION_YEAR}-01-01,until-pub-date:{MAX_PUBLICATION_YEAR}-12-31",
        "select": "DOI,title,author,published,published-print,published-online,issued,container-title,URL,abstract,type,is-referenced-by-count,score",
    }
    if email:
        params["mailto"] = email
    headers = {"User-Agent": f"fyp-agent/0.3 ({email or 'academic research prototype'})"}
    with httpx.Client(timeout=15, follow_redirects=True, headers=headers) as client:
        response = client.get(CROSSREF_WORKS_URL, params=params)
        response.raise_for_status()
        items = response.json()["message"]["items"]
        papers = []
        seen: set[str] = set()
        for item in items:
            paper = normalize_crossref_item(item)
            if not paper or paper["doi"] in seen:
                continue
            paper["open_access_url"] = _open_access_location(client, paper["doi"], email)
            paper["is_open_access"] = bool(paper["open_access_url"])
            if meets_thesis_source_rules(paper):
                paper["url"] = paper["open_access_url"]
                papers.append(paper)
                seen.add(paper["doi"])
    return papers[:rows]


def search_papers(query: str, rows: int = 8) -> list[dict[str, Any]]:
    query = query.strip()
    if len(query) < 3:
        raise ResearchSearchError("Enter at least three characters")
    rows = max(1, min(rows, 20))
    email = os.getenv("CROSSREF_MAILTO", "").strip()
    errors: list[str] = []
    academic: list[dict[str, Any]] = []
    academic_rows = max(1, rows - 1)
    try:
        academic = _search_openalex(query, academic_rows, email)
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        errors.append(f"OpenAlex: {exc}")
    if not academic:
        try:
            academic = _search_crossref(query, academic_rows, email)
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            errors.append(f"Crossref: {exc}")
    web_sources: list[dict[str, Any]] = []
    try:
        web_sources = search_web_sources(query, min(2, rows))
    except (httpx.HTTPError, ET.ParseError, ValueError) as exc:
        errors.append(f"Web: {exc}")
    combined = []
    seen: set[str] = set()
    for paper in (*academic, *web_sources):
        if paper["doi"] not in seen:
            combined.append(paper)
            seen.add(paper["doi"])
    if combined:
        return combined[:rows]
    if errors:
        raise ResearchSearchError("; ".join(errors))
    return []
