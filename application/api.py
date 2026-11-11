"""API and dashboard server for the XENG workspace."""

from __future__ import annotations

import os
import hmac
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
    decide_candidate,
    backend_name,
    get_section,
    get_sections,
    list_activities,
    list_agent_messages,
    list_agent_states,
    list_candidates,
    list_job_runs,
    list_papers,
    log_activity,
    methodology_status,
    save_paper,
    save_section,
    set_methodology_status,
)
from application.agents import refresh_team_states
from application.notifications import (
    answer_callback,
    configure_webhook,
    remove_message_buttons,
    send_agent_action,
    send_agent_update,
    send_paper_review,
    telegram_configured,
)
from application.research import ResearchSearchError, search_papers
from application.thesis import build_evidence_outline
from application.bibliography import import_approved_citations

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
    evidence_dois: list[str] | None = None


class ApprovalRequest(BaseModel):
    confirmed: bool
    notes: str = ""


class LoginRequest(BaseModel):
    password: str = Field(min_length=1)


class CitationImportRequest(BaseModel):
    text: str = Field(min_length=20, max_length=100_000)
    approved_for_introduction: bool = False


def local_team_status() -> dict[str, Any]:
    return {
        "mode": "cloud-ready" if os.getenv("DATABASE_URL") else "free-local",
        "paid_api": False,
        "agents": [agent["name"] for agent in list_agent_states()],
    }


def _notify_agent(agent: str, update_type: str, message: str, next_step: str = "") -> bool:
    try:
        return send_agent_update(agent, update_type, message, next_step)
    except Exception:
        return False


@app.middleware("http")
async def protect_api(request: Request, call_next):
    public_paths = {"/api/health", "/api/auth/status", "/api/auth/login", "/api/telegram/webhook"}
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
        "agents": list_agent_states(),
        "agent_messages": list_agent_messages(18),
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


def _approve_methodology_action(notes: str = "Approved by Boss Beng through Telegram") -> dict[str, Any]:
    section = get_section("methodology")
    if not section or len(section["content"].strip()) < 120:
        raise ValueError("Methodology draft is too short to approve")
    if not list_papers():
        raise ValueError("Save at least one verified paper first")
    save_section("methodology", section["content"], status="approved")
    gate = set_methodology_status("approved", notes)
    log_activity("Cordy", "Methodology approved", "Xengineer development gate unlocked")
    refresh_team_states()
    return {"methodology": gate, "build_unlocked": True}


@app.post("/api/telegram/setup")
def setup_telegram(request: Request) -> dict[str, Any]:
    configured_url = os.getenv("XENG_PUBLIC_URL", "").strip()
    public_url = configured_url or str(request.base_url).rstrip("/")
    try:
        configure_webhook(public_url)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    log_activity("Cordy", "Telegram control connected", public_url)
    return {"success": True, "webhook": f"{public_url}/api/telegram/webhook"}


@app.post("/api/telegram/sync-papers")
def sync_papers_to_telegram(limit: int = Query(default=5, ge=1, le=10)) -> dict[str, Any]:
    sent = 0
    for candidate in list_candidates("pending", limit):
        sent += int(send_paper_review(candidate))
    return {"success": True, "sent": sent}


@app.post("/api/telegram/webhook")
async def telegram_webhook(request: Request) -> dict[str, bool]:
    expected_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()
    received_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not expected_secret or not hmac.compare_digest(received_secret, expected_secret):
        raise HTTPException(status_code=403, detail="Invalid Telegram webhook secret")

    update = await request.json()
    callback = update.get("callback_query")
    if not callback:
        return {"ok": True}
    message = callback.get("message") or {}
    chat_id = str((message.get("chat") or {}).get("id", ""))
    owner_chat = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not owner_chat or not hmac.compare_digest(chat_id, owner_chat):
        answer_callback(callback.get("id", ""), "This control belongs to Boss Beng.")
        raise HTTPException(status_code=403, detail="Telegram owner mismatch")

    data = callback.get("data", "")
    notice = "Decision recorded."
    try:
        parts = data.split(":")
        if len(parts) == 3 and parts[0] == "paper" and parts[1] in {"approve", "reject"}:
            decision = "approved" if parts[1] == "approve" else "rejected"
            candidate = decide_candidate(int(parts[2]), decision)
            title = candidate["paper"]["title"]
            notice = f"Paper {decision}."
            log_activity("Evi-Revy", f"Candidate {decision}", title)
            refresh_team_states()
            if decision == "approved" and not candidate["already_decided"]:
                _notify_agent(
                    "Planx", "Evidence approved",
                    f'Boss Beng approved "{title}". I added it to the evidence library.',
                    "I will use it only when Boss Beng selects it for a thesis draft.",
                )
        elif data == "method:approve":
            _approve_methodology_action()
            notice = "Methodology approved. Xengineer is unlocked."
        elif data.startswith("draft:reviewed:"):
            section_key = data.removeprefix("draft:reviewed:")
            section = get_section(section_key)
            if not section:
                raise ValueError("Draft section was not found")
            save_section(section_key, section["content"], status="reviewed")
            log_activity("Planx", "Draft reviewed", section["title"])
            notice = f"{section['title']} marked as reviewed."
        elif data.startswith("test:ack:"):
            log_activity("TeeHee", "Test result acknowledged", data.removeprefix("test:ack:"))
            notice = "Test result acknowledged."
        else:
            raise ValueError("Unknown or expired Telegram action")
        remove_message_buttons(chat_id, int(message["message_id"]))
        answer_callback(callback["id"], notice)
    except (ValueError, KeyError) as exc:
        answer_callback(callback.get("id", ""), str(exc))
    return {"ok": True}


@app.post("/api/research/candidates/{doi:path}/approve")
def approve_research_candidate(doi: str) -> dict[str, Any]:
    try:
        paper = approve_candidate(doi)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    log_activity("Evi-Revy", "Candidate approved", paper["title"])
    refresh_team_states()
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
    log_activity("Scoot", "Searched papers", f"{query} — {len(papers)} results")
    return {"query": query, "count": len(papers), "papers": papers}


@app.post("/api/research/evidence")
def add_evidence(request: EvidenceRequest) -> dict[str, Any]:
    try:
        paper = save_paper(request.paper, request.relevance, request.notes)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid paper: {exc}") from exc
    log_activity("Evi-Revy", "Saved evidence", f"{paper['title']} — {paper['doi']}")
    refresh_team_states()
    return {"success": True, "paper": paper}


@app.get("/api/research/evidence")
def evidence_library() -> dict[str, Any]:
    papers = list_papers()
    return {"count": len(papers), "papers": papers}


@app.post("/api/research/import-citations")
def import_citations(request: CitationImportRequest) -> dict[str, Any]:
    if not request.approved_for_introduction:
        raise HTTPException(
            status_code=400,
            detail="Confirm that these sources were approved for the submitted Introduction",
        )
    result = import_approved_citations(request.text)
    if not result["imported"]:
        raise HTTPException(status_code=400, detail="No valid citation entries were found")
    log_activity(
        "Evi-Revy",
        "Imported approved Introduction sources",
        f"{result['imported']} saved · {result['duplicates']} duplicates removed",
    )
    refresh_team_states()
    _notify_agent(
        "Evi-Revy", "Import completed",
        f"I imported {result['imported']} approved Introduction sources and removed {result['duplicates']} duplicate(s).",
        "Please review any correction notes when convenient. Full-text checks are still required for detailed claims.",
    )
    _notify_agent(
        "Planx", "Evidence ready",
        f"The approved Introduction sources are now available in my evidence pool.",
        "Open Thesis Studio, search for the papers you want, and add them to my next draft.",
    )
    return {"success": True, **result}


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
    log_activity("Planx", "Saved draft", section["title"])
    return {"success": True, "section": section}


@app.post("/api/thesis/draft")
def draft_thesis_section(request: DraftRequest) -> dict[str, Any]:
    section = get_section(request.section_key)
    if not section:
        raise HTTPException(status_code=404, detail="Unknown thesis section")
    papers = list_papers()
    if request.evidence_dois is not None:
        selected = {doi.strip().lower() for doi in request.evidence_dois if doi.strip()}
        if not selected:
            raise HTTPException(status_code=400, detail="Select at least one approved source for Planx")
        papers = [paper for paper in papers if paper["doi"].strip().lower() in selected]
        if not papers:
            raise HTTPException(status_code=400, detail="None of the selected sources are available")
    content = build_evidence_outline(request.section_key, papers)
    mode = "local_outline"
    saved = save_section(request.section_key, content)
    log_activity("Planx", "Prepared draft", f"{saved['title']} — {len(papers)} selected sources")
    public_url = os.getenv("XENG_PUBLIC_URL", "").strip().rstrip("/")
    if public_url:
        try:
            buttons = [[{"text": "✅ Mark reviewed", "callback_data": f"draft:reviewed:{request.section_key}"}]]
            if request.section_key == "methodology":
                buttons[0].append({"text": "🔓 Approve method", "callback_data": "method:approve"})
            buttons.append([{"text": "Open Thesis Studio", "url": f"{public_url}/#thesis-studio"}])
            send_agent_action(
                "Planx", "Review requested",
                f"The {saved['title']} is ready for your decision.",
                "Review it in XENG, then use the action below.", buttons,
            )
        except Exception:
            pass
    else:
        _notify_agent(
            "Planx", "Draft ready",
            f"I prepared the {saved['title']} draft using {len(papers)} source(s) selected by you.",
            "Please review the academic wording and in-text citations before saving or approving it.",
        )
    return {"success": True, "mode": mode, "section": saved, "source_count": len(papers)}


@app.post("/api/methodology/approve")
def approve_methodology(request: ApprovalRequest) -> dict[str, Any]:
    if not request.confirmed:
        raise HTTPException(status_code=400, detail="Approval confirmation is required")
    try:
        result = _approve_methodology_action(request.notes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _notify_agent(
        "Xengineer", "Methodology approved",
        "The methodology gate is open and I can begin converting it into prototype tasks.",
        "No action is required unless you want to revise the methodology.",
    )
    return {"success": True, **result}


@app.post("/api/methodology/reopen")
def reopen_methodology() -> dict[str, Any]:
    section = get_section("methodology")
    if section:
        save_section("methodology", section["content"], status="draft")
    gate = set_methodology_status("locked", "Reopened for editing")
    log_activity("Cordy", "Methodology reopened", "Xengineer development gate locked")
    refresh_team_states()
    _notify_agent(
        "Cordy", "Approval changed",
        "The methodology was reopened, so I paused Xengineer and locked development again.",
        "Finish your revisions and approve the methodology when it is ready.",
    )
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
    payload = result.to_dict()
    public_url = os.getenv("XENG_PUBLIC_URL", "").strip().rstrip("/")
    if public_url:
        try:
            send_agent_action(
                "TeeHee", "Prototype check" if result.success else "Issue found",
                f"The {request.tool} operation {'completed successfully' if result.success else 'was stopped safely'}.",
                "Review the result, then acknowledge it below.",
                [
                    [{"text": "✅ Acknowledge", "callback_data": f"test:ack:{request.tool}"}],
                    [{"text": "Open Build Lab", "url": f"{public_url}/#command-lab"}],
                ],
            )
        except Exception:
            pass
    else:
        _notify_agent(
            "TeeHee", "Prototype check" if result.success else "Issue found",
            f"The {request.tool} operation {'completed successfully' if result.success else 'was stopped safely'}.",
            "Review the execution result in Build Lab." if not result.success else "No action is required unless you want to run another test.",
        )
    return payload


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
