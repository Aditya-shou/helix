# import time
from datetime import datetime, timezone

from langgraph.graph import END, StateGraph

from agent.analysis import analyze_project
from agent.architecture import analyze_architecture
from agent.autonomous import autonomous_step
from agent.code_understanding import analyze_codebase
from agent.filesystem import analyze_project_structure
from agent.memory import load_memories, store_memory
from agent.planner import create_plan
from agent.reflection import reflect_on_plan
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
            "project_path": p.project_path,  # ⭐ ADD THIS
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
    # workflow.add_node("filesystem_analysis", filesystem_analysis)
    # workflow.add_node("evaluate_progress", evaluate_progress)
    # workflow.add_node("planner_node", planner_node)
    # workflow.add_node("code_understanding", code_understanding)
    # workflow.add_node("architecture_understanding", architecture_understanding)
    workflow.add_node("autonomous_reasoner", autonomous_reasoner)
    workflow.add_node("analysis", analysis_node)
    workflow.add_node("reflection_node", reflection_node)

    workflow.set_entry_point("load_projects")

    workflow.add_edge("load_projects", "autonomous_reasoner")
    workflow.add_edge("autonomous_reasoner", "analysis")
    workflow.add_edge("analysis", "reflection_node")
    workflow.add_edge("reflection_node", END)

    return workflow.compile()


def filesystem_analysis(state: AgentState):
    session = SessionLocal()

    enriched_projects = []

    for proj in state["projects"]:
        project_db = session.get(Project, proj["id"])
        if project_db is None:
            continue

        analysis = analyze_project_structure(project_db.project_path)

        proj["analysis"] = analysis
        enriched_projects.append(proj)

    session.close()
    state["projects"] = enriched_projects
    return state


def planner_node(state: AgentState):
    plan = create_plan(state["projects"])

    state["updates"].append("\nHelix Plan:\n" + plan)

    return state


def reflection_node(state: AgentState):
    # last update contains planner output
    last_update = state["updates"][-1]

    refined_plan = reflect_on_plan(last_update, state["projects"])

    state["updates"].append("\nHelix Reflection:\n" + refined_plan)

    return state


def code_understanding(state: AgentState):
    session = SessionLocal()

    enriched_projects = []

    for proj in state["projects"]:
        project_db = session.get(Project, proj["id"])
        if project_db is None:
            continue

        code_info = analyze_codebase(project_db.project_path)

        proj["code_info"] = code_info
        enriched_projects.append(proj)

    session.close()

    state["projects"] = enriched_projects
    return state


def architecture_understanding(state: AgentState):
    session = SessionLocal()

    enriched_projects = []

    for proj in state["projects"]:
        project_db = session.get(Project, proj["id"])
        if not project_db:
            continue

        architecture = analyze_architecture(project_db.project_path)

        proj["architecture"] = architecture
        enriched_projects.append(proj)

    session.close()
    state["projects"] = enriched_projects
    return state


def autonomous_reasoner(state: AgentState):
    project = state["projects"][0]
    path = project["project_path"]

    past_memory = load_memories()
    memory = {**past_memory}

    MAX_STEPS = 10  # safety ceiling
    step = 0

    while step < MAX_STEPS:
        decision, memory = autonomous_step(path, memory)

        tool = decision.get("tool", "none")

        print(f"[Helix] Step {step + 1}: {decision}")

        #  Self-termination condition
        if tool == "none":
            print("[Helix] No further tools required. Stopping.")
            break

        step += 1

    store_memory("run_summary", memory)

    state["updates"].append(
        f"\nAutonomous reasoning completed in {step + 1} steps:\n{memory}"
    )
    state["memory_snapshot"] = memory

    return state


def analysis_node(state: AgentState):

    memory = state.get("memory_snapshot", {})

    analysis = analyze_project(memory)

    state["updates"].append("\nHelix Analysis:\n" + analysis)

    return state
