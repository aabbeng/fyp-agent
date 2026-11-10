"""Optional OpenAI Agents SDK connection for evidence-bound thesis drafting."""

from __future__ import annotations

import os
import re
from typing import Any


class AgentNotConfiguredError(RuntimeError):
    pass


class UnsupportedCitationError(RuntimeError):
    pass


def status() -> dict[str, Any]:
    configured = bool(os.getenv("OPENAI_API_KEY", "").strip())
    return {
        "configured": configured,
        "model": os.getenv("OPENAI_MODEL", "gpt-6.1-sol"),
        "agents": ["Coordinator", "Research Analyst", "Thesis Writer", "Development Gate"],
    }


async def draft_with_team(
    section_key: str,
    current_content: str,
    focus: str,
    papers: list[dict[str, Any]],
) -> str:
    if not status()["configured"]:
        raise AgentNotConfiguredError(
            "AI writer is not connected. Add OPENAI_API_KEY, then restart the dashboard."
        )
    if not papers:
        raise AgentNotConfiguredError("Save at least one verified paper before using the writer")

    from agents import Agent, Runner

    model = status()["model"]
    research_analyst = Agent(
        name="Research Analyst",
        model=model,
        instructions=(
            "Review only the supplied verified paper metadata. Identify useful themes, methods, "
            "limits, and gaps. Never invent papers, DOIs, quotes, results, or page numbers."
        ),
    )
    thesis_writer = Agent(
        name="Thesis Writer",
        model=model,
        instructions=(
            "Write a concise undergraduate thesis draft in clear academic English. Use only the "
            "verified evidence supplied by the user. Mark expected results as predictions. "
            "Never claim an experiment has happened unless the supplied evidence says so. "
            "Cite sources using [DOI: value]."
        ),
        tools=[
            research_analyst.as_tool(
                tool_name="review_verified_evidence",
                tool_description="Review the verified papers before drafting the thesis section.",
            )
        ],
    )
    evidence = "\n".join(
        f"- {paper['title']} | authors: {', '.join(paper.get('authors', []))} | "
        f"year: {paper.get('year')} | DOI: {paper['doi']} | abstract: {paper.get('abstract', '')}"
        for paper in papers
    )
    prompt = (
        f"Section: {section_key}\nFocus: {focus or 'Improve this section using verified evidence.'}\n"
        f"Current draft:\n{current_content or '(empty)'}\n\nVerified evidence:\n{evidence}"
    )
    result = await Runner.run(thesis_writer, prompt)
    draft = str(result.final_output).strip()
    allowed_dois = {paper["doi"].lower() for paper in papers}
    cited_dois = {
        match.rstrip(".,;)").lower()
        for match in re.findall(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", draft, flags=re.I)
    }
    unsupported = cited_dois - allowed_dois
    if unsupported:
        raise UnsupportedCitationError(
            f"Writer returned unsupported DOI(s): {', '.join(sorted(unsupported))}"
        )
    return draft
