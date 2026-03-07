"""
progress_evaluator.py
---------------------
Compares the current project state against the previous snapshot to:

1. Generate a human-readable delta report  ("tests: 0 → 5", etc.)
2. Auto-complete tasks whose success condition is now measurably met
3. Compute an updated progress_score for the project
4. Persist a new ProjectSnapshot to DB

This runs BEFORE analysis so the LLM gets real delta context, not just
a static snapshot of the current state.
"""

from datetime import datetime, timezone
from typing import Any

from db.database import SessionLocal
from db.models import Project, Task
from db.snapshot_models import ProjectSnapshot

# Metric definitions
# Each entry maps a snapshot field to:
#   - label:      human-readable name
#   - task_hints: substrings — if a task_key contains any of these AND the
#                 metric improved, the task is auto-completed
METRIC_DEFINITIONS = [
    {
        "field": "test_files",
        "label": "Test files",
        "task_hints": ["test", "pytest", "coverage"],
    },
    {
        "field": "total_functions",
        "label": "Functions",
        "task_hints": [],  # generic metric, no auto-complete
    },
    {
        "field": "total_classes",
        "label": "Classes",
        "task_hints": [],
    },
    {
        "field": "total_files",
        "label": "Total files",
        "task_hints": [],
    },
    {
        "field": "has_cli",
        "label": "CLI present",
        "task_hints": ["cli", "main", "entrypoint"],
    },
]


# Core public function


def evaluate_and_snapshot(
    project_id: int,
    current_metrics: dict[str, Any],
) -> dict[str, Any]:
    """
    Main entry point called from graph.py snapshot_node.

    Parameters
    ----------
    project_id      : DB id of the project
    current_metrics : dict built from tool outputs, expected keys:
                        filesystem → {files, tests, has_cli}
                        code       → {total_functions, total_classes}
                        tasks      → computed from DB (injected by graph)

    Returns a result dict:
        delta_lines   : list[str]   — one line per changed metric
        delta_summary : str         — joined delta_lines
        auto_completed: list[str]   — task_keys that were auto-completed
        progress_score: float       — new 0.0–1.0 score
        snapshot_id   : int         — newly created snapshot PK
    """
    session = SessionLocal()
    result: dict[str, Any] = {
        "delta_lines": [],
        "delta_summary": "",
        "auto_completed": [],
        "progress_score": 0.0,
        "snapshot_id": None,
    }

    try:
        # ── Build current snapshot values ─────────────────────────────────
        fs = current_metrics.get("filesystem", {})
        code = current_metrics.get("code", {})
        task_counts = current_metrics.get("task_counts", {})

        current = {
            "total_files": int(fs.get("files", 0)),
            "test_files": int(fs.get("tests", 0)),
            "has_cli": int(bool(fs.get("has_cli", False))),
            "total_functions": int(code.get("total_functions", 0)),
            "total_classes": int(code.get("total_classes", 0)),
            "open_tasks": int(task_counts.get("open", 0)),
            "completed_tasks": int(task_counts.get("completed", 0)),
        }

        # Load previous snapshot
        previous = (
            session.query(ProjectSnapshot)
            .filter_by(project_id=project_id)
            .order_by(ProjectSnapshot.created_at.desc())
            .first()
        )

        # Diff
        delta_lines: list[str] = []
        improved_fields: set[str] = set()

        if previous is None:
            delta_lines.append("First run — baseline snapshot recorded.")
        else:
            for metric in METRIC_DEFINITIONS:
                field = metric["field"]
                label = metric["label"]
                prev_val = getattr(previous, field, 0)
                curr_val = current[field]

                if curr_val != prev_val:
                    direction = "↑" if curr_val > prev_val else "↓"
                    delta_lines.append(f"{label}: {prev_val} → {curr_val} {direction}")
                    if curr_val > prev_val:
                        improved_fields.add(field)

            # Tasks completed since last run
            prev_completed = previous.completed_tasks
            curr_completed = current["completed_tasks"]
            if curr_completed > prev_completed:
                delta_lines.append(
                    f"Tasks completed: {prev_completed} → {curr_completed} ↑"
                )

            if not delta_lines:
                delta_lines.append("No measurable changes since last run.")

        # Auto-complete tasks whose metric improved
        auto_completed: list[str] = []

        if improved_fields:
            open_tasks = (
                session.query(Task)
                .filter_by(project_id=project_id, status="open")
                .all()
            )
            for task in open_tasks:
                for metric in METRIC_DEFINITIONS:
                    if metric["field"] not in improved_fields:
                        continue
                    for hint in metric["task_hints"]:
                        if hint in task.task_key.lower():
                            task.status = "completed"
                            task.updated_at = datetime.now(timezone.utc)
                            auto_completed.append(task.task_key)
                            break

        # Compute progress score
        total_tasks = current["open_tasks"] + current["completed_tasks"]
        progress_score = (
            current["completed_tasks"] / total_tasks if total_tasks > 0 else 0.0
        )

        # Bonus: bump score if tests exist
        if current["test_files"] > 0:
            progress_score = min(1.0, progress_score + 0.05)

        # Persist new snapshot
        delta_summary = "\n".join(delta_lines)

        snapshot = ProjectSnapshot(
            project_id=project_id,
            total_files=current["total_files"],
            test_files=current["test_files"],
            has_cli=current["has_cli"],
            total_functions=current["total_functions"],
            total_classes=current["total_classes"],
            open_tasks=current["open_tasks"],
            completed_tasks=current["completed_tasks"],
            progress_score=progress_score,
            delta_summary=delta_summary,
        )
        session.add(snapshot)

        # Update Project.progress_score
        project = session.get(Project, project_id)
        if project:
            project.progress_score = progress_score
            project.last_checked = datetime.now(timezone.utc)

        session.commit()

        result["delta_lines"] = delta_lines
        result["delta_summary"] = delta_summary
        result["auto_completed"] = auto_completed
        result["progress_score"] = progress_score
        result["snapshot_id"] = snapshot.id

    except Exception as e:
        session.rollback()
        raise RuntimeError(f"Snapshot failed: {e}") from e
    finally:
        session.close()

    return result


# Helper: load last two snapshots for a project (useful for reporting)


def get_snapshot_history(project_id: int, limit: int = 5) -> list[dict]:
    session = SessionLocal()
    try:
        snapshots = (
            session.query(ProjectSnapshot)
            .filter_by(project_id=project_id)
            .order_by(ProjectSnapshot.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": s.id,
                "created_at": s.created_at.isoformat(),
                "total_files": s.total_files,
                "test_files": s.test_files,
                "total_functions": s.total_functions,
                "total_classes": s.total_classes,
                "open_tasks": s.open_tasks,
                "completed_tasks": s.completed_tasks,
                "progress_score": round(s.progress_score, 3),
                "delta_summary": s.delta_summary,
            }
            for s in snapshots
        ]
    finally:
        session.close()
