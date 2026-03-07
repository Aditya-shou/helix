"""
task_persister.py
-----------------
Responsible for writing generated tasks into the database.

Design decisions:
- Upsert by (project_id, task_key): if the task already exists
  and is still "open", we leave it untouched so status history
  is preserved across runs.
- If the task exists but was "dismissed" or "completed", we skip it —
  Helix won't re-open work the user already resolved.
- New tasks are always inserted as "open".
"""

from datetime import datetime, timezone
from typing import Any

from db.database import SessionLocal
from db.models import Task


def persist_tasks(project_id: int, tasks: list[dict[str, Any]]) -> dict[str, int]:
    """
    Write a list of task dicts to the database for the given project.

    Each task dict is expected to have:
        task        – short identifier string  (maps to task_key)
        description – human-readable detail
        priority    – "P0" | "P1" | "P2"
        estimated_hours – numeric

    Returns a summary dict: {"inserted": n, "skipped": n}
    """
    session = SessionLocal()
    inserted = 0
    skipped = 0

    try:
        for raw in tasks:
            task_key = raw.get("task", "unknown")
            description = raw.get("description", "")
            priority = raw.get("priority", "P2")
            estimated_hours = float(raw.get("estimated_hours", 0))

            existing = (
                session.query(Task)
                .filter_by(project_id=project_id, task_key=task_key)
                .first()
            )

            if existing:
                # Preserve completed / dismissed decisions
                if existing.status in ("completed", "dismissed"):
                    skipped += 1
                    continue

                # Task already open — update description/priority in case
                # the analysis refined them, but keep status as-is
                existing.description = description
                existing.priority = priority
                existing.estimated_hours = estimated_hours
                existing.updated_at = datetime.now(timezone.utc)
                skipped += 1  # not a net-new row

            else:
                session.add(
                    Task(
                        project_id=project_id,
                        task_key=task_key,
                        description=description,
                        priority=priority,
                        estimated_hours=estimated_hours,
                        status="open",
                    )
                )
                inserted += 1

        session.commit()

    except Exception as e:
        session.rollback()
        raise RuntimeError(f"Failed to persist tasks: {e}") from e

    finally:
        session.close()

    return {"inserted": inserted, "skipped": skipped}


def load_open_tasks(project_id: int) -> list[Task]:
    """Return all open tasks for a project, ordered by priority."""
    priority_order = {"P0": 0, "P1": 1, "P2": 2}
    session = SessionLocal()
    try:
        tasks = (
            session.query(Task).filter_by(project_id=project_id, status="open").all()
        )
        return sorted(tasks, key=lambda t: priority_order.get(t.priority, 9))
    finally:
        session.close()


def mark_task_complete(project_id: int, task_key: str) -> bool:
    """Mark a specific task as completed. Returns True if found."""
    session = SessionLocal()
    try:
        task = (
            session.query(Task)
            .filter_by(project_id=project_id, task_key=task_key)
            .first()
        )
        if not task:
            return False
        task.status = "completed"
        task.updated_at = datetime.now(timezone.utc)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        raise RuntimeError(f"Failed to mark task complete: {e}") from e
    finally:
        session.close()
