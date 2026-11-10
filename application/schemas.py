"""Shared structured results returned by every project tool."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolResult:
    """Serializable outcome for a tool invocation."""

    success: bool
    tool: str
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""

        return asdict(self)
