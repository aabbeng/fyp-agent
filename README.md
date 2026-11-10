# FYP Agent Workspace

Development workspace for **LLM-Based Agentic AI for Tool Selection and Multi-Step Execution in Local Image Management**.

## Repository areas

- `application/` — prototype source code
- `tests/` — deterministic unit and integration tests
- `experiments/` — experiment configurations and recorded results
- `research/` — verified literature notes and evidence
- `thesis/` — thesis drafts and evidence-linked updates
- `agent-control/` — operating rules for the development agent

The safe tool layer, 20-case evaluation matrix, and first local dashboard are now available. The next milestone is the executable scenario runner, followed by lightweight LLM integration.

## Run the local dashboard

Create a virtual environment, install the requirements, and start the app:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python run.py
```

Open `http://127.0.0.1:8000`. Use **Load demo gallery** to try the safe tools without using personal images.
