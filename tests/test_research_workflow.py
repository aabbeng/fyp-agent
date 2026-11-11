from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException

from application import database
from application.api import (
    ApprovalRequest,
    DraftRequest,
    EvidenceRequest,
    SectionRequest,
    add_evidence,
    approve_methodology,
    draft_thesis_section,
    update_thesis_section,
    workspace,
)
from application.research import normalize_crossref_item
from application.thesis import build_evidence_outline


SAMPLE_PAPER = {
    "doi": "10.1000/fyp.2026.1",
    "title": "Reliable Tool Selection for Language Model Agents",
    "authors": ["Amina Rahman", "Kai Lee"],
    "year": 2026,
    "venue": "Journal of Agent Systems",
    "url": "https://doi.org/10.1000/fyp.2026.1",
    "abstract": "A controlled study of tool selection and recovery.",
    "paper_type": "journal-article",
    "source": "Crossref",
}


class ResearchWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.original_db_path = database.DB_PATH
        database.DB_PATH = Path(self.temp.name) / "test.db"
        database.initialize_database()

    def tearDown(self) -> None:
        database.DB_PATH = self.original_db_path
        self.temp.cleanup()

    def test_normalizes_crossref_metadata(self) -> None:
        paper = normalize_crossref_item(
            {
                "DOI": "10.1000/Example",
                "title": ["<b>Agent tools</b>"],
                "author": [{"given": "Ada", "family": "Lovelace"}],
                "published": {"date-parts": [[2025, 2, 1]]},
                "container-title": ["AI Journal"],
                "is-referenced-by-count": 12,
            }
        )

        self.assertEqual(paper["doi"], "10.1000/example")
        self.assertEqual(paper["title"], "Agent tools")
        self.assertEqual(paper["authors"], ["Ada Lovelace"])
        self.assertEqual(paper["year"], 2025)

    def test_saves_verified_evidence_without_duplicates(self) -> None:
        request = EvidenceRequest(paper=SAMPLE_PAPER, relevance="Supports evaluation metrics")
        add_evidence(request)
        add_evidence(request)

        state = workspace()
        self.assertEqual(state["paper_count"], 1)
        self.assertEqual(state["papers"][0]["source"], "Crossref")

    def test_academic_draft_uses_in_text_citation(self) -> None:
        content = build_evidence_outline("literature_review", [SAMPLE_PAPER])

        self.assertIn("Evaluation and Research Gap", content)
        self.assertIn("(Rahman et al., 2026)", content)
        self.assertNotIn("##", content)
        self.assertNotIn("- ", content)

    def test_outline_flags_citation_only_sources(self) -> None:
        citation_only = {**SAMPLE_PAPER, "abstract": ""}
        content = build_evidence_outline("literature_review", [citation_only])
        self.assertIn("verified abstracts or full papers", content)
        self.assertNotIn("##", content)

    def test_draft_endpoint_builds_evidence_outline(self) -> None:
        add_evidence(EvidenceRequest(paper=SAMPLE_PAPER))

        result = draft_thesis_section(DraftRequest(section_key="expected_results"))

        self.assertEqual(result["mode"], "local_outline")
        self.assertIn("predictions rather than research findings", result["section"]["content"])

    def test_methodology_requires_evidence_and_substantial_draft(self) -> None:
        with self.assertRaises(HTTPException):
            approve_methodology(ApprovalRequest(confirmed=True))

        add_evidence(EvidenceRequest(paper=SAMPLE_PAPER))
        update_thesis_section(
            "methodology",
            SectionRequest(content="A controlled methodology. " * 10),
        )
        result = approve_methodology(
            ApprovalRequest(confirmed=True, notes="Reviewed by student")
        )

        self.assertTrue(result["build_unlocked"])
        self.assertEqual(workspace()["methodology"]["status"], "approved")

    def test_editing_approved_methodology_locks_build_again(self) -> None:
        add_evidence(EvidenceRequest(paper=SAMPLE_PAPER))
        update_thesis_section("methodology", SectionRequest(content="Method step. " * 20))
        approve_methodology(ApprovalRequest(confirmed=True))

        update_thesis_section("methodology", SectionRequest(content="Changed method. " * 20))

        self.assertFalse(workspace()["build_unlocked"])


if __name__ == "__main__":
    unittest.main()
