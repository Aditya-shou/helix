# Helix

**Your personal autonomous engineering and reading OS.**

Helix understands your codebases, tracks your reading, generates improvement tasks, and remembers everything across runs — all from a single app you double-click to open.

---

## What Helix does

**For code projects:**
- Reads your filesystem, code structure, and architecture automatically
- Detects missing tests, config issues, and architectural risks
- Generates structured improvement tasks (P0/P1/P2) and persists them across runs
- Tracks progress over time — knows when something improved and won't suggest it again
- Manages multiple projects and tells you where to focus next

**For books:**
- Upload any PDF and read it inside Helix
- Remembers the exact page you left on, even if you close the browser mid-chapter
- Add notes anchored to specific pages
- Summarize any page range or an entire book using AI

**Chat:**
- Ask Helix anything — "what should I work on today?", "summarize where I left off in this book"
- Answers are grounded in your live project and reading data, not generic advice

---

## Project structure

```
helix/
├── agent/                  # Core agent logic
│   ├── graph.py            # LangGraph pipeline
│   ├── autonomous.py       # Tool-gathering reasoning loop
│   ├── analysis.py         # LLM project analysis
│   ├── task_extractor.py   # Converts analysis → structured tasks
│   ├── task_persister.py   # Saves/updates tasks in DB
│   ├── progress_evaluator.py # Snapshots + diffs project state
│   ├── portfolio_summary.py  # Cross-project priority ranking
│   ├── book_service.py     # PDF reading, notes, summarization
│   ├── memory.py           # Per-project persistent memory
│   ├── config.py           # Centralized settings (pydantic-settings)
│   ├── llm_provider.py     # LLM factory + retry logic
│   ├── ignore.py           # Filters venv, pycache, etc.
│   └── logging_config.py   # Structured logging setup
│
├── db/
│   ├── database.py         # SQLAlchemy engine + session (single source)
│   ├── models.py           # Project, Task
│   ├── book_models.py      # Book, BookNote, BookSummary
│   ├── snapshot_models.py  # ProjectSnapshot (progress history)
│   ├── memory_models.py    # AgentMemory
│   └── init_db.py          # Creates all tables
│
├── backend/
│   └── api.py              # FastAPI — all REST endpoints
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx         # Main UI — dashboard, projects, books, chat
│   │   ├── PdfReader.jsx   # In-app PDF reader with page sync
│   │   └── main.jsx        # React entry point
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
│
├── helix_cli.py            # Terminal CLI (run, status, tasks, chat, done)
├── start.sh                # Launch everything + open browser
├── stop.sh                 # Kill everything cleanly
├── update.sh               # Rebuild frontend + restart
├── reset_and_seed.py       # Wipe DB and seed fresh project data
└── .env                    # API keys (never commit this)
```

---

## Setup

### Requirements

- Python 3.11+
- Node.js 18+
- A virtual environment

### 1. Clone and create venv

```bash
git clone https://github.com/your-username/helix
cd helix
python -m venv venv
source venv/bin/activate
```

### 2. Install Python dependencies

```bash
pip install fastapi uvicorn sqlalchemy pydantic-settings langchain-anthropic langchain-openai langgraph pypdf python-multipart tenacity pathspec rich
```

```bash
pip install -r requirements.txt
```

### 3. Configure environment

Create a `.env` file in the project root:

```env
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Optional overrides (defaults shown)
ANTHROPIC_MODEL=claude-haiku-4-5-20251001
OPENAI_MODEL=gpt-4o-mini
ANALYSIS_PROVIDER=anthropic
PLANNER_PROVIDER=openai
LOG_LEVEL=INFO
AGENT_MAX_STEPS=10
```

### 4. Initialize the database

```bash
python -m db.init_db
```

### 5. Seed your first project

Edit `reset_and_seed.py` — update `project_path` to point to your project, then:

```bash
python reset_and_seed.py
```

### 6. Build the frontend

```bash
cd frontend
npm install
npm run build
cd ..
```

### 7. Install as a desktop app (Linux)

```bash
chmod +x start.sh stop.sh update.sh

# Edit helix.desktop — update the Exec and Icon paths to match your system
cp helix.desktop ~/.local/share/applications/
update-desktop-database ~/.local/share/applications/
```

Now Helix appears in your app launcher. Double-click to open.

---

## Running Helix

### Double-click (recommended)
Click the Helix icon in your app launcher. Done.

### Terminal
```bash
./start.sh      # start everything + open browser
./stop.sh       # stop everything
```

### CLI (without the UI)
```bash
source venv/bin/activate

python helix_cli.py run                # analyze all projects, concise output
python helix_cli.py status             # project progress table
python helix_cli.py tasks              # all open tasks
python helix_cli.py tasks --project 1  # tasks for a specific project
python helix_cli.py done <task_key>    # mark a task complete
python helix_cli.py chat               # interactive mode
```

---

## Updating Helix

| What changed | Command |
|---|---|
| Frontend (React/JSX) | `./update.sh` |
| Backend (Python) | Nothing — auto-reloads while running |
| Both | `./update.sh` |
| New pip/npm package | `./update.sh --deps` |
| Backend restart only | `./update.sh --be` |

---

## Adding a project

Open `reset_and_seed.py` and add an entry to the `projects` list:

```python
Project(
    name="My App",
    github_repo="https://github.com/you/my-app",
    description="What this project does",
    goals="improve test coverage,reduce technical debt,add CI/CD",
    project_path="/absolute/path/to/my-app",
    status="In Progress",
),
```

Then run:
```bash
python reset_and_seed.py
```

> **Note:** `reset_and_seed.py` wipes the database before seeding. To add a project without losing existing data, insert it directly via the Python shell or add an `add_project.py` script.

---

## Adding a book

**Via the UI:** Open Helix → click `+ Add Book` in the sidebar → drag and drop a PDF.

**Via the CLI:**
```bash
python helix_cli.py chat
# then ask: "add a book at /path/to/book.pdf"
```

**Via the API directly:**
```bash
curl -X POST http://localhost:8000/api/books \
  -H "Content-Type: application/json" \
  -d '{"title": "Deep Work", "author": "Cal Newport", "file_path": "/home/you/books/deep-work.pdf"}'
```

---

## How the pipeline works

Each time you run an analysis, Helix does this for every project:

```
1. autonomous_reasoner   — gathers filesystem, code, and architecture data
                           skips tools already in memory from last run
2. snapshot              — measures current state, diffs against last run
                           auto-completes tasks whose metric improved
3. analysis              — LLM reviews the data and delta, produces focused output
4. task extraction       — converts analysis into P0/P1/P2 tasks
5. task persistence      — upserts tasks to DB, preserves completed/dismissed status
```

After all projects complete:
```
6. portfolio summary     — ranks projects by urgency, generates sprint focus
7. reflection            — reviews the full portfolio and refines the plan
```

Memory is namespaced per project so multiple projects never overwrite each other.

---

## Architecture decisions

**Why LangGraph?** The pipeline has clear state transitions and conditional logic (skip tools already in memory, stop when all tools gathered). LangGraph makes this explicit and debuggable.

**Why SQLite?** Zero setup, file-based, works on any machine. Easy to inspect with any SQLite viewer. Can be swapped for PostgreSQL by changing `DATABASE_URL` in `db/database.py`.

**Why a single `Base` in `db/database.py`?** All models import from one place so `Base.metadata.create_all()` always knows about every table. Having multiple `Base` objects was an early bug that caused tables to silently not be created.

**Why per-project memory keys?** Each project's tool results are stored under `project_{id}_run_summary`. Without namespacing, running two projects in sequence would cause the second to overwrite the first's memory.

**Why cache LLM summaries in `book_summaries`?** Summarizing 300 pages is expensive. Caching by `(book_id, page_start, page_end)` means re-opening a book and requesting the same summary is instant.

---

## Logs

All logs are written to `.logs/` in the project root:

```
.logs/
├── backend.log     # FastAPI / uvicorn output
├── frontend.log    # Vite or Python HTTP server output
└── helix.pids      # PIDs of running processes (used by stop.sh)
```

To follow backend logs live:
```bash
tail -f .logs/backend.log
```

---

## Roadmap

- [ ] Git history analysis tool (detect recent changes, commit frequency)
- [ ] Test coverage detection (parse pytest-cov output)
- [ ] Dependency vulnerability scanning
- [ ] Project path picker in the UI
- [ ] Multi-user support
- [ ] Tauri desktop app (no browser required)
- [ ] Project Gutenberg / Open Library book search

---
