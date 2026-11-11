"""Deterministic XENG agent team and controlled handoffs."""

from __future__ import annotations

from application.database import (
    list_candidates,
    list_papers,
    methodology_status,
    send_agent_message,
    update_agent_state,
)


def _review_summary() -> tuple[int, int]:
    candidates = list_candidates("pending", 1000)
    reviewable = sum(
        1 for item in candidates
        if item["paper"].get("title") and item["paper"].get("doi")
        and (item["paper"].get("year") or item["paper"].get("abstract"))
    )
    return len(candidates), reviewable


def refresh_team_states(papers_checked: int = 0, new_candidates: int = 0) -> list[str]:
    """Move each specialist to the correct stage without bypassing human approval."""
    pending, reviewable = _review_summary()
    approved = len(list_papers())
    method_approved = methodology_status()["status"] == "approved"

    updates = []
    update_agent_state(
        "scoot", "done", "Search scholarly indexes",
        f"Checked {papers_checked} papers and found {new_candidates} new candidates.",
    )
    updates.append(f"Scoot: checked {papers_checked}, found {new_candidates} new")
    send_agent_message("scoot", "evi-revy", f"Please review {pending} paper candidates.")

    evi_status = "review" if pending else "waiting"
    update_agent_state(
        "evi-revy", evi_status, "Check candidate metadata and relevance",
        f"{reviewable} of {pending} candidates have enough metadata for your review.",
    )
    updates.append(f"Evi-Revy: {pending} papers waiting for human approval")
    send_agent_message("evi-revy", "planx", f"{approved} approved papers are ready for thesis planning.")

    if approved:
        update_agent_state(
            "planx", "working", "Prepare evidence-linked thesis outlines",
            f"Working from {approved} approved papers. Methodology still needs your approval.",
        )
    else:
        update_agent_state(
            "planx", "blocked", "Wait for approved evidence",
            "I need at least one approved paper before planning the thesis.",
        )
    updates.append(f"Planx: {approved} approved evidence papers available")

    if method_approved:
        update_agent_state(
            "xengineer", "working", "Convert methodology into prototype tasks",
            "Methodology approved. Prototype development is unlocked.",
        )
        send_agent_message("xengineer", "teehee", "Prepare the test plan for the unlocked build.")
        update_agent_state(
            "teehee", "waiting", "Prepare prototype tests",
            "Test plan ready; waiting for Xengineer's next completed build.",
        )
    else:
        update_agent_state(
            "xengineer", "blocked", "Wait for methodology approval",
            "Development remains locked until you approve the methodology.",
        )
        update_agent_state(
            "teehee", "blocked", "Wait for a prototype build",
            "Testing starts after Xengineer produces an approved build.",
        )
    updates.append("Xengineer and TeeHee: " + ("build stage unlocked" if method_approved else "waiting at approval gate"))

    update_agent_state(
        "cordy", "working", "Coordinate agents and report progress",
        f"Team synced: {pending} reviews, {approved} approved papers, method "
        f"{'open' if method_approved else 'locked'}.",
    )
    send_agent_message("cordy", "scoot", "Next research cycle remains scheduled every 6 hours.")
    updates.append("Cordy: team synced and Telegram report prepared")
    return updates
