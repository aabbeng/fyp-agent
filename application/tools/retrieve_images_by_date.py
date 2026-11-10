"""Retrieve image files using their filesystem last-modified date."""

from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path

from application.schemas import ToolResult
from application.security import gallery_root

LOGGER = logging.getLogger(__name__)

SUPPORTED_IMAGE_EXTENSIONS = frozenset(
    {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff", ".webp"}
)


def retrieve_images_by_date(
    gallery: str | Path,
    target_date: str,
    *,
    recursive: bool = True,
) -> ToolResult:
    """Find supported images whose last-modified date matches YYYY-MM-DD."""

    tool_name = "retrieve_images_by_date"
    try:
        root = gallery_root(gallery)
        requested_date = date.fromisoformat(target_date)
        paths = root.rglob("*") if recursive else root.glob("*")
        matches = sorted(
            path
            for path in paths
            if path.is_file()
            and path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
            and datetime.fromtimestamp(path.stat().st_mtime).date() == requested_date
        )
        relative_matches = [path.relative_to(root).as_posix() for path in matches]
        LOGGER.info("%s found %d image(s) for %s", tool_name, len(matches), target_date)
        return ToolResult(
            success=True,
            tool=tool_name,
            data={
                "date": target_date,
                "count": len(relative_matches),
                "images": relative_matches,
            },
        )
    except (OSError, ValueError) as exc:
        LOGGER.warning("%s failed: %s", tool_name, exc)
        return ToolResult(success=False, tool=tool_name, error=str(exc))
