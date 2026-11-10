from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from application.tools import retrieve_images_by_date
from tests.helpers import create_image


class RetrieveImagesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.gallery = Path(self.temporary_directory.name)
        create_image(self.gallery / "morning.jpg", datetime(2026, 11, 10, 8, 0))
        create_image(self.gallery / "nested" / "evening.PNG", datetime(2026, 11, 10, 18, 0))
        create_image(self.gallery / "older.webp", datetime(2026, 11, 9, 12, 0))
        (self.gallery / "notes.txt").write_text("not an image", encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_retrieves_supported_images_recursively(self) -> None:
        result = retrieve_images_by_date(self.gallery, "2026-11-10")

        self.assertTrue(result.success)
        self.assertEqual(result.data["count"], 2)
        self.assertEqual(result.data["images"], ["morning.jpg", "nested/evening.PNG"])

    def test_non_recursive_search_excludes_nested_images(self) -> None:
        result = retrieve_images_by_date(self.gallery, "2026-11-10", recursive=False)

        self.assertEqual(result.data["images"], ["morning.jpg"])

    def test_returns_successful_empty_result(self) -> None:
        result = retrieve_images_by_date(self.gallery, "2026-01-01")

        self.assertTrue(result.success)
        self.assertEqual(result.data["count"], 0)

    def test_rejects_invalid_date(self) -> None:
        result = retrieve_images_by_date(self.gallery, "10/11/2026")

        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)


if __name__ == "__main__":
    unittest.main()
