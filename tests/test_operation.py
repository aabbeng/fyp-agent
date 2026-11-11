from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from application import database
from application.auth import create_session, password_valid, session_valid
from application.automation import research_topics, run_research_cycle


PAPER = {
    "doi": "10.1000/xeng.1",
    "title": "Agent Tool Selection",
    "authors": ["Test Author"],
    "year": 2026,
    "venue": "Test Journal",
    "url": "https://doi.org/10.1000/xeng.1",
    "abstract": "",
    "paper_type": "journal-article",
    "source": "Crossref",
}


class OperationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.original_db_path = database.DB_PATH
        database.DB_PATH = Path(self.temp.name) / "operation.db"
        database.initialize_database()

    def tearDown(self) -> None:
        database.DB_PATH = self.original_db_path
        self.temp.cleanup()

    def test_candidate_needs_human_approval(self) -> None:
        _, created = database.save_candidate(PAPER, "agent tools")
        self.assertTrue(created)
        self.assertEqual(database.list_papers(), [])
        database.approve_candidate(PAPER["doi"])
        self.assertEqual(len(database.list_papers()), 1)

    def test_six_named_agents_are_initialized(self) -> None:
        agents = database.list_agent_states()
        self.assertEqual(
            [agent["name"] for agent in agents],
            ["Scoot", "Evi-Revy", "Planx", "Xengineer", "TeeHee", "Cordy"],
        )

    @patch.dict(os.environ, {"XENG_RESEARCH_TOPICS": ""})
    def test_empty_topic_variable_uses_defaults(self) -> None:
        self.assertGreater(len(research_topics()), 0)

    @patch("application.automation.send_telegram", return_value=True)
    @patch("application.automation.search_papers", return_value=[PAPER])
    def test_cycle_records_run_and_notifies(self, _search, _telegram) -> None:
        result = run_research_cycle()
        self.assertEqual(result["new_candidates"], 1)
        self.assertTrue(result["telegram_sent"])
        self.assertEqual(database.list_job_runs()[0]["status"], "completed")
        self.assertGreater(len(database.list_agent_messages()), 0)


class AuthTests(unittest.TestCase):
    @patch.dict(os.environ, {"XENG_ADMIN_PASSWORD": "correct", "XENG_SESSION_SECRET": "secret"})
    def test_signed_session(self) -> None:
        self.assertTrue(password_valid("correct"))
        self.assertFalse(password_valid("wrong"))
        self.assertTrue(session_valid(create_session()))
        self.assertFalse(session_valid("bad.session"))


if __name__ == "__main__":
    unittest.main()
