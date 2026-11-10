from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from application.controller import execute_tool


class ControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.gallery = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_dispatches_allowlisted_tool(self) -> None:
        result = execute_tool(
            self.gallery,
            {"tool": "create_folder", "arguments": {"folder": "approved"}},
        )

        self.assertTrue(result.success)
        self.assertTrue((self.gallery / "approved").is_dir())

    def test_rejects_unknown_tool(self) -> None:
        result = execute_tool(
            self.gallery,
            {"tool": "delete_images", "arguments": {"path": "all"}},
        )

        self.assertFalse(result.success)
        self.assertEqual(result.error, "Tool is not allowed")

    def test_rejects_non_object_arguments(self) -> None:
        result = execute_tool(
            self.gallery,
            {"tool": "create_folder", "arguments": "album"},
        )

        self.assertFalse(result.success)

    def test_reports_missing_arguments(self) -> None:
        result = execute_tool(
            self.gallery,
            {"tool": "create_folder", "arguments": {}},
        )

        self.assertFalse(result.success)
        self.assertIn("Invalid arguments", result.error)


if __name__ == "__main__":
    unittest.main()
