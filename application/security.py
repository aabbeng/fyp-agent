"""Filesystem boundary checks shared by the image-management tools."""

from __future__ import annotations

from pathlib import Path


class UnsafePathError(ValueError):
    """Raised when a requested path escapes the configured gallery."""


def gallery_root(path: str | Path) -> Path:
    """Return an existing gallery root as an absolute path."""

    root = Path(path).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Gallery directory does not exist: {root}")
    return root


def path_within(root: Path, requested: str | Path) -> Path:
    """Resolve a relative or absolute path and require it to stay in root."""

    candidate = Path(requested).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()

    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise UnsafePathError(f"Path is outside the configured gallery: {candidate}") from exc

    return candidate
