"""Test fixture helpers."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path


def create_image(path: Path, modified_at: datetime) -> Path:
    """Create a small fake image and set a deterministic modification time."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"fixture-image-data")
    timestamp = modified_at.timestamp()
    os.utime(path, (timestamp, timestamp))
    return path
