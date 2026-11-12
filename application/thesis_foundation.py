"""Approved Chapter 1 facts that every Planx chapter must follow."""

PROJECT_TITLE = (
    "LLM-Based Agentic AI for Tool Selection and Multi-Step Execution "
    "in Local Image Management"
)

RESEARCH_AIM = (
    "Implement and evaluate an LLM-based Agentic AI system for tool selection "
    "and multi-step execution in local image management."
)

OBJECTIVES = (
    "Implement an LLM-based agent that selects predefined Python tools and "
    "generates their arguments from natural-language image-management instructions.",
    "Implement an iterative execution mechanism that uses tool results to perform "
    "dependent actions in multi-step image-management tasks.",
    "Evaluate tool-selection accuracy, argument correctness and task-completion "
    "rate using predefined single-step, multi-step and error-handling scenarios.",
)

RESEARCH_QUESTIONS = (
    "How accurately can the agent select predefined tools and generate the required arguments?",
    "Can the agent use returned tool results to complete dependent multi-step tasks?",
    "What are its tool-selection accuracy, argument correctness and task-completion rate?",
)

SCOPE = (
    "One pretrained LLM-based agent; a Python controller; designated Windows directories; "
    "image retrieval by date or date range; destination-folder creation; copying selected "
    "images; predefined tools only; a controlled dataset; and predefined test scenarios."
)

EXCLUSIONS = (
    "Image-content recognition, semantic image search, facial recognition, cloud image "
    "storage, voice interaction, model training or fine-tuning, unrestricted code execution, "
    "permanent deletion and general desktop automation."
)

EVALUATION_METRICS = (
    "tool-selection accuracy",
    "argument correctness",
    "task-completion rate",
)

