"""
portfolio_summary.py
--------------------
After all projects have been analyzed, this module produces a
cross-project priority view — answering the question:

    "Across all my projects, what should I work on first?"

It ranks by:
  1. P0 task count (highest urgency)
  2. Progress score (lowest progress = needs most attention)
  3. Project age (older last_checked = more stale)
"""

import logging
from dataclasses import dataclass, field

from agent.llm_provider import get_llm, invoke_with_retry
from db.database import SessionLocal
from db.models import Project, Task

logger = logging.getLogger(__name__)


@dataclass
class ProjectSummary:
    project_id: int
    name: str
    progress_score: float
    open_tasks: int
    p0_tasks: int
    p1_tasks: int
    p2_tasks: int
    top_tasks: list[str] = field(default_factory=list)


def _load_project_summaries(project_ids: list[int]) -> list[ProjectSummary]:
    session = SessionLocal()
    summaries: list[ProjectSummary] = []

    try:
        for pid in project_ids:
            project = session.get(Project, pid)
            if not project:
                continue

            open_tasks = (
                session.query(Task).filter_by(project_id=pid, status="open").all()
            )

            p0 = [t for t in open_tasks if t.priority == "P0"]
            p1 = [t for t in open_tasks if t.priority == "P1"]
            p2 = [t for t in open_tasks if t.priority == "P2"]

            # Top 3 most urgent task descriptions for the LLM context
            top = [t.task_key for t in (p0 + p1)[:3]]

            summaries.append(
                ProjectSummary(
                    project_id=pid,
                    name=project.name,
                    progress_score=project.progress_score,
                    open_tasks=len(open_tasks),
                    p0_tasks=len(p0),
                    p1_tasks=len(p1),
                    p2_tasks=len(p2),
                    top_tasks=top,
                )
            )
    finally:
        session.close()

    return summaries


def _rank_projects(summaries: list[ProjectSummary]) -> list[ProjectSummary]:
    """
    Sort projects by urgency:
      primary   → P0 task count descending
      secondary → progress score ascending (least done first)
    """
    return sorted(
        summaries,
        key=lambda s: (-s.p0_tasks, s.progress_score),
    )


def build_portfolio_summary(project_ids: list[int]) -> str:
    """
    Build a ranked, LLM-refined cross-project priority summary.
    Returns a human-readable string appended to state updates.
    """
    summaries = _load_project_summaries(project_ids)

    if not summaries:
        return "No projects to summarize."

    ranked = _rank_projects(summaries)

    # ── Build structured text for the LLM ────────────────────────────────
    projects_text = ""
    for i, s in enumerate(ranked, 1):
        projects_text += (
            f"\n{i}. {s.name}"
            f"\n   Progress: {s.progress_score:.0%}"
            f"\n   Open tasks: {s.open_tasks} (P0={s.p0_tasks}, P1={s.p1_tasks}, P2={s.p2_tasks})"
            f"\n   Top priorities: {', '.join(s.top_tasks) if s.top_tasks else 'none'}\n"
        )

    prompt = f"""
You are Helix, a senior engineering manager overseeing multiple projects.

Here is the current state of all projects, ranked by urgency:
{projects_text}

Your job:
1. Identify which project needs immediate attention and why.
2. Call out any projects that are dangerously behind.
3. Suggest a concrete focus order for the next engineering sprint.
4. Be direct and specific — no generic advice.

Return 5-8 bullet points only.
"""

    logger.debug("Generating portfolio summary for %d projects", len(ranked))
    llm = get_llm("analysis")
    llm_summary = invoke_with_retry(llm, prompt)

    # Combine structured data + LLM narrative
    header = "── Portfolio Overview ──\n"
    for i, s in enumerate(ranked, 1):
        header += (
            f"  #{i} {s.name:<20} "
            f"progress={s.progress_score:.0%}  "
            f"P0={s.p0_tasks}  open={s.open_tasks}\n"
        )

    return f"{header}\n{llm_summary}"
