from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from application import database
from application.auth import create_session, password_valid, session_valid
from application.automation import research_topics, run_research_cycle
from application.notifications import format_agent_update, format_team_update


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

    def test_telegram_decision_can_approve_paper_by_compact_id(self) -> None:
        candidate, _ = database.save_candidate(PAPER, "agent tools")
        result = database.decide_candidate(candidate["id"], "approved")
        self.assertEqual(result["status"], "approved")
        self.assertEqual(len(database.list_papers()), 1)

    def test_telegram_decision_can_reject_without_saving_paper(self) -> None:
        candidate, _ = database.save_candidate(PAPER, "agent tools")
        result = database.decide_candidate(candidate["id"], "rejected")
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(database.list_papers(), [])

    def test_six_named_agents_are_initialized(self) -> None:
        agents = database.list_agent_states()
        self.assertEqual(
            [agent["name"] for agent in agents],
            ["Scoot", "Evi-Revy", "Planx", "Xengineer", "TeeHee", "Cordy"],
        )

    @patch.dict(os.environ, {"XENG_RESEARCH_TOPICS": ""})
    def test_empty_topic_variable_uses_defaults(self) -> None:
        self.assertGreater(len(research_topics()), 0)

    @patch("application.automation.send_team_update", return_value=True)
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


class NotificationTests(unittest.TestCase):
    def test_agent_update_addresses_beng_as_owner(self) -> None:
        message = format_agent_update(
            "Planx", "Draft ready", "I finished the literature review.", "Please review it.",
        )
        self.assertIn("PLANX — DRAFT READY", message)
        self.assertIn("Boss Beng", message)
        self.assertIn("What I need from you", message)

    def test_team_update_keeps_each_agent_clearly_separated(self) -> None:
        message = format_team_update([
            {"agent": "Scoot", "type": "Status", "message": "Research is complete."},
            {"agent": "Cordy", "type": "Reminder", "message": "The team is synced."},
        ])
        self.assertIn("Owner: BENG", message)
        self.assertIn("SCOOT — STATUS", message)
        self.assertIn("CORDY — REMINDER", message)


if __name__ == "__main__":
    unittest.main()
