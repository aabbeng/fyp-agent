from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from application import database
from application.api import ToolRequest, dashboard, health, run_tool, tools


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.gallery = Path(self.temporary_directory.name)
        self.original_db_path = database.DB_PATH
        database.DB_PATH = self.gallery / "api-test.db"
        database.initialize_database()

    def tearDown(self) -> None:
        database.DB_PATH = self.original_db_path
        self.temporary_directory.cleanup()

    def test_dashboard_is_served(self) -> None:
        response = dashboard()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Path(response.path).is_file())

    def test_health_reports_three_allowed_tools(self) -> None:
        response = health()

        self.assertEqual(response["allowed_tools"], 3)

    def test_tools_endpoint_documents_allowlist(self) -> None:
        response = tools()

        self.assertEqual(len(response["tools"]), 3)

    def test_execute_endpoint_runs_safe_tool(self) -> None:
        database.set_methodology_status("approved", "Test approval")
        response = run_tool(
            ToolRequest(
                gallery=str(self.gallery),
                tool="create_folder",
                arguments={"folder": "albums/demo"},
            )
        )

        self.assertTrue(response["success"])
        self.assertTrue((self.gallery / "albums" / "demo").is_dir())

    def test_execute_endpoint_blocks_unknown_tool(self) -> None:
        database.set_methodology_status("approved", "Test approval")
        response = run_tool(
            ToolRequest(
                gallery=str(self.gallery),
                tool="delete_images",
                arguments={},
            )
        )

        self.assertFalse(response["success"])

    def test_execute_endpoint_respects_methodology_gate(self) -> None:
        response = run_tool(
            ToolRequest(
                gallery=str(self.gallery),
                tool="create_folder",
                arguments={"folder": "should-not-exist"},
            )
        )

        self.assertFalse(response["success"])
        self.assertIn("methodology", response["error"].lower())
        self.assertFalse((self.gallery / "should-not-exist").exists())


if __name__ == "__main__":
    unittest.main()
