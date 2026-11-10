"""Create a destination folder within the configured gallery."""

from __future__ import annotations

import logging
from pathlib import Path

from application.schemas import ToolResult
from application.security import UnsafePathError, gallery_root, path_within

LOGGER = logging.getLogger(__name__)


def create_folder(gallery: str | Path, folder: str | Path) -> ToolResult:
    """Create a non-empty relative folder without leaving the gallery root."""

    tool_name = "create_folder"
    try:
        root = gallery_root(gallery)
        if not str(folder).strip() or Path(folder) == Path("."):
            raise ValueError("Folder name must not be empty or the gallery root")

        destination = path_within(root, folder)
        existed = destination.exists()
        if existed and not destination.is_dir():
            raise ValueError(f"Destination exists and is not a directory: {destination}")

        destination.mkdir(parents=True, exist_ok=True)
        relative = destination.relative_to(root).as_posix()
        LOGGER.info("%s prepared %s", tool_name, relative)
        return ToolResult(
            success=True,
            tool=tool_name,
            data={"path": relative, "created": not existed},
        )
    except (OSError, UnsafePathError, ValueError) as exc:
        LOGGER.warning("%s failed: %s", tool_name, exc)
        return ToolResult(success=False, tool=tool_name, error=str(exc))
