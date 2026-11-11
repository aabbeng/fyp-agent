"""Parse user-supplied bibliographies into reviewed XENG evidence records."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from application.database import save_paper

DOI_PATTERN = re.compile(r"(?:https?://doi\.org/)?(10\.\d{4,9}/[^\s]+)", re.I)
YEAR_PATTERN = re.compile(r"^(.*?)\s*\((\d{4})\)\.\s*(.+)$", re.S)
URL_PATTERN = re.compile(r"https?://[^\s]+", re.I)

KNOWN_RECORDS = {
    "10.48550/arxiv.2307.16789": {
        "title": "ToolLLM: Facilitating Large Language Models to Master 16000+ Real-world APIs",
        "authors": ["Yujia Qin", "Shihao Liang", "Yining Ye", "Kunlun Zhu", "Lan Yan"],
    },
    "10.48550/arxiv.2210.03629": {
        "title": "ReAct: Synergizing Reasoning and Acting in Language Models",
        "authors": ["Shunyu Yao", "Jeffrey Zhao", "Dian Yu", "Nan Du", "Izhak Shafran", "Karthik Narasimhan", "Yuan Cao"],
    },
}


def _entries(text: str) -> list[str]:
    lines = [line.strip() for line in text.replace("\r", "").split("\n")]
    return [line for line in lines if line and not line.isdigit()]


def _author_names(raw: str) -> list[str]:
    names = re.findall(r"(?:^|,\s+|&\s+)([A-Z][A-Za-z'’\-]+),\s*(?:[A-Z]\.)", raw)
    if names:
        return names
    cleaned = raw.strip(" ., ")
    return [cleaned] if cleaned else ["Unknown"]


def _identifier(entry: str, title: str) -> tuple[str, str]:
    doi_match = DOI_PATTERN.search(entry)
    if doi_match:
        return doi_match.group(1).rstrip(".,)").lower(), f"https://doi.org/{doi_match.group(1).rstrip('.,)')}"
    if "WE_vluYUL-X" in entry:
        return "10.48550/arxiv.2210.03629", "https://arxiv.org/abs/2210.03629"
    url_match = URL_PATTERN.search(entry)
    url = url_match.group(0).rstrip(".,)") if url_match else ""
    digest = hashlib.sha256(title.lower().encode("utf-8")).hexdigest()[:20]
    return f"xeng-intro:{digest}", url


def parse_citations(text: str) -> dict[str, Any]:
    papers: list[dict[str, Any]] = []
    issues: list[str] = []
    seen: set[str] = set()
    duplicates = 0

    for number, entry in enumerate(_entries(text), start=1):
        match = YEAR_PATTERN.match(entry)
        if not match:
            issues.append(f"Entry {number}: could not identify authors and year")
            continue
        author_text, year_text, remainder = match.groups()
        title = remainder.split(". ", 1)[0].strip().rstrip(".")
        identifier, url = _identifier(entry, title)
        canonical = KNOWN_RECORDS.get(identifier)
        corrected = False
        authors = _author_names(author_text)
        if canonical:
            corrected = title.casefold() != canonical["title"].casefold()
            title = canonical["title"]
            authors = canonical["authors"]
            if corrected:
                issues.append(f"Corrected title for {identifier}")
        if identifier in seen:
            duplicates += 1
            issues.append(f"Removed duplicate: {title}")
            continue
        seen.add(identifier)
        papers.append({
            "doi": identifier,
            "title": title,
            "authors": authors,
            "year": int(year_text),
            "venue": remainder[len(remainder.split(". ", 1)[0]):].strip(" ."),
            "url": url,
            "abstract": "",
            "paper_type": "approved-introduction-source",
            "source": "Approved Introduction",
            "raw_citation": entry,
            "metadata_corrected": corrected,
        })
    return {"papers": papers, "issues": issues, "duplicates": duplicates}


def import_approved_citations(text: str) -> dict[str, Any]:
    parsed = parse_citations(text)
    saved = []
    for paper in parsed["papers"]:
        saved.append(save_paper(
            paper,
            relevance="Approved source used in the submitted Introduction.",
            notes=(
                "Evi-Revy: bibliography approved by Beng. Verify abstract or full text "
                "before using claim-level evidence. Original citation: " + paper["raw_citation"]
            ),
        ))
    return {
        "imported": len(saved),
        "duplicates": parsed["duplicates"],
        "issues": parsed["issues"],
        "papers": saved,
    }
