"""API and dashboard server for the XENG workspace."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from application.controller import ALLOWED_TOOLS, execute_tool
from application.auth import (
    COOKIE_NAME,
    SESSION_SECONDS,
    auth_required,
    create_session,
    password_valid,
    secure_cookies,
    session_valid,
)
from application.database import (
    approve_candidate,
    backend_name,
    get_section,
    get_sections,
    list_activities,
    list_candidates,
    list_job_runs,
    list_papers,
    log_activity,
    methodology_status,
    save_paper,
    save_section,
    set_methodology_status,
)
from application.notifications import telegram_configured
from application.research import ResearchSearchError, search_papers
from application.thesis import build_evidence_outline

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_ROOT = REPOSITORY_ROOT / "frontend"
DEMO_GALLERY = REPOSITORY_ROOT / "runtime" / "demo-gallery"
DEMO_DATE = "2026-11-10"

app = FastAPI(
    title="XENG",
    description="Research-to-prototype workspace for the XENG agent system",
    version="0.3.0",
)
app.mount("/assets", StaticFiles(directory=FRONTEND_ROOT / "assets"), name="assets")


class ToolRequest(BaseModel):
    gallery: str = Field(min_length=1)
    tool: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class EvidenceRequest(BaseModel):
    paper: dict[str, Any]
    relevance: str = ""
    notes: str = ""


class SectionRequest(BaseModel):
    content: str


class DraftRequest(BaseModel):
    section_key: str
    focus: str = ""


class ApprovalRequest(BaseModel):
    confirmed: bool
    notes: str = ""


class LoginRequest(BaseModel):
    password: str = Field(min_length=1)


def local_team_status() -> dict[str, Any]:
    return {
        "mode": "cloud-ready" if os.getenv("DATABASE_URL") else "free-local",
        "paid_api": False,
        "agents": ["Coordinator", "Research Assistant", "Thesis Organizer", "Development Gate"],
    }


@app.middleware("http")
async def protect_api(request: Request, call_next):
    public_paths = {"/api/health", "/api/auth/status", "/api/auth/login"}
    if (
        auth_required()
        and request.url.path.startswith("/api/")
        and request.url.path not in public_paths
        and not session_valid(request.cookies.get(COOKIE_NAME))
    ):
        return JSONResponse({"detail": "Please sign in to XENG"}, status_code=401)
    return await call_next(request)


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
        "service": "XENG operation",
        "allowed_tools": len(ALLOWED_TOOLS),
        "safety": "gallery-bound",
        "agents": local_team_status(),
        "methodology": methodology_status()["status"],
        "database": backend_name(),
        "login_required": auth_required(),
        "telegram_configured": telegram_configured(),
    }


@app.get("/api/auth/status")
def auth_status(request: Request) -> dict[str, bool]:
    required = auth_required()
    return {
        "required": required,
        "authenticated": not required or session_valid(request.cookies.get(COOKIE_NAME)),
    }


@app.post("/api/auth/login")
def login(request: LoginRequest, response: Response) -> dict[str, bool]:
    if not password_valid(request.password):
        raise HTTPException(status_code=401, detail="Wrong password")
    response.set_cookie(
        COOKIE_NAME,
        create_session(),
        max_age=SESSION_SECONDS,
        httponly=True,
        secure=secure_cookies(),
        samesite="strict",
    )
    return {"success": True}


@app.post("/api/auth/logout")
def logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(COOKIE_NAME)
    return {"success": True}


@app.get("/api/workspace")
def workspace() -> dict[str, Any]:
    papers = list_papers()
    sections = get_sections()
    gate = methodology_status()
    return {
        "papers": papers,
        "paper_count": len(papers),
        "sections": sections,
        "methodology": gate,
        "build_unlocked": gate["status"] == "approved",
        "agent_team": local_team_status(),
        "activities": list_activities(12),
        "research_candidates": list_candidates("pending", 50),
        "job_runs": list_job_runs(12),
        "operation": {
            "database": backend_name(),
            "telegram": telegram_configured(),
            "schedule": "Every 6 hours on GitHub Actions",
        },
    }


@app.get("/api/research/candidates")
def research_candidates() -> dict[str, Any]:
    candidates = list_candidates("pending", 100)
    return {"count": len(candidates), "candidates": candidates}


@app.post("/api/research/candidates/{doi:path}/approve")
def approve_research_candidate(doi: str) -> dict[str, Any]:
    try:
        paper = approve_candidate(doi)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    log_activity("Research Agent", "Candidate approved", paper["title"])
    return {"success": True, "paper": paper}


@app.get("/api/research/search")
def research_search(
    query: str = Query(min_length=3, max_length=240),
    rows: int = Query(default=8, ge=1, le=20),
) -> dict[str, Any]:
    try:
        papers = search_papers(query, rows)
    except ResearchSearchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    log_activity("Research Agent", "Searched papers", f"{query} — {len(papers)} results")
    return {"query": query, "count": len(papers), "papers": papers}


@app.post("/api/research/evidence")
def add_evidence(request: EvidenceRequest) -> dict[str, Any]:
    try:
        paper = save_paper(request.paper, request.relevance, request.notes)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid paper: {exc}") from exc
    log_activity("Research Agent", "Saved evidence", f"{paper['title']} — {paper['doi']}")
    return {"success": True, "paper": paper}


@app.get("/api/research/evidence")
def evidence_library() -> dict[str, Any]:
    papers = list_papers()
    return {"count": len(papers), "papers": papers}


@app.get("/api/thesis/sections")
def thesis_sections() -> dict[str, Any]:
    return {"sections": get_sections()}


@app.put("/api/thesis/sections/{section_key}")
def update_thesis_section(section_key: str, request: SectionRequest) -> dict[str, Any]:
    try:
        section = save_section(section_key, request.content)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if section_key == "methodology" and methodology_status()["status"] == "approved":
        set_methodology_status("locked", "Methodology changed after approval")
    log_activity("Thesis Writer", "Saved draft", section["title"])
    return {"success": True, "section": section}


@app.post("/api/thesis/draft")
def draft_thesis_section(request: DraftRequest) -> dict[str, Any]:
    section = get_section(request.section_key)
    if not section:
        raise HTTPException(status_code=404, detail="Unknown thesis section")
    papers = list_papers()
    content = build_evidence_outline(request.section_key, papers)
    mode = "local_outline"
    saved = save_section(request.section_key, content)
    log_activity("Thesis Writer", "Prepared draft", f"{saved['title']} — {mode}")
    return {"success": True, "mode": mode, "section": saved}


@app.post("/api/methodology/approve")
def approve_methodology(request: ApprovalRequest) -> dict[str, Any]:
    section = get_section("methodology")
    if not request.confirmed:
        raise HTTPException(status_code=400, detail="Approval confirmation is required")
    if not section or len(section["content"].strip()) < 120:
        raise HTTPException(status_code=400, detail="Methodology draft is too short to approve")
    if not list_papers():
        raise HTTPException(status_code=400, detail="Save at least one verified paper first")
    save_section("methodology", section["content"], status="approved")
    gate = set_methodology_status("approved", request.notes)
    log_activity("Coordinator", "Methodology approved", "Development gate unlocked")
    return {"success": True, "methodology": gate, "build_unlocked": True}


@app.post("/api/methodology/reopen")
def reopen_methodology() -> dict[str, Any]:
    section = get_section("methodology")
    if section:
        save_section("methodology", section["content"], status="draft")
    gate = set_methodology_status("locked", "Reopened for editing")
    log_activity("Coordinator", "Methodology reopened", "Development gate locked")
    return {"success": True, "methodology": gate, "build_unlocked": False}


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
    if methodology_status()["status"] != "approved":
        return {
            "success": False,
            "tool": request.tool,
            "data": {},
            "error": "Development is locked. Approve the methodology before running prototype tools.",
        }
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
