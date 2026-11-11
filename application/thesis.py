"""Evidence-bound thesis drafting helpers."""

from __future__ import annotations

from typing import Any


SECTION_NAMES = {
    "literature_review": "Literature Review",
    "methodology": "Methodology",
    "expected_results": "Expected Results",
}

PLANX_REVIEW_PRINCIPLES = (
    "summarise", "analyse", "evaluate", "synthesise",
    "trace how knowledge evolved", "identify debates and agreements",
    "identify emerging trends", "identify unresolved problems and gaps",
    "position the FYP against previous research",
)


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
        f"- [{('CLAIM-READY' if paper.get('abstract') else 'BIBLIOGRAPHY-ONLY')}] "
        f"{citation_label(paper)} — {paper['title']} [DOI: {paper['doi']}]"
        for paper in papers
    ) or "- No verified papers saved yet. Add evidence before writing claims."

    if section_key == "literature_review":
        return (
            "## Planx literature review workspace\n\n"
            "### Review goal\n"
            "Build a critical and evidence-linked account of existing knowledge—not a list of paper summaries. "
            "The review must summarise, analyse, evaluate, and synthesise the key literature.\n\n"
            "### 1. Scope and source selection\n"
            "Define the specific research area, inclusion boundaries, and why each key source is relevant. "
            "Use a comprehensive thesis approach while keeping only sources that support the research problem.\n\n"
            "### 2. Development of knowledge\n"
            "Explain how the field moved from language-model reasoning to tool use, function calling, "
            "multi-step agents, feedback, and evaluation. Distinguish established findings from emerging work.\n\n"
            "### 3. Thematic synthesis\n"
            "Group evidence across sources under themes rather than reviewing one paper at a time:\n"
            "- LLM-based agents and tool use\n"
            "- Function calling and tool selection\n"
            "- Multi-step execution, observation, and recovery\n"
            "- Evaluation benchmarks, reliability, and safety\n\n"
            "### 4. Critical evaluation\n"
            "Compare methods and evidence quality. Identify agreements, contradictions, controversies, "
            "limitations, unresolved problems, and promising new approaches.\n\n"
            "### 5. Research gap and FYP position\n"
            "State what remains under-researched and explain clearly how this FYP extends, builds upon, "
            "or departs from previous work on controlled local tool-using agents.\n\n"
            "### Planx writing rules\n"
            "- Never invent a paper's findings, method, or limitations.\n"
            "- BIBLIOGRAPHY-ONLY sources need an abstract or full-text check before supporting detailed claims.\n"
            "- Every major comparison or claim must be connected to approved evidence.\n"
            "- End each theme with synthesis, not a source-by-source summary.\n\n"
            f"## Evidence readiness map\n{evidence}"
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
