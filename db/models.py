from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    github_repo: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    goals: Mapped[str] = mapped_column(Text)
    project_path: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="Not Started")
    progress_score: Mapped[float] = mapped_column(Float, default=0.0)
    last_checked: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
    )

    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="project", cascade="all, delete-orphan"
    )


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id"), nullable=False
    )

    # Short identifier e.g. "setup_pytest_framework"
    task_key: Mapped[str] = mapped_column(String, nullable=False)

    description: Mapped[str] = mapped_column(Text, nullable=False)

    priority: Mapped[str] = mapped_column(String, default="P2")  # P0 / P1 / P2

    estimated_hours: Mapped[float] = mapped_column(Float, default=0.0)

    # open | in_progress | completed | dismissed
    status: Mapped[str] = mapped_column(String, default="open")

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    project: Mapped["Project"] = relationship("Project", back_populates="tasks")

    def __repr__(self) -> str:
        return f"<Task {self.task_key} [{self.priority}] {self.status}>"
