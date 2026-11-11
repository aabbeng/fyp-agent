"""Evidence-bound, plain-text academic drafting helpers for Planx."""

from __future__ import annotations

from typing import Any

SECTION_NAMES = {"literature_review": "Literature Review", "methodology": "Methodology", "expected_results": "Expected Results"}


def author_year(paper: dict[str, Any]) -> str:
    authors = paper.get("authors") or []
    family = authors[0].split()[-1] if authors else "Unknown"
    if len(authors) > 1:
        family += " et al."
    return f"{family}, {paper.get('year') or 'n.d.'}"


def parenthetical(papers: list[dict[str, Any]]) -> str:
    return "(" + "; ".join(author_year(paper) for paper in papers) + ")" if papers else ""


def select_theme(papers: list[dict[str, Any]], terms: tuple[str, ...]) -> list[dict[str, Any]]:
    return [paper for paper in papers if any(term in paper.get("title", "").casefold() for term in terms)][:6]


def literature_review(papers: list[dict[str, Any]]) -> str:
    foundations = select_theme(papers, ("toolformer", "react", "autonomous agent", "toolllm", "tool-augmented"))
    function_calling = select_theme(papers, ("function call", "api", "toolace", "dispatchqa", "structured"))
    evaluation = select_theme(papers, ("benchmark", "leaderboard", "evaluation", "reflexion", "executable"))
    broad = papers[:5]
    return (
        "Literature Review\n\n"
        "Tool-Augmented Language Models and Autonomous Agents\n\n"
        "Research on large language models has increasingly moved beyond text generation towards systems that can "
        "reason about a task, select an external tool, perform an action and respond to the resulting observation. "
        "The approved literature positions tool use as a central capability in the development of autonomous "
        f"language-model agents {parenthetical(foundations or broad)}. Taken together, these sources provide the "
        "conceptual background for examining an agent as a controlled workflow rather than as an isolated text "
        "generator. Detailed comparisons of their findings must remain tied to verified abstracts or full papers.\n\n"
        "Function Calling and Tool Selection\n\n"
        "A major theme in the literature concerns function calling: the process through which a model identifies an "
        "appropriate tool and supplies arguments in the required structure. Existing work covers API-oriented "
        "benchmarks, structured generation and datasets designed to measure whether models can select and invoke "
        f"tools correctly {parenthetical(function_calling or broad)}. This theme is directly relevant to the present "
        "study because the prototype must distinguish between available image-management tools and produce valid, "
        "safe arguments for each operation.\n\n"
        "Multi-Step Execution, Feedback and Recovery\n\n"
        "Tool selection alone does not guarantee successful task completion. An agent may also need to preserve "
        "context across dependent steps, interpret observations and revise its behaviour after an unsuccessful "
        f"action. The selected literature therefore supports attention to execution traces, feedback and recovery "
        f"as part of agent evaluation {parenthetical(evaluation or foundations or broad)}. For this FYP, these ideas "
        "will be examined through controlled single-tool, multi-step and failure scenarios rather than through "
        "unrestricted autonomous access.\n\n"
        "Evaluation and Research Gap\n\n"
        "Current research provides substantial work on general tool-use benchmarks and large collections of APIs; "
        "however, less attention is given to lightweight agents operating within a narrow, safety-controlled local "
        "file environment. This creates a practical gap between broad benchmark performance and reliable execution "
        "in a bounded personal workflow. The present study addresses that gap by developing and evaluating an agent "
        "that performs a limited set of image-management tasks while enforcing path validation, explicit methodology "
        "approval and observable execution records. This positioning will be refined as Evi-Revy verifies the full "
        "content, methods and limitations of each approved source."
    )


def methodology(papers: list[dict[str, Any]]) -> str:
    citation = parenthetical(papers[:5])
    return (
        "Methodology\n\nResearch Design\n\n"
        "This study will use a design-and-evaluation approach to develop a controlled language-model agent for local "
        "image-management tasks. The prototype will be limited to three explicit operations: retrieving images by "
        "date, creating a destination folder and copying selected images. This bounded design allows the study to "
        "examine tool selection and multi-step execution while reducing the risks of unrestricted file access.\n\n"
        "Prototype Development\n\n"
        "The system will connect a lightweight language model to a validated controller. Every requested operation "
        "will be checked against an allowlist, and every file path will be resolved within a user-selected gallery "
        "before execution. The approved literature on function calling and tool-using agents will guide the structure "
        f"of tool descriptions, argument validation and execution feedback {citation}.\n\n"
        "Evaluation Procedure\n\n"
        "Evaluation will include single-tool requests, dependent multi-step tasks and failure scenarios containing "
        "invalid or unsafe inputs. The recorded measures will include tool-selection accuracy, argument correctness, "
        "task-completion rate and the agent's response to execution errors. All scenarios, expected outcomes and "
        "observed results will be stored so that the prototype can be assessed consistently.\n\n"
        "Approval and Development Control\n\n"
        "This methodology remains a draft until it is reviewed and approved by the researcher. Xengineer must not "
        "change or implement the prototype from unapproved methodological claims."
    )


def expected_results(papers: list[dict[str, Any]]) -> str:
    citation = parenthetical(papers[:5])
    return (
        "Expected Results\n\nAnticipated Prototype Performance\n\n"
        "The prototype is expected to perform most reliably on direct, single-tool requests because these tasks "
        "require fewer decisions and contain fewer dependent states. Multi-step requests are expected to create "
        "greater difficulty because an error in an early tool call may affect every later action. This expectation "
        f"is consistent with the study's focus on function calling, execution feedback and agent evaluation {citation}.\n\n"
        "Anticipated Safety and Evaluation Outcomes\n\n"
        "Strict path validation and an explicit tool allowlist are expected to prevent operations outside the selected "
        "gallery. Failure scenarios should reveal where the agent misunderstands arguments, selects an unsuitable "
        "tool or fails to recover after receiving an error. These statements are predictions rather than research "
        "findings and must be revised after the prototype experiments have been completed."
    )


def build_evidence_outline(section_key: str, papers: list[dict[str, Any]]) -> str:
    if section_key not in SECTION_NAMES:
        raise ValueError("Unknown thesis section")
    if section_key == "literature_review":
        return literature_review(papers)
    if section_key == "methodology":
        return methodology(papers)
    return expected_results(papers)
