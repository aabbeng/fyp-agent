"""Evidence-bound, plain-text academic drafting helpers for Planx."""

from __future__ import annotations

from typing import Any

from application.thesis_foundation import EVALUATION_METRICS, EXCLUSIONS, OBJECTIVES, PROJECT_TITLE, SCOPE

SECTION_NAMES = {
    "literature_review": "Chapter 2 — Literature Review",
    "methodology": "Chapter 3 — Methodology",
    "expected_results": "Chapter 4 — Expected Results",
}


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
        "CHAPTER 2\n\nLITERATURE REVIEW\n\n"
        "2.1 Introduction\n\n"
        f"This chapter critically reviews knowledge relevant to {PROJECT_TITLE}. It establishes the concepts, "
        "compares approaches and evaluation practices, and identifies the gap addressed by the three approved "
        "research objectives in Chapter 1.\n\n"
        "2.2 LLM-Based Agents and Tool-Augmented Systems\n\n"
        "Research on large language models has increasingly moved beyond text generation towards systems that can "
        "reason about a task, select an external tool, perform an action and respond to the resulting observation. "
        "The approved literature positions tool use as a central capability in the development of autonomous "
        f"language-model agents {parenthetical(foundations or broad)}. Taken together, these sources provide the "
        "conceptual background for examining an agent as a controlled workflow rather than as an isolated text "
        "generator. Detailed comparisons of their findings must remain tied to verified abstracts or full papers.\n\n"
        "2.3 Function Calling and Tool Selection\n\n"
        "A major theme in the literature concerns function calling: the process through which a model identifies an "
        "appropriate tool and supplies arguments in the required structure. Existing work covers API-oriented "
        "benchmarks, structured generation and datasets designed to measure whether models can select and invoke "
        f"tools correctly {parenthetical(function_calling or broad)}. This theme is directly relevant to the present "
        "study because the prototype must distinguish between available image-management tools and produce valid, "
        "safe arguments for each operation.\n\n"
        "2.4 Multi-Step Execution, Feedback and Error Recovery\n\n"
        "Tool selection alone does not guarantee successful task completion. An agent may also need to preserve "
        "context across dependent steps, interpret observations and revise its behaviour after an unsuccessful "
        f"action. The selected literature therefore supports attention to execution traces, feedback and recovery "
        f"as part of agent evaluation {parenthetical(evaluation or foundations or broad)}. For this FYP, these ideas "
        "will be examined through controlled single-tool, multi-step and failure scenarios rather than through "
        "unrestricted autonomous access.\n\n"
        "2.5 Local Image Management and Controlled File Operations\n\n"
        "The application domain is deliberately narrow: local image retrieval by date, folder creation and copying "
        "selected files. The review will compare relevant local automation and image-management approaches without "
        f"expanding into the excluded areas defined in Chapter 1: {EXCLUSIONS}\n\n"
        "2.6 Evaluation of Tool-Using Agents\n\n"
        f"The reviewed evaluation approaches will be related to the approved measures of {', '.join(EVALUATION_METRICS)}. "
        "A comparative table will record each study's task setting, model, tools, metrics, findings and limitations.\n\n"
        "2.7 Evaluation and Research Gap\n\n"
        "Current research provides substantial work on general tool-use benchmarks and large collections of APIs; "
        "however, less attention is given to lightweight agents operating within a narrow, safety-controlled local "
        "file environment. This creates a practical gap between broad benchmark performance and reliable execution "
        "in a bounded personal workflow. The present study addresses that gap by developing and evaluating an agent "
        "that performs a limited set of image-management tasks while enforcing path validation, explicit methodology "
        "approval and observable execution records. This positioning will be refined as Evi-Revy verifies the full "
        "content, methods and limitations of each approved source.\n\n"
        "2.8 Conceptual Framework\n\n"
        "The proposed framework links a natural-language instruction to tool selection, argument validation, controlled "
        "execution, structured observation and either the next action or task completion. It provides the conceptual "
        "bridge from the literature to the methodology in Chapter 3.\n\n"
        "2.9 Chapter Summary\n\n"
        "This chapter will conclude by synthesising the evidence, stating the research gap and showing how that gap "
        "supports the approved objectives. It will not introduce unverified findings or claims."
    )


def methodology(papers: list[dict[str, Any]]) -> str:
    citation = parenthetical(papers[:5])
    return (
        "CHAPTER 3\n\nMETHODOLOGY\n\n3.1 Introduction\n\n"
        "This chapter explains how the approved research objectives will be achieved and evaluated. Every design "
        "decision remains within the scope established in Chapter 1.\n\n"
        "3.2 Research Design and Development Approach\n\n"
        "This study will use a design-and-evaluation approach to develop a controlled language-model agent for local "
        "image-management tasks. The prototype will be limited to three explicit operations: retrieving images by "
        "date, creating a destination folder and copying selected images. This bounded design allows the study to "
        "examine tool selection and multi-step execution while reducing the risks of unrestricted file access.\n\n"
        "3.3 Requirements and Testable Task Scenarios\n\n"
        "Functional and safety requirements will be converted into exact-date, date-range, multi-step and failure "
        "scenarios, each with expected tool calls, arguments and success conditions.\n\n"
        "3.4 System Architecture and Agent Workflow\n\n"
        "The system will connect a lightweight language model to a validated controller. Every requested operation "
        "will be checked against an allowlist, and every file path will be resolved within a user-selected gallery "
        "before execution. The approved literature on function calling and tool-using agents will guide the structure "
        f"of tool descriptions, argument validation and execution feedback {citation}.\n\n"
        "3.5 Prototype Development\n\n"
        f"The implementation will remain within this approved scope: {SCOPE}\n\n"
        "3.6 Dataset and Experimental Setup\n\n"
        "The controlled image dataset, directory structure, available EXIF dates, fallback rules, model configuration, "
        "hardware and software environment will be documented so the evaluation can be reproduced.\n\n"
        "3.7 Testing and Evaluation Procedure\n\n"
        "Evaluation will include single-tool requests, dependent multi-step tasks and failure scenarios containing "
        "invalid or unsafe inputs. The recorded measures will include tool-selection accuracy, argument correctness, "
        "task-completion rate and the agent's response to execution errors. All scenarios, expected outcomes and "
        "observed results will be stored so that the prototype can be assessed consistently.\n\n"
        "3.8 Data Analysis\n\n"
        "Tool-selection accuracy, argument correctness and task-completion rate will be calculated from the documented "
        "test outcomes. Execution logs will be analysed to explain failures and recovery behaviour.\n\n"
        "3.9 Safety, Privacy and Research Integrity\n\n"
        "Testing will use designated directories, validated paths, an explicit tool allowlist, step limits and "
        "confirmation where appropriate. No result will be reported before it is observed.\n\n"
        "3.10 Chapter Summary and Development Gate\n\n"
        "This methodology remains a draft until it is reviewed and approved by the researcher. Xengineer must not "
        "change or implement the prototype from unapproved methodological claims."
    )


def expected_results(papers: list[dict[str, Any]]) -> str:
    citation = parenthetical(papers[:5])
    return (
        "CHAPTER 4\n\nEXPECTED RESULTS\n\n4.1 Introduction\n\n"
        "This proposal-stage chapter states anticipated outcomes only. It will become Implementation, Testing and "
        "Analysis of Results after the prototype experiments are completed.\n\n"
        "4.2 Expected Prototype Deliverables\n\n"
        "The expected deliverables are a functional agent prototype, documented requirements and architecture, "
        "validated Python image-management tools, a controlled dataset, execution logs and evaluation results.\n\n"
        "4.3 Expected Results by Research Objective\n\n"
        "The first objective is expected to produce measurable tool-selection and argument-generation performance. "
        "The second is expected to demonstrate whether returned observations support dependent actions. The third "
        "will report the approved evaluation metrics across single-step, multi-step and error-handling scenarios.\n\n"
        "4.4 Anticipated Prototype Performance\n\n"
        "The prototype is expected to perform most reliably on direct, single-tool requests because these tasks "
        "require fewer decisions and contain fewer dependent states. Multi-step requests are expected to create "
        "greater difficulty because an error in an early tool call may affect every later action. This expectation "
        f"is consistent with the study's focus on function calling, execution feedback and agent evaluation {citation}.\n\n"
        "4.5 Anticipated Safety and Evaluation Outcomes\n\n"
        "Strict path validation and an explicit tool allowlist are expected to prevent operations outside the selected "
        "gallery. Failure scenarios should reveal where the agent misunderstands arguments, selects an unsuitable "
        "tool or fails to recover after receiving an error. These statements are predictions rather than research "
        "findings and must be revised after the prototype experiments have been completed.\n\n"
        "4.6 Expected Contribution and Limitations\n\n"
        "The expected contribution is evidence about a bounded agent's reliability in a controlled local workflow, "
        "not a claim of general autonomous capability. Limitations will follow the scope and exclusions in Chapter 1.\n\n"
        "4.7 Chapter Summary\n\n"
        "The final version of this chapter must replace every prediction with observed implementation details, tables, "
        "test results and evidence-based discussion."
    )


def build_evidence_outline(section_key: str, papers: list[dict[str, Any]]) -> str:
    if section_key not in SECTION_NAMES:
        raise ValueError("Unknown thesis section")
    if section_key == "literature_review":
        return literature_review(papers)
    if section_key == "methodology":
        return methodology(papers)
    return expected_results(papers)
