"""Autonomous, review-first research operation."""

from __future__ import annotations

import json
import os
from datetime import date

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

ALWAYS_RESEARCH_TOPICS = (
    "LLM agent tool selection multi-step execution",
    "agentic AI local image management",
    "local LLM privacy safe file automation",
    "intelligent image retrieval digital asset management",
)

DAILY_RESEARCH_TOPICS = (
    "large language model autonomous agents",
    "small language models tool use",
    "on-device AI and edge language models",
    "function calling and API orchestration",
    "tool augmented language models",
    "AI planning reasoning and action execution",
    "ReAct agents planning and tool use",
    "multimodal agents for image tasks",
    "semantic image search and visual retrieval",
    "computer vision personal photo organization",
    "AI digital asset management",
    "automated image classification and metadata tagging",
    "privacy preserving artificial intelligence",
    "local-first software and offline AI",
    "safe autonomous file management",
    "human in the loop autonomous systems",
    "AI agent evaluation benchmarks",
    "agent reliability failure recovery and self-correction",
    "autonomous software agents workflow automation",
    "LLM hallucination tool execution safety",
    "natural language interfaces for file management",
    "intelligent desktop automation agents",
    "AI task decomposition and multi-step planning",
    "user trust explainability and controllable AI agents",
)


def research_topics(research_day: date | None = None) -> list[str]:
    custom = [
        topic.strip() for topic in os.getenv("XENG_RESEARCH_TOPICS", "").split(";")
        if topic.strip()
    ]
    current_day = research_day or date.today()
    start = current_day.toordinal() % len(DAILY_RESEARCH_TOPICS)
    rotating = tuple(
        DAILY_RESEARCH_TOPICS[(start + offset) % len(DAILY_RESEARCH_TOPICS)]
        for offset in range(8)
    )
    # Four title anchors always run; eight related themes rotate every day.
    return list(dict.fromkeys((*custom, *ALWAYS_RESEARCH_TOPICS, *rotating)))


def run_research_cycle() -> dict[str, object]:
    job_id = start_job("research-cycle")
    new_count = 0
    new_candidates: list[dict[str, object]] = []
    seen_count = 0
    errors: list[str] = []
    try:
        rows = max(1, min(int(os.getenv("XENG_RESULTS_PER_TOPIC", "3")), 20))
        max_new = max(5, min(int(os.getenv("XENG_MAX_NEW_CANDIDATES", "30")), 100))
        for topic in research_topics():
            if new_count >= max_new:
                break
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
            for candidate in new_candidates[:10]:
                sent_reviews += int(send_paper_review(candidate))
            result["paper_reviews_sent"] = sent_reviews
            result["paper_reviews_in_xeng"] = len(new_candidates)
            result["telegram_sent"] = send_team_update(team_updates)
        except Exception as exc:
            result["telegram_sent"] = False
            errors.append(f"Telegram: {exc}")
        return result
    except Exception as exc:
        finish_job(job_id, "failed", str(exc))
        raise
