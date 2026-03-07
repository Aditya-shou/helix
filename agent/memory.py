"""
memory.py
---------
Per-project memory storage. Each project gets its own memory_type key
so projects never overwrite each other's gathered tool data.
"""

import json
import logging

from db.database import SessionLocal
from db.memory_models import AgentMemory

logger = logging.getLogger(__name__)


def _memory_key(project_id: int) -> str:
    return f"project_{project_id}_run_summary"


def store_memory(project_id: int, content: dict) -> None:
    """Persist memory for a specific project."""
    session = SessionLocal()

    # Never store the history key — it causes recursion bloat
    content = {k: v for k, v in content.items() if k != "history"}

    summary = {
        "filesystem": content.get("filesystem"),
        "architecture_known": "architecture" in content,
        "code_known": "code" in content,
        "architecture": content.get("architecture"),
        "code": content.get("code"),
    }

    if not any(
        [summary["filesystem"], summary["architecture_known"], summary["code_known"]]
    ):
        session.close()
        return

    serialized = json.dumps(summary)
    memory_type = _memory_key(project_id)

    last = (
        session.query(AgentMemory)
        .filter_by(memory_type=memory_type)
        .order_by(AgentMemory.created_at.desc())
        .first()
    )

    if last:
        if last.content == serialized:
            logger.debug(
                "Memory unchanged for project %d — skipping write.", project_id
            )
            session.close()
            return
        last.content = serialized
    else:
        session.add(AgentMemory(memory_type=memory_type, content=serialized))

    session.commit()
    session.close()
    logger.debug("Memory stored for project %d.", project_id)


def load_memories(project_id: int) -> dict:
    """Load the latest memory state for a specific project."""
    session = SessionLocal()
    memory_type = _memory_key(project_id)

    last = (
        session.query(AgentMemory)
        .filter_by(memory_type=memory_type)
        .order_by(AgentMemory.created_at.desc())
        .first()
    )
    session.close()

    if not last:
        logger.debug("No memory found for project %d — starting fresh.", project_id)
        return {}

    return json.loads(last.content)
