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
from application.notifications import send_telegram
from application.research import search_papers

DEFAULT_TOPICS = (
    "LLM agent tool selection multi-step execution;"
    "agentic AI local image management;"
    "LLM agents planning tool use evaluation"
)


def research_topics() -> list[str]:
    raw = os.getenv("XENG_RESEARCH_TOPICS", DEFAULT_TOPICS)
    return [topic.strip() for topic in raw.split(";") if topic.strip()]


def run_research_cycle() -> dict[str, object]:
    job_id = start_job("research-cycle")
    new_count = 0
    seen_count = 0
    errors: list[str] = []
    try:
        rows = max(1, min(int(os.getenv("XENG_RESULTS_PER_TOPIC", "8")), 20))
        for topic in research_topics():
            try:
                for paper in search_papers(topic, rows):
                    _, created = save_candidate(paper, topic)
                    new_count += int(created)
                    seen_count += 1
            except Exception as exc:  # one topic must not stop the full cycle
                errors.append(f"{topic}: {exc}")

        pending = len(list_candidates("pending", 1000))
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
            "Research Agent",
            "Autonomous cycle finished",
            f"{new_count} new papers · {pending} waiting for review",
        )
        message = (
            "XENG research update\n"
            f"New papers: {new_count}\n"
            f"Waiting for review: {pending}\n"
            f"Topics checked: {len(research_topics())}\n"
            f"Status: {result['status']}"
        )
        try:
            result["telegram_sent"] = send_telegram(message)
        except Exception as exc:
            result["telegram_sent"] = False
            errors.append(f"Telegram: {exc}")
        return result
    except Exception as exc:
        finish_job(job_id, "failed", str(exc))
        raise
