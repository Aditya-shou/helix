"""
ignore.py
---------
Determines whether a file should be excluded from Helix's analysis.

Two layers of filtering:
  1. ALWAYS_IGNORE — hardcoded patterns that should never be analyzed
     regardless of .gitignore (pycache, venv, build artifacts, etc.)
  2. .gitignore    — project-specific patterns via pathspec
"""

from pathlib import Path

import pathspec

# Patterns that are ALWAYS ignored — no project should ever analyze these
ALWAYS_IGNORE: list[str] = [
    # Python cache
    "__pycache__",
    ".pyc",
    ".pyo",
    ".pyd",
    # Virtual environments — common names
    "venv",
    ".venv",
    "env",
    ".env",  # env dir (not .env file — pathspec handles file vs dir)
    "virtualenv",
    ".virtualenv",
    # Build / dist artifacts
    "build",
    "dist",
    ".eggs",
    "*.egg-info",
    # Type checker / linter caches
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    ".hypothesis",
    # IDE
    ".idea",
    ".vscode",
    # VCS
    ".git",
    # Node (in case of mixed projects)
    "node_modules",
]


def _is_always_ignored(path: Path) -> bool:
    """
    Check if any part of the path matches an always-ignore pattern.
    Checks every component so nested pycache dirs are caught too.
    """
    parts = path.parts
    path_str = str(path)

    for pattern in ALWAYS_IGNORE:
        if pattern.startswith("*"):
            # Extension / glob match
            suffix = pattern[1:]  # e.g. ".pyc"
            if path_str.endswith(suffix):
                return True
        else:
            # Directory / name match — check every path component
            if pattern in parts:
                return True

    return False


def load_gitignore(root: Path) -> pathspec.PathSpec | None:
    gitignore = root / ".gitignore"

    if not gitignore.exists():
        return None

    patterns = gitignore.read_text().splitlines()
    return pathspec.PathSpec.from_lines("gitwildmatch", patterns)


def is_ignored(path: Path, root: Path, spec: pathspec.PathSpec | None) -> bool:
    """
    Returns True if the file should be excluded from analysis.
    Checks always-ignore patterns first, then .gitignore.
    """
    # Always-ignore check (catches venv, pycache, etc.)
    if _is_always_ignored(path):
        return True

    # .gitignore check
    if spec:
        try:
            relative = path.relative_to(root).as_posix()
            if spec.match_file(relative):
                return True
        except ValueError:
            # path is not relative to root — skip it
            return True

    return False
