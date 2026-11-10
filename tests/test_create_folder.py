from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from application.tools import create_folder


class CreateFolderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.gallery = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_creates_folder_within_gallery(self) -> None:
        result = create_folder(self.gallery, "albums/November")

        self.assertTrue(result.success)
        self.assertTrue((self.gallery / "albums" / "November").is_dir())
        self.assertTrue(result.data["created"])

    def test_existing_folder_is_successful_and_not_created(self) -> None:
        (self.gallery / "existing").mkdir()

        result = create_folder(self.gallery, "existing")

        self.assertTrue(result.success)
        self.assertFalse(result.data["created"])

    def test_rejects_parent_traversal(self) -> None:
        result = create_folder(self.gallery, "../outside")

        self.assertFalse(result.success)
        self.assertIn("outside", result.error.lower())

    def test_rejects_empty_folder_name(self) -> None:
        result = create_folder(self.gallery, "")

        self.assertFalse(result.success)


if __name__ == "__main__":
    unittest.main()
