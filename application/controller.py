"""Allowlisted dispatcher for structured tool requests."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from application.schemas import ToolResult
from application.tools import copy_images, create_folder, retrieve_images_by_date

Tool = Callable[..., ToolResult]

ALLOWED_TOOLS: dict[str, Tool] = {
    "retrieve_images_by_date": retrieve_images_by_date,
    "create_folder": create_folder,
    "copy_images": copy_images,
}


def execute_tool(gallery: str | Path, request: dict[str, Any]) -> ToolResult:
    """Validate a structured request and execute one allowlisted tool."""

    tool_name = request.get("tool")
    arguments = request.get("arguments")
    if tool_name not in ALLOWED_TOOLS:
        return ToolResult(success=False, tool=str(tool_name), error="Tool is not allowed")
    if not isinstance(arguments, dict):
        return ToolResult(success=False, tool=tool_name, error="Arguments must be an object")

    try:
        return ALLOWED_TOOLS[tool_name](gallery=gallery, **arguments)
    except TypeError as exc:
        return ToolResult(success=False, tool=tool_name, error=f"Invalid arguments: {exc}")
