import json

from db.database import SessionLocal
from db.memory_models import AgentMemory


def store_memory(memory_type: str, content: dict):
    session = SessionLocal()

    # Strip history to avoid recursion
    content = {k: v for k, v in content.items() if k != "history"}

    summary = {
        "filesystem": content.get("filesystem"),
        "architecture_known": "architecture" in content,
        "code_known": "code" in content,
        # Store actual data, not just booleans
        "architecture": content.get("architecture"),
        "code": content.get("code"),
    }

    # Don't store if nothing useful
    if not any(
        [summary["filesystem"], summary["architecture_known"], summary["code_known"]]
    ):
        session.close()
        return

    serialized = json.dumps(summary)

    # UPSERT: update latest record instead of inserting duplicate
    last = session.query(AgentMemory).order_by(AgentMemory.created_at.desc()).first()

    if last and last.memory_type == memory_type:
        if last.content == serialized:
            session.close()
            return  # No change, skip
        last.content = serialized  # ✅ Update in place
    else:
        session.add(AgentMemory(memory_type=memory_type, content=serialized))

    session.commit()
    session.close()


def load_memories() -> dict:
    """Load the single latest merged memory state (not a list)."""
    session = SessionLocal()
    last = session.query(AgentMemory).order_by(AgentMemory.created_at.desc()).first()
    session.close()

    if not last:
        return {}

    return json.loads(last.content)
