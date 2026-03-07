from db.book_models import Book, BookNote, BookSummary  # noqa: F401
from db.database import Base, engine

# Import ALL models so Base.metadata knows about every table
from db.memory_models import AgentMemory  # noqa: F401
from db.models import Project, Task  # noqa: F401
from db.snapshot_models import ProjectSnapshot  # noqa: F401

Base.metadata.create_all(bind=engine)

print("Database initialized — tables: projects, tasks, agent_memory")
