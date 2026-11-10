# FYP Agent Workspace

Development workspace for **LLM-Based Agentic AI for Tool Selection and Multi-Step Execution in Local Image Management**.

## Repository areas

- `application/` — prototype source code
- `tests/` — deterministic unit and integration tests
- `experiments/` — experiment configurations and recorded results
- `research/` — verified literature notes and evidence
- `thesis/` — thesis drafts and evidence-linked updates
- `agent-control/` — operating rules for the development agent

The workspace now follows a controlled research-to-development flow:

1. **Research Agent** searches live Crossref metadata and saves DOI-backed evidence.
2. **Thesis Writer** prepares the literature review, methodology, and expected results from saved evidence.
3. **Methodology Gate** requires the student to review and approve the method.
4. **Development Agent** is unlocked only after that approval and uses the safe local tool layer.

The built-in evidence-outline mode works without an AI key. The optional AI writer uses the OpenAI Agents SDK and rejects DOI citations that are not in the saved evidence library.

## Run the local dashboard

Create a virtual environment, install the requirements, and start the app:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python run.py
```

Open `http://127.0.0.1:8000`. Use **Load demo gallery** to try the safe tools without using personal images.

## Optional connections

Set these in PowerShell before starting the dashboard:

```powershell
$env:OPENAI_API_KEY="your-key"
$env:OPENAI_MODEL="gpt-6.1-sol"
$env:CROSSREF_MAILTO="your-university-email@example.com"
```

- `OPENAI_API_KEY` enables the AI thesis writer. Keep it private and never commit it.
- `OPENAI_MODEL` changes the model used by the agent team.
- `CROSSREF_MAILTO` identifies this academic client to Crossref's polite pool.

Research papers, drafts, approval state, and activity history are stored locally in `runtime/fyp-agent.db`. The `runtime/` folder is ignored by Git.
