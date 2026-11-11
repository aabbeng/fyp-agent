# XENG Workspace

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
2. **Thesis Organizer** prepares evidence-linked outlines for the literature review, methodology, and expected results.
3. **Methodology Gate** requires the student to review and approve the method.
4. **Development Agent** is unlocked only after that approval and uses the safe local tool layer.

The full workflow runs without a paid AI API. Draft automation is deterministic and uses only papers saved in the evidence library, so it does not invent sources or create extra API costs.

## Run the local dashboard

Create a virtual environment, install the requirements, and start the app:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python run.py
```

Open `http://127.0.0.1:8000`. Use **Load demo gallery** to try the safe tools without using personal images.

## Optional research setting

Set these in PowerShell before starting the dashboard:

```powershell
$env:CROSSREF_MAILTO="your-university-email@example.com"
```

- `CROSSREF_MAILTO` identifies this academic client to Crossref's polite pool.

No OpenAI API key or paid AI subscription is required.

Research papers, drafts, approval state, and activity history are stored locally in `runtime/fyp-agent.db`. The `runtime/` folder is ignored by Git.

## Put XENG online

This setup keeps the dashboard online and runs research every 6 hours without a paid AI API:

1. Create a free Supabase project. In **Connect**, copy the session-pooler PostgreSQL connection string.
2. In Render, create a **Blueprint** from this repository. Render reads `render.yaml`.
3. Add these private Render values: `DATABASE_URL`, `XENG_ADMIN_PASSWORD`, `CROSSREF_MAILTO`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and a long random `TELEGRAM_WEBHOOK_SECRET`. Set `XENG_PUBLIC_URL` to `https://xeng.onrender.com`.
4. In GitHub → **Settings → Secrets and variables → Actions**, add secrets named `DATABASE_URL`, `CROSSREF_MAILTO`, `TELEGRAM_BOT_TOKEN`, and `TELEGRAM_CHAT_ID`.
5. Optionally add the repository variable `XENG_RESEARCH_TOPICS`. Separate topics with semicolons.
6. Merge this branch into the default branch. GitHub scheduled workflows run from the default branch.

The autonomous worker only adds papers to a **pending review queue**. You approve a paper before it enters the thesis evidence library. It never auto-approves methodology or executes the prototype.

The free Render service can sleep when unused, but GitHub Actions still runs the research operation and writes results into Supabase. Telegram sends the run summary to you.

### Two-way Telegram control

After Render finishes deploying, sign in to XENG and open **Operation centre**. Click **Enable replies** once to register the secure Telegram webhook. Click **Send 5 papers** to send the next five pending Evi-Revy reviews. Only the configured `TELEGRAM_CHAT_ID` can use the decision buttons.

### Telegram setup

1. Message `@BotFather` in Telegram, create a bot, and copy its token.
2. Send one message to your new bot.
3. Open `https://api.telegram.org/botYOUR_TOKEN/getUpdates` and copy the numeric `chat.id`.
4. Save both values as GitHub Actions secrets. Never commit them to this repository.
