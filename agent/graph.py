"""
graph.py
--------
LangGraph pipeline for Helix.

Pipeline shape:
    load_projects
          ↓
    project_loop          ← iterates over every project in state["projects"]
    (per project):
        autonomous_reasoner
        snapshot
        analysis
        tasks
          ↓
    portfolio_summary     ← cross-project priority view
          ↓
    reflection            ← reflects on the full portfolio
          ↓
    END
"""

import logging
import time

from langgraph.graph import END, StateGraph

from agent.analysis import analyze_project
from agent.autonomous import autonomous_step
from agent.config import settings
from agent.memory import load_memories, store_memory
from agent.portfolio_summary import build_portfolio_summary
from agent.progress_evaluator import evaluate_and_snapshot
from agent.reflection import reflect_on_plan
from agent.state import AgentState, ProjectResult
from agent.task_extractor import extract_tasks
from agent.task_persister import persist_tasks
from db.database import SessionLocal
from db.models import Project, Task

logger = logging.getLogger(__name__)


# Individual project pipeline


def _run_project_pipeline(project: dict) -> ProjectResult:
    """
    Run the full reasoning pipeline for a single project.
    Returns a ProjectResult with everything Helix learned.
    """
    project_id = project["id"]
    project_name = project["name"]
    project_path = project["project_path"]

    logger.info(
        "── Starting pipeline for project: %s (id=%d)", project_name, project_id
    )

    # Autonomous reasoning
    past_memory = load_memories(project_id)
    memory = {**past_memory}

    step = 0
    while step < settings.agent_max_steps:
        decision, memory = autonomous_step(project_path, memory)
        tool = decision.get("tool", "none")

        logger.info("[%s] Step %d: tool=%s", project_name, step + 1, tool)
        time.sleep(1)

        if tool == "none":
            logger.info("[%s] Reasoning complete.", project_name)
            break

        step += 1

    store_memory(project_id, memory)

    # 2. Snapshot + progress diff
    session = SessionLocal()
    open_count = (
        session.query(Task).filter_by(project_id=project_id, status="open").count()
    )
    completed_count = (
        session.query(Task).filter_by(project_id=project_id, status="completed").count()
    )
    session.close()

    snapshot_result = evaluate_and_snapshot(
        project_id,
        {
            "filesystem": memory.get("filesystem", {}),
            "code": memory.get("code", {}),
            "task_counts": {"open": open_count, "completed": completed_count},
        },
    )

    delta_summary = snapshot_result["delta_summary"]
    progress_score = snapshot_result["progress_score"]
    auto_completed = snapshot_result["auto_completed"]

    logger.info(
        "[%s] Snapshot saved. Progress=%.0f%% auto_completed=%s",
        project_name,
        progress_score * 100,
        auto_completed,
    )

    #  Analysis
    enriched_memory = {
        **memory,
        "progress_delta": delta_summary,
        "progress_score": progress_score,
    }
    analysis_text = analyze_project(enriched_memory)
    logger.info("[%s] Analysis complete (%d chars).", project_name, len(analysis_text))

    # Task extraction + persistence
    tasks = extract_tasks(analysis_text)
    persistence = persist_tasks(project_id, tasks)
    logger.info(
        "[%s] Tasks — inserted: %d, skipped: %d",
        project_name,
        persistence["inserted"],
        persistence["skipped"],
    )

    return ProjectResult(
        project_id=project_id,
        project_name=project_name,
        memory_snapshot=memory,
        delta_summary=delta_summary,
        progress_score=progress_score,
        auto_completed=auto_completed,
        analysis_text=analysis_text,
        tasks=tasks,
    )


# Graph nodes


def load_projects(state: AgentState) -> AgentState:
    session = SessionLocal()
    projects = session.query(Project).all()
    state["projects"] = [
        {
            "id": p.id,
            "name": p.name,
            "goals": p.goals,
            "project_path": p.project_path,
        }
        for p in projects
    ]
    session.close()
    logger.info("Loaded %d project(s).", len(state["projects"]))
    return state


def project_loop_node(state: AgentState) -> AgentState:
    """
    Iterate over every project and run the full pipeline for each.
    Results accumulate in state["project_results"].
    """
    results: list[ProjectResult] = []

    for i, project in enumerate(state["projects"], 1):
        logger.info(
            "Processing project %d/%d: %s",
            i,
            len(state["projects"]),
            project["name"],
        )
        try:
            result = _run_project_pipeline(project)
            results.append(result)

            state["updates"].append(
                f"\n── {project['name']} ──\n"
                f"Progress: {result['progress_score']:.0%}\n"
                f"Delta: {result['delta_summary']}\n"
                f"Tasks inserted: {sum(1 for t in result['tasks'])}\n"
                + (
                    f"Auto-completed: {', '.join(result['auto_completed'])}\n"
                    if result["auto_completed"]
                    else ""
                )
            )

        except Exception as e:
            logger.error("Pipeline failed for project '%s': %s", project["name"], e)
            state["updates"].append(
                f"\n[ERROR] {project['name']}: pipeline failed — {e}"
            )

    state["project_results"] = results
    return state


def portfolio_summary_node(state: AgentState) -> AgentState:
    """
    After all projects are processed, build a cross-project priority view.
    """
    project_ids = [p["id"] for p in state["projects"]]

    if not project_ids:
        return state

    summary = build_portfolio_summary(project_ids)
    state["portfolio_summary"] = summary
    state["updates"].append(f"\n── Portfolio Summary ──\n{summary}")

    logger.info("Portfolio summary generated.")
    return state


def reflection_node(state: AgentState) -> AgentState:
    """
    Reflect on the portfolio as a whole.
    Uses the portfolio summary + all individual analyses as context.
    """
    results: list[ProjectResult] = state.get("project_results", [])

    if not results:
        state["updates"].append("[Helix] Reflection skipped — no results.")
        return state

    # Build a condensed context from all project analyses
    combined = ""
    for r in results:
        combined += (
            f"\n=== {r['project_name']} (progress={r['progress_score']:.0%}) ===\n"
            f"{r['analysis_text'][:800]}...\n"  # trim to avoid huge prompts
            f"Delta: {r['delta_summary']}\n"
        )

    portfolio = state.get("portfolio_summary", "")
    context = f"{combined}\n\nPortfolio Priority:\n{portfolio}"

    refined = reflect_on_plan(context, state["projects"])
    state["updates"].append(f"\nHelix Reflection:\n{refined}")
    logger.info("Reflection complete.")
    return state


# Building the graph flow


def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("load_projects", load_projects)
    workflow.add_node("project_loop", project_loop_node)
    workflow.add_node("portfolio_summary", portfolio_summary_node)
    workflow.add_node("reflection_node", reflection_node)

    workflow.set_entry_point("load_projects")

    workflow.add_edge("load_projects", "project_loop")
    workflow.add_edge("project_loop", "portfolio_summary")
    workflow.add_edge("portfolio_summary", "reflection_node")
    workflow.add_edge("reflection_node", END)

    return workflow.compile()
