from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base

if TYPE_CHECKING:
    from db.models import Project


class ProjectSnapshot(Base):
    """
    A point-in-time measurement of a project taken at the start of each run.
    Comparing two consecutive snapshots gives Helix concrete progress data.
    """

    __tablename__ = "project_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id"), nullable=False
    )

    # Filesystem metrics
    total_files: Mapped[int] = mapped_column(Integer, default=0)
    test_files: Mapped[int] = mapped_column(Integer, default=0)
    has_cli: Mapped[int] = mapped_column(Integer, default=0)  # 0/1 bool

    # Code metrics
    total_functions: Mapped[int] = mapped_column(Integer, default=0)
    total_classes: Mapped[int] = mapped_column(Integer, default=0)

    # Task metrics (captured at snapshot time)
    open_tasks: Mapped[int] = mapped_column(Integer, default=0)
    completed_tasks: Mapped[int] = mapped_column(Integer, default=0)

    # Derived score (0.0 – 1.0)
    progress_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Human-readable diff vs previous snapshot
    delta_summary: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
    )

    project: Mapped["Project"] = relationship("Project")
