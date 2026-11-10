from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from application.api import ToolRequest, dashboard, health, run_tool, tools


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.gallery = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
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
        response = run_tool(
            ToolRequest(
                gallery=str(self.gallery),
                tool="delete_images",
                arguments={},
            )
        )

        self.assertFalse(response["success"])


if __name__ == "__main__":
    unittest.main()
