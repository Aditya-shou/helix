from datetime import datetime, timezone

from langgraph.graph import END, StateGraph

from agent.filesystem import analyze_project
from agent.planner import create_plan
from agent.state import AgentState
from db.models import Project, SessionLocal


def load_projects(state: AgentState):
    session = SessionLocal()
    projects = session.query(Project).all()

    state["projects"] = [
        {
            "id": p.id,
            "name": p.name,
            "goals": p.goals,
            "progress_score": p.progress_score,
        }
        for p in projects
    ]

    session.close()
    return state


def evaluate_progress(state: AgentState):
    session = SessionLocal()

    updates = []

    for proj in state["projects"]:
        goals = proj["goals"].split(",")

        # TEMP LOGIC (later to be replaced by repo analysis)
        analysis = proj.get("analysis", {})

        score = 0
        total = len(goals)

        for g in goals:
            g = g.strip().lower()

            if "database" in g:
                score += 1

            elif "cli" in g and analysis.get("has_cli"):
                score += 1

            elif "test" in g and analysis.get("tests", 0) > 0:
                score += 1

        progress = score / total if total else 0

        project_db = session.get(Project, proj["id"])

        if project_db is None:
            updates.append(f"Warning: Project id {proj['id']} not found in DB")
            continue

        project_db.progress_score = progress
        project_db.status = "Completed" if progress >= 1 else "In Progress"
        project_db.last_checked = datetime.now(timezone.utc)

        updates.append(f"{project_db.name} updated → {progress * 100:.0f}%")

    session.commit()
    session.close()

    state["updates"] = updates
    return state


def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("load_projects", load_projects)
    workflow.add_node("filesystem_analysis", filesystem_analysis)
    workflow.add_node("evaluate_progress", evaluate_progress)
    workflow.add_node("planner_node", planner_node)

    workflow.set_entry_point("load_projects")

    workflow.add_edge("load_projects", "filesystem_analysis")
    workflow.add_edge("filesystem_analysis", "evaluate_progress")
    workflow.add_edge("evaluate_progress", "planner_node")
    workflow.add_edge("planner_node", END)

    return workflow.compile()


def filesystem_analysis(state: AgentState):
    session = SessionLocal()

    enriched_projects = []

    for proj in state["projects"]:
        project_db = session.get(Project, proj["id"])
        if project_db is None:
            continue

        analysis = analyze_project(project_db.project_path)

        proj["analysis"] = analysis
        enriched_projects.append(proj)

    session.close()
    state["projects"] = enriched_projects
    return state


def planner_node(state: AgentState):
    plan = create_plan(state["projects"])

    state["updates"].append("\nHelix Plan:\n" + plan)

    return state
