"""Autonomous, review-first research operation."""

from __future__ import annotations

import json
import os

from application.database import (
    finish_job,
    list_candidates,
    log_activity,
    save_candidate,
    start_job,
)
from application.notifications import send_paper_review, send_team_update
from application.research import meets_thesis_source_rules, search_papers
from application.agents import refresh_team_states

CORE_RESEARCH_TOPICS = (
    "artificial intelligence tool selection and multi-step task execution",
    "autonomous software agents planning and action execution",
    "function calling tool use and API orchestration",
    "intelligent image retrieval organization and digital asset management",
    "computer vision assisted personal photo management",
    "local-first AI privacy security and safe file automation",
    "human in the loop approval for autonomous AI systems",
    "evaluation benchmarks reliability and failure recovery for AI agents",
)


def research_topics() -> list[str]:
    custom = [
        topic.strip() for topic in os.getenv("XENG_RESEARCH_TOPICS", "").split(";")
        if topic.strip()
    ]
    # Custom interests extend the project profile; they never remove its core themes.
    return list(dict.fromkeys((*custom, *CORE_RESEARCH_TOPICS)))


def run_research_cycle() -> dict[str, object]:
    job_id = start_job("research-cycle")
    new_count = 0
    new_candidates: list[dict[str, object]] = []
    seen_count = 0
    errors: list[str] = []
    try:
        rows = max(1, min(int(os.getenv("XENG_RESULTS_PER_TOPIC", "5")), 20))
        for topic in research_topics():
            try:
                for paper in search_papers(topic, rows):
                    candidate, created = save_candidate(paper, topic)
                    new_count += int(created)
                    if created:
                        new_candidates.append(candidate)
                    seen_count += 1
            except Exception as exc:  # one topic must not stop the full cycle
                errors.append(f"{topic}: {exc}")

        pending = sum(
            1 for candidate in list_candidates("pending", 1000)
            if meets_thesis_source_rules(candidate["paper"])
        )
        result = {
            "job_id": job_id,
            "status": "completed" if seen_count or not errors else "failed",
            "topics": len(research_topics()),
            "papers_checked": seen_count,
            "new_candidates": new_count,
            "pending_review": pending,
            "errors": errors,
        }
        finish_job(job_id, result["status"], json.dumps(result))
        log_activity(
            "Scoot",
            "Autonomous cycle finished",
            f"{new_count} new papers · {pending} waiting for review",
        )
        team_updates = refresh_team_states(seen_count, new_count)
        try:
            sent_reviews = 0
            for candidate in new_candidates:
                sent_reviews += int(send_paper_review(candidate))
            result["paper_reviews_sent"] = sent_reviews
            result["telegram_sent"] = send_team_update(team_updates)
        except Exception as exc:
            result["telegram_sent"] = False
            errors.append(f"Telegram: {exc}")
        return result
    except Exception as exc:
        finish_job(job_id, "failed", str(exc))
        raise
