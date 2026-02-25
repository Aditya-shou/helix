from pathlib import Path


def analyze_project(path: str):
    root = Path(path)

    if not root.exists():
        return {
            "files": 0,
            "tests": 0,
            "has_cli": False,
        }

    files = list(root.rglob("*.py"))
    test_files = [f for f in files if "test" in f.name.lower()]

    has_cli = any(f.name == "main.py" for f in files)

    return {
        "files": len(files),
        "tests": len(test_files),
        "has_cli": has_cli,
    }
