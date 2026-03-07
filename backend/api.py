"""
api.py
------
Run from the helix/ root:
    uvicorn backend.api:app --reload --port 8000

Or move this file to helix/ root and run:
    uvicorn api:app --reload --port 8000
"""

import sys
from pathlib import Path

from fastapi.responses import FileResponse

# Make agent/ and db/ importable when api.py lives in backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import shutil
import uuid
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent.book_service import (
    add_note,
    delete_note,
    get_book,
    list_books,
    register_book,
    summarize_full_book,
    summarize_range,
    update_page,
)
from agent.llm_provider import get_llm, invoke_with_retry
from db.database import SessionLocal
from db.models import Project, Task

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="Helix", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads" / "books"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class UpdatePageRequest(BaseModel):
    page: int


class AddNoteRequest(BaseModel):
    page: int
    content: str


class SummarizeRangeRequest(BaseModel):
    page_start: int
    page_end: int
    chapter_title: Optional[str] = ""


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


class RegisterBookRequest(BaseModel):
    title: str
    author: str = "Unknown"
    file_path: str


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


@app.get("/api/projects")
def get_projects():
    session = SessionLocal()
    try:
        projects = session.query(Project).all()
        result = []
        for p in projects:
            open_t = (
                session.query(Task).filter_by(project_id=p.id, status="open").count()
            )
            done_t = (
                session.query(Task)
                .filter_by(project_id=p.id, status="completed")
                .count()
            )
            p0 = (
                session.query(Task)
                .filter_by(project_id=p.id, priority="P0", status="open")
                .count()
            )
            result.append(
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "goals": p.goals,
                    "status": p.status,
                    "progress_score": round(p.progress_score or 0.0, 3),
                    "open_tasks": open_t,
                    "completed_tasks": done_t,
                    "p0_tasks": p0,
                    "last_checked": p.last_checked.isoformat()
                    if p.last_checked
                    else None,
                }
            )
        return result
    finally:
        session.close()


@app.get("/api/projects/{project_id}/tasks")
def get_project_tasks(project_id: int, status: Optional[str] = None):
    session = SessionLocal()
    try:
        q = session.query(Task).filter_by(project_id=project_id)
        if status:
            q = q.filter_by(status=status)
        tasks = q.order_by(Task.priority, Task.created_at).all()
        return [
            {
                "id": t.id,
                "task_key": t.task_key,
                "description": t.description,
                "priority": t.priority,
                "status": t.status,
                "estimated_hours": t.estimated_hours,
                "created_at": t.created_at.isoformat(),
            }
            for t in tasks
        ]
    finally:
        session.close()


@app.put("/api/tasks/{task_id}/status")
def update_task_status(task_id: int, body: dict):
    session = SessionLocal()
    try:
        task = session.get(Task, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        task.status = body.get("status", task.status)
        session.commit()
        return {"ok": True}
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Books
# ---------------------------------------------------------------------------


@app.get("/api/books")
def get_books():
    return list_books()


@app.post("/api/books")
def create_book(req: RegisterBookRequest):
    if not Path(req.file_path).exists():
        raise HTTPException(status_code=400, detail="File not found at given path")
    book = register_book(req.title, req.author, req.file_path)
    return {"id": book.id, "title": book.title, "total_pages": book.total_pages}


@app.post("/api/books/upload")
async def upload_book(
    file: UploadFile = File(...),
    title: str = "",
    author: str = "Unknown",
):
    if not file.filename or not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    dest = UPLOAD_DIR / safe_name

    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    inferred_title = (
        title or Path(file.filename).stem.replace("-", " ").replace("_", " ").title()
    )
    book = register_book(inferred_title, author, str(dest))
    return {"id": book.id, "title": book.title, "total_pages": book.total_pages}


@app.get("/api/books/{book_id}")
def get_book_detail(book_id: int):
    book = get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@app.put("/api/books/{book_id}/page")
def set_page(book_id: int, req: UpdatePageRequest):
    try:
        return update_page(book_id, req.page)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/books/{book_id}/notes")
def create_note(book_id: int, req: AddNoteRequest):
    try:
        return add_note(book_id, req.page, req.content)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/api/notes/{note_id}")
def remove_note(note_id: int):
    if not delete_note(note_id):
        raise HTTPException(status_code=404, detail="Note not found")
    return {"ok": True}


@app.post("/api/books/{book_id}/summarize")
def summarize_section(book_id: int, req: SummarizeRangeRequest):
    try:
        return summarize_range(
            book_id, req.page_start, req.page_end, req.chapter_title or ""
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/books/{book_id}/summarize/full")
def summarize_book(book_id: int):
    try:
        return summarize_full_book(book_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ---------------------------------------------------------------------------
# PDF file serving
# ---------------------------------------------------------------------------


@app.get("/api/books/{book_id}/file")
def serve_book_file(book_id: int):
    """Serve the raw PDF so pdfjs can render it in-browser."""
    from db.book_models import Book as BookModel

    session = SessionLocal()
    try:
        book = session.get(BookModel, book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        path = Path(book.file_path)
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {path}")
        return FileResponse(str(path), media_type="application/pdf")
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


@app.post("/api/chat")
def chat(req: ChatRequest):
    session = SessionLocal()
    try:
        projects = session.query(Project).all()
        books = list_books()

        context = "Current state:\n\nPROJECTS:\n"
        for p in projects:
            open_t = (
                session.query(Task).filter_by(project_id=p.id, status="open").count()
            )
            p0 = (
                session.query(Task)
                .filter_by(project_id=p.id, priority="P0", status="open")
                .count()
            )
            context += (
                f"  • {p.name}: {(p.progress_score or 0):.0%} done, "
                f"{open_t} open tasks, {p0} P0\n"
            )

        context += "\nBOOKS:\n"
        for b in books:
            context += (
                f"  • {b['title']} by {b.get('author', '?')}: "
                f"page {b['current_page']}/{b['total_pages']} "
                f"({b['progress']:.0%})\n"
            )
    finally:
        session.close()

    history_text = "\n".join(
        f"{'User' if m['role'] == 'user' else 'Helix'}: {m['content']}"
        for m in req.history[-6:]
    )

    prompt = (
        "You are Helix, a personal engineering and reading assistant.\n"
        "Answer in max 6 lines. Be direct and specific.\n\n"
        f"{context}\n\n"
        f"Conversation:\n{history_text}\n"
        f"User: {req.message}\n\nHelix:"
    )

    llm = get_llm("analysis")
    response = invoke_with_retry(llm, prompt)
    return {"response": response.strip()}


# ---------------------------------------------------------------------------
# Run pipeline
# ---------------------------------------------------------------------------


@app.post("/api/run")
def trigger_run():
    from agent.graph import build_graph
    from agent.state import AgentState

    state: AgentState = {
        "user_goal": "analyze all projects",
        "projects": [],
        "updates": [],
    }

    agent = build_graph()
    result = agent.invoke(state)

    project_results = result.get("project_results", [])
    return {
        "ok": True,
        "projects_analyzed": len(project_results),
        "summaries": [
            {
                "project": r["project_name"],
                "progress": r["progress_score"],
                "delta": r["delta_summary"],
                "auto_completed": r["auto_completed"],
                "task_count": len(r["tasks"]),
            }
            for r in project_results
        ],
        "portfolio": result.get("portfolio_summary", ""),
    }
