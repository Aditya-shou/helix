from pathlib import Path

from agent.ignore import is_ignored, load_gitignore


def analyze_project_structure(path: str):
    root = Path(path)
    spec = load_gitignore(root)

    files = []
    tests = 0

    for f in root.rglob("*.py"):
        if is_ignored(f, root, spec):
            continue

        files.append(f)

        if "test" in f.name.lower():
            tests += 1

    has_cli = any(f.name == "main.py" for f in files)

    return {
        "files": len(files),
        "tests": tests,
        "has_cli": has_cli,
    }


def load_ignore_patterns(root: Path):
    ignore_file = root / ".helixignore"

    if not ignore_file.exists():
        return []

    return [
        line.strip()
        for line in ignore_file.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]


def should_ignore(path: Path, ignore_patterns):
    path_str = str(path)

    for pattern in ignore_patterns:
        if pattern.endswith("/"):
            if pattern[:-1] in path_str:
                return True
        elif pattern.startswith("*"):
            if path_str.endswith(pattern[1:]):
                return True
        elif pattern in path_str:
            return True

    return False
