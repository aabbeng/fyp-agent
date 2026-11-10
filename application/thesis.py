"""Evidence-bound thesis drafting helpers."""

from __future__ import annotations

from typing import Any


SECTION_NAMES = {
    "literature_review": "Literature Review",
    "methodology": "Methodology",
    "expected_results": "Expected Results",
}


def citation_label(paper: dict[str, Any]) -> str:
    authors = paper.get("authors") or []
    family = authors[0].split()[-1] if authors else "Unknown"
    if len(authors) > 1:
        family += " et al."
    return f"{family} ({paper.get('year') or 'n.d.'})"


def build_evidence_outline(section_key: str, papers: list[dict[str, Any]]) -> str:
    if section_key not in SECTION_NAMES:
        raise ValueError("Unknown thesis section")
    evidence = "\n".join(
        f"- {citation_label(paper)} — {paper['title']} [DOI: {paper['doi']}]"
        for paper in papers
    ) or "- No verified papers saved yet. Add evidence before writing claims."

    if section_key == "literature_review":
        return (
            "## Draft structure\n\n"
            "### 1. LLM-based agents and tool use\n"
            "Explain the move from text generation to tool-supported actions.\n\n"
            "### 2. Function calling and tool selection\n"
            "Compare how prior studies evaluate correct tools and arguments.\n\n"
            "### 3. Multi-step execution and feedback\n"
            "Discuss dependent actions, observations, and recovery from failure.\n\n"
            "### 4. Research gap\n"
            "State what is still unknown for lightweight models in a controlled local gallery.\n\n"
            f"## Verified evidence\n{evidence}"
        )
    if section_key == "methodology":
        return (
            "## Proposed method\n\n"
            "1. Prepare a controlled local image dataset.\n"
            "2. Implement three safe tools: find by date, create folder, and copy images.\n"
            "3. Connect a lightweight LLM through a validated controller.\n"
            "4. Run single-tool, multi-step, and failure scenarios.\n"
            "5. Measure tool-selection accuracy, argument correctness, task completion, and error handling.\n\n"
            "## Approval note\n"
            "The development agent must follow this method after you approve it.\n\n"
            f"## Supporting evidence\n{evidence}"
        )
    return (
        "## Anticipated outcomes — not actual findings\n\n"
        "- Single-tool tasks are expected to be easier than dependent multi-step tasks.\n"
        "- Strict argument and path checks are expected to reduce unsafe file operations.\n"
        "- Failure scenarios are expected to reveal limits in feedback use and recovery.\n\n"
        "These are predictions only. Replace them with measured findings in the Results chapter.\n\n"
        f"## Evidence used to form the expectations\n{evidence}"
    )
