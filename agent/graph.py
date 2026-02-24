from datetime import datetime, timezone

from langgraph.graph import END, StateGraph

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
        progress = min(len(goals) * 0.2, 1.0)

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
    workflow.add_node("evaluate_progress", evaluate_progress)

    workflow.set_entry_point("load_projects")
    workflow.add_edge("load_projects", "evaluate_progress")
    workflow.add_edge("evaluate_progress", END)

    return workflow.compile()
