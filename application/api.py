"""Local API and dashboard server for the image-management agent."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from application.controller import ALLOWED_TOOLS, execute_tool

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_ROOT = REPOSITORY_ROOT / "frontend"
DEMO_GALLERY = REPOSITORY_ROOT / "runtime" / "demo-gallery"
DEMO_DATE = "2026-11-10"

app = FastAPI(
    title="FYP Agent",
    description="Safe local image-management agent dashboard",
    version="0.2.0",
)
app.mount("/assets", StaticFiles(directory=FRONTEND_ROOT / "assets"), name="assets")


class ToolRequest(BaseModel):
    gallery: str = Field(min_length=1)
    tool: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


def _create_demo_image(path: Path, hour: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"fyp-agent-demo-image")
    timestamp = datetime(2026, 11, 10, hour, 0).timestamp()
    os.utime(path, (timestamp, timestamp))


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(FRONTEND_ROOT / "index.html")


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ready",
        "service": "FYP Agent local runner",
        "allowed_tools": len(ALLOWED_TOOLS),
        "safety": "gallery-bound",
    }


@app.get("/api/tools")
def tools() -> dict[str, Any]:
    return {
        "tools": [
            {
                "name": "retrieve_images_by_date",
                "label": "Find images",
                "description": "Find supported images using their last-modified date.",
                "fields": ["target_date", "recursive"],
            },
            {
                "name": "create_folder",
                "label": "Create folder",
                "description": "Create a safe destination inside the selected gallery.",
                "fields": ["folder"],
            },
            {
                "name": "copy_images",
                "label": "Copy images",
                "description": "Copy selected images without deleting or overwriting originals.",
                "fields": ["images", "destination_folder"],
            },
        ]
    }


@app.post("/api/tools/execute")
def run_tool(request: ToolRequest) -> dict[str, Any]:
    result = execute_tool(
        request.gallery,
        {"tool": request.tool, "arguments": request.arguments},
    )
    return result.to_dict()


@app.post("/api/demo/setup")
def setup_demo() -> dict[str, Any]:
    DEMO_GALLERY.mkdir(parents=True, exist_ok=True)
    _create_demo_image(DEMO_GALLERY / "inbox" / "campus-morning.jpg", 8)
    _create_demo_image(DEMO_GALLERY / "inbox" / "lab-session.png", 11)
    _create_demo_image(DEMO_GALLERY / "inbox" / "sunset.webp", 18)
    (DEMO_GALLERY / "archive").mkdir(exist_ok=True)
    return {
        "success": True,
        "gallery": str(DEMO_GALLERY),
        "date": DEMO_DATE,
        "message": "Demo gallery is ready with three sample images.",
    }
