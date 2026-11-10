"""Copy selected images within the configured gallery without overwriting."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Iterable

from application.schemas import ToolResult
from application.security import UnsafePathError, gallery_root, path_within
from application.tools.retrieve_images_by_date import SUPPORTED_IMAGE_EXTENSIONS

LOGGER = logging.getLogger(__name__)


def _available_destination(destination: Path) -> Path:
    """Return a deterministic non-existing destination path."""

    if not destination.exists():
        return destination

    counter = 1
    while True:
        candidate = destination.with_name(f"{destination.stem}_{counter}{destination.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def copy_images(
    gallery: str | Path,
    images: Iterable[str | Path],
    destination_folder: str | Path,
) -> ToolResult:
    """Copy supported image files to an existing folder under the gallery root."""

    tool_name = "copy_images"
    try:
        root = gallery_root(gallery)
        destination = path_within(root, destination_folder)
        if not destination.is_dir():
            raise ValueError(f"Destination folder does not exist: {destination}")

        requested_images = list(images)
        if not requested_images:
            raise ValueError("At least one source image is required")

        sources: list[Path] = []
        for requested in requested_images:
            source = path_within(root, requested)
            if not source.is_file():
                raise ValueError(f"Source image does not exist: {source}")
            if source.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
                raise ValueError(f"Unsupported image type: {source.suffix or '<none>'}")
            sources.append(source)

        copied: list[dict[str, str]] = []
        for source in sources:
            target = _available_destination(destination / source.name)
            if target.resolve() == source.resolve():
                raise ValueError(f"Source and destination refer to the same file: {source}")
            shutil.copy2(source, target)
            copied.append(
                {
                    "source": source.relative_to(root).as_posix(),
                    "destination": target.relative_to(root).as_posix(),
                }
            )

        LOGGER.info("%s copied %d image(s)", tool_name, len(copied))
        return ToolResult(
            success=True,
            tool=tool_name,
            data={"count": len(copied), "files": copied},
        )
    except (OSError, UnsafePathError, ValueError) as exc:
        LOGGER.warning("%s failed: %s", tool_name, exc)
        return ToolResult(success=False, tool=tool_name, error=str(exc))
