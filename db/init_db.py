from db.database import Base, engine
from db.memory_models import AgentMemory  # noqa: F401

# IMPORTANT: import models BEFORE create_all
from db.models import Project  # noqa: F401

Base.metadata.create_all(bind=engine)

print("Database initialized.")
