from typing import List, TypedDict


class AgentState(TypedDict):
    user_goal: str
    projects: List[dict]
    updates: List[str]
