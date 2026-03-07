from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    title: Mapped[str] = mapped_column(String, nullable=False)
    author: Mapped[str] = mapped_column(String, default="Unknown")
    file_path: Mapped[str] = mapped_column(String, nullable=False)

    current_page: Mapped[int] = mapped_column(Integer, default=1)
    total_pages: Mapped[int] = mapped_column(Integer, default=0)

    # 0.0 – 1.0
    progress: Mapped[float] = mapped_column(Float, default=0.0)

    started_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    last_read_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    notes: Mapped[list["BookNote"]] = relationship(
        "BookNote", back_populates="book", cascade="all, delete-orphan"
    )
    summaries: Mapped[list["BookSummary"]] = relationship(
        "BookSummary", back_populates="book", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Book {self.title!r} page={self.current_page}/{self.total_pages}>"


class BookNote(Base):
    __tablename__ = "book_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    book_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("books.id"), nullable=False
    )
    page_number: Mapped[int] = mapped_column(Integer, default=1)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    book: Mapped["Book"] = relationship("Book", back_populates="notes")


class BookSummary(Base):
    __tablename__ = "book_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    book_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("books.id"), nullable=False
    )

    # e.g. "Chapter 1", "Full Book", "Pages 10-30"
    chapter_title: Mapped[str] = mapped_column(String, default="")
    page_start: Mapped[int] = mapped_column(Integer, default=1)
    page_end: Mapped[int] = mapped_column(Integer, default=1)
    summary: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    book: Mapped["Book"] = relationship("Book", back_populates="summaries")
