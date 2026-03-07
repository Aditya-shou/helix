from typing import Any, Dict, List, TypedDict

from typing_extensions import NotRequired


class ProjectResult(TypedDict):
    """Holds the full analysis result for one project after its pipeline run."""

    project_id: int
    project_name: str
    memory_snapshot: Dict[str, Any]
    delta_summary: str
    progress_score: float
    auto_completed: List[str]
    analysis_text: str
    tasks: List[Dict[str, Any]]


class AgentState(TypedDict):
    # Input
    user_goal: str

    # Loaded from DB at start — list of project dicts
    projects: List[dict]

    # Accumulated log of everything that happened this run
    updates: List[str]

    # Per-project results — one entry appended per project after its pipeline
    project_results: NotRequired[List[ProjectResult]]

    # Cross-project portfolio summary (set by portfolio_summary_node)
    portfolio_summary: NotRequired[str]
