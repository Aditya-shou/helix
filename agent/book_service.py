"""
book_service.py

All book-related business logic:
- PDF text extraction per page range
- Page progress tracking
- LLM summarization (chapter or full book)
- Note management
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

import pypdf

from agent.llm_provider import get_llm, invoke_with_retry
from db.book_models import Book, BookNote, BookSummary
from db.database import SessionLocal

logger = logging.getLogger(__name__)


# To get details of the pdf


def extract_text(file_path: str, page_start: int, page_end: int) -> str:
    """
    Extract raw text from a PDF between page_start and page_end (1-indexed).
    Returns empty string on failure rather than raising.
    """
    try:
        reader = pypdf.PdfReader(file_path)
        total = len(reader.pages)
        start = max(0, page_start - 1)
        end = min(total, page_end)
        chunks = []
        for i in range(start, end):
            text = reader.pages[i].extract_text() or ""
            chunks.append(text)
        return "\n".join(chunks)
    except Exception as e:
        logger.error("PDF extraction failed for %s: %s", file_path, e)
        return ""


def get_total_pages(file_path: str) -> int:
    try:
        reader = pypdf.PdfReader(file_path)
        return len(reader.pages)
    except Exception as e:
        logger.error("Could not read PDF %s: %s", file_path, e)
        return 0


# CRUD operation for updating books details


def register_book(title: str, author: str, file_path: str) -> Book:
    """Add a new book to the DB and detect its page count."""
    session = SessionLocal()
    try:
        total = get_total_pages(file_path)
        book = Book(
            title=title,
            author=author,
            file_path=file_path,
            total_pages=total,
            current_page=1,
            progress=0.0,
        )
        session.add(book)
        session.commit()
        session.refresh(book)
        logger.info("Registered book '%s' (%d pages)", title, total)
        return book
    finally:
        session.close()


def update_page(book_id: int, page: int) -> dict:
    """Update reading position and recalculate progress."""
    session = SessionLocal()
    try:
        book = session.get(Book, book_id)
        if not book:
            raise ValueError(f"Book {book_id} not found")

        book.current_page = max(1, min(page, book.total_pages or page))
        book.progress = (
            book.current_page / book.total_pages if book.total_pages > 0 else 0.0
        )
        book.last_read_at = datetime.now(timezone.utc)
        session.commit()

        return {
            "book_id": book.id,
            "current_page": book.current_page,
            "total_pages": book.total_pages,
            "progress": round(book.progress, 3),
        }
    finally:
        session.close()


def list_books() -> list[dict]:
    session = SessionLocal()
    try:
        books = session.query(Book).order_by(Book.last_read_at.desc()).all()
        return [
            {
                "id": b.id,
                "title": b.title,
                "author": b.author,
                "current_page": b.current_page,
                "total_pages": b.total_pages,
                "progress": round(b.progress, 3),
                "last_read_at": b.last_read_at.isoformat(),
            }
            for b in books
        ]
    finally:
        session.close()


def get_book(book_id: int) -> dict | None:
    session = SessionLocal()
    try:
        book = session.get(Book, book_id)
        if not book:
            return None
        notes = [
            {
                "id": n.id,
                "page": n.page_number,
                "content": n.content,
                "created_at": n.created_at.isoformat(),
            }
            for n in sorted(book.notes, key=lambda n: n.page_number)
        ]
        summaries = [
            {
                "id": s.id,
                "chapter": s.chapter_title,
                "page_start": s.page_start,
                "page_end": s.page_end,
                "summary": s.summary,
                "created_at": s.created_at.isoformat(),
            }
            for s in sorted(book.summaries, key=lambda s: s.page_start)
        ]
        return {
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "file_path": book.file_path,
            "current_page": book.current_page,
            "total_pages": book.total_pages,
            "progress": round(book.progress, 3),
            "started_at": book.started_at.isoformat(),
            "last_read_at": book.last_read_at.isoformat(),
            "notes": notes,
            "summaries": summaries,
        }
    finally:
        session.close()


# Notes


def add_note(book_id: int, page: int, content: str) -> dict:
    session = SessionLocal()
    try:
        book = session.get(Book, book_id)
        if not book:
            raise ValueError(f"Book {book_id} not found")
        note = BookNote(book_id=book_id, page_number=page, content=content)
        session.add(note)
        session.commit()
        session.refresh(note)
        return {
            "id": note.id,
            "book_id": book_id,
            "page": note.page_number,
            "content": note.content,
            "created_at": note.created_at.isoformat(),
        }
    finally:
        session.close()


def delete_note(note_id: int) -> bool:
    session = SessionLocal()
    try:
        note = session.get(BookNote, note_id)
        if not note:
            return False
        session.delete(note)
        session.commit()
        return True
    finally:
        session.close()


def summarize_range(
    book_id: int,
    page_start: int,
    page_end: int,
    chapter_title: str = "",
) -> dict:
    """
    Extract text from a page range and ask the LLM to summarize it.
    Caches the result in book_summaries so repeated calls don't re-run the LLM.
    """
    session = SessionLocal()
    try:
        book = session.get(Book, book_id)
        if not book:
            raise ValueError(f"Book {book_id} not found")

        existing = (
            session.query(BookSummary)
            .filter_by(book_id=book_id, page_start=page_start, page_end=page_end)
            .first()
        )
        if existing:
            logger.info(
                "Returning cached summary for pages %d-%d", page_start, page_end
            )
            return {
                "book_id": book_id,
                "chapter_title": existing.chapter_title,
                "page_start": existing.page_start,
                "page_end": existing.page_end,
                "summary": existing.summary,
                "cached": True,
            }

        text = extract_text(book.file_path, page_start, page_end)
        if not text.strip():
            raise ValueError(f"No text extracted from pages {page_start}-{page_end}")

        # Trim to ~12k chars to stay within token limits
        text = text[:12000]

        label = chapter_title or f"Pages {page_start}–{page_end}"
        prompt = (
            f"You are summarizing '{book.title}' by {book.author}.\n\n"
            f"Section: {label}\n\n"
            f"Text:\n{text}\n\n"
            "Write a clear, concise summary (8-12 sentences). Cover:\n"
            "- Main ideas and arguments\n"
            "- Key characters or concepts introduced\n"
            "- Important quotes or moments (paraphrased)\n"
            "- How this section connects to the broader work\n"
        )

        llm = get_llm("analysis")
        summary_text = invoke_with_retry(llm, prompt)

        summary = BookSummary(
            book_id=book_id,
            chapter_title=label,
            page_start=page_start,
            page_end=page_end,
            summary=summary_text,
        )
        session.add(summary)
        session.commit()
        session.refresh(summary)

        return {
            "book_id": book_id,
            "chapter_title": label,
            "page_start": page_start,
            "page_end": page_end,
            "summary": summary_text,
            "cached": False,
        }
    finally:
        session.close()


def summarize_full_book(book_id: int) -> dict:
    """
    Summarize the entire book by chunking it into 50-page sections,
    summarizing each, then asking the LLM for a final synthesis.
    """
    session = SessionLocal()
    book = session.get(Book, book_id)
    if not book:
        session.close()
        raise ValueError(f"Book {book_id} not found")

    total = book.total_pages
    title = book.title
    author = book.author
    file_path = book.file_path
    session.close()

    CHUNK = 50
    chunk_summaries: list[str] = []

    for start in range(1, total + 1, CHUNK):
        end = min(start + CHUNK - 1, total)
        result = summarize_range(book_id, start, end, f"Pages {start}–{end}")
        chunk_summaries.append(f"[Pages {start}–{end}]\n{result['summary']}")
        logger.info("Summarized pages %d-%d of %d", start, end, total)

    combined = "\n\n".join(chunk_summaries)[:15000]
    prompt = (
        f"You have section-by-section summaries of '{title}' by {author}.\n\n"
        f"{combined}\n\n"
        "Write a comprehensive book summary (15-20 sentences) covering:\n"
        "- Central thesis or narrative arc\n"
        "- Major themes\n"
        "- Key characters or ideas\n"
        "- Most important takeaways\n"
    )

    llm = get_llm("analysis")
    full_summary = invoke_with_retry(llm, prompt)

    # Store as a special full-book summary entry
    session = SessionLocal()
    try:
        existing = (
            session.query(BookSummary)
            .filter_by(
                book_id=book_id, page_start=1, page_end=total, chapter_title="Full Book"
            )
            .first()
        )
        if existing:
            existing.summary = full_summary
        else:
            session.add(
                BookSummary(
                    book_id=book_id,
                    chapter_title="Full Book",
                    page_start=1,
                    page_end=total,
                    summary=full_summary,
                )
            )
        session.commit()
    finally:
        session.close()

    return {
        "book_id": book_id,
        "chapter_title": "Full Book",
        "summary": full_summary,
        "sections_processed": len(chunk_summaries),
    }
