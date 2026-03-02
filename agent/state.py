from typing import Any, Dict, List, TypedDict

from typing_extensions import NotRequired


class AgentState(TypedDict):
    user_goal: str
    projects: List[dict]
    updates: List[str]
    memory_snapshot: NotRequired[Dict[str, Any]]
