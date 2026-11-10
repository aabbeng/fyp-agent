from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from application.tools import copy_images
from tests.helpers import create_image


class CopyImagesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.gallery = Path(self.temporary_directory.name)
        self.source = create_image(
            self.gallery / "source" / "photo.jpg", datetime(2026, 11, 10, 9, 0)
        )
        self.destination = self.gallery / "album"
        self.destination.mkdir()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_copies_image_and_preserves_source(self) -> None:
        result = copy_images(self.gallery, ["source/photo.jpg"], "album")

        self.assertTrue(result.success)
        self.assertTrue(self.source.exists())
        self.assertTrue((self.destination / "photo.jpg").exists())
        self.assertEqual(result.data["count"], 1)

    def test_renames_duplicate_without_overwriting(self) -> None:
        (self.destination / "photo.jpg").write_bytes(b"existing")

        result = copy_images(self.gallery, ["source/photo.jpg"], "album")

        self.assertTrue(result.success)
        self.assertEqual((self.destination / "photo.jpg").read_bytes(), b"existing")
        self.assertTrue((self.destination / "photo_1.jpg").exists())

    def test_rejects_source_outside_gallery(self) -> None:
        result = copy_images(self.gallery, ["../photo.jpg"], "album")

        self.assertFalse(result.success)
        self.assertIn("outside", result.error.lower())

    def test_rejects_missing_destination(self) -> None:
        result = copy_images(self.gallery, ["source/photo.jpg"], "missing")

        self.assertFalse(result.success)

    def test_rejects_empty_source_list(self) -> None:
        result = copy_images(self.gallery, [], "album")

        self.assertFalse(result.success)

    def test_rejects_unsupported_file_type(self) -> None:
        (self.gallery / "source" / "notes.txt").write_text("text", encoding="utf-8")

        result = copy_images(self.gallery, ["source/notes.txt"], "album")

        self.assertFalse(result.success)


if __name__ == "__main__":
    unittest.main()
