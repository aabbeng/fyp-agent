from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from application import database
from application.bibliography import import_approved_citations, parse_citations


SAMPLE = """Qin, Y., Liang, S., & Sun, M. (2023). Wrong title. arXiv. https://doi.org/10.48550/arxiv.2307.16789
Shunyu, Y., Jeffrey, Z., & Yuan, C. (2023). REACT: SYNERGIZING REASONING AND ACTING IN LANGUAGE MODELS. ICLR. https://openreview.net/pdf?id=WE_vluYUL-X
Yao, S., Zhao, J., & Cao, Y. (2022). Wrong duplicate title. arXiv. https://doi.org/10.48550/arxiv.2210.03629
10
"""


class BibliographyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.original_db_path = database.DB_PATH
        database.DB_PATH = Path(self.temp.name) / "bibliography.db"
        database.initialize_database()

    def tearDown(self) -> None:
        database.DB_PATH = self.original_db_path
        self.temp.cleanup()

    def test_parser_corrects_titles_and_removes_duplicate(self) -> None:
        result = parse_citations(SAMPLE)
        self.assertEqual(len(result["papers"]), 2)
        self.assertEqual(result["duplicates"], 1)
        self.assertEqual(result["papers"][0]["title"].split(":")[0], "ToolLLM")
        self.assertEqual(result["papers"][1]["title"].split(":")[0], "ReAct")

    def test_import_marks_sources_as_approved_introduction(self) -> None:
        result = import_approved_citations(SAMPLE)
        self.assertEqual(result["imported"], 2)
        saved = database.list_papers()
        self.assertTrue(all(paper["source"] == "Approved Introduction" for paper in saved))
        self.assertTrue(all("submitted Introduction" in paper["relevance"] for paper in saved))


if __name__ == "__main__":
    unittest.main()
