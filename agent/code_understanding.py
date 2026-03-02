import ast
from pathlib import Path

from agent.ignore import is_ignored, load_gitignore


def analyze_python_file(file_path: Path):
    """Extract semantic information from Python file."""
    try:
        tree = ast.parse(file_path.read_text())
    except Exception:
        return None

    classes = []
    functions = []
    sqlalchemy_models = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            classes.append(node.name)

            # detect SQLAlchemy model
            for base in node.bases:
                if getattr(base, "id", "") == "Base":
                    sqlalchemy_models.append(node.name)

        elif isinstance(node, ast.FunctionDef):
            functions.append(node.name)

    return {
        "classes": classes,
        "functions": functions,
        "models": sqlalchemy_models,
    }


def analyze_codebase(project_path: str):
    root = Path(project_path)

    results = {
        "total_classes": 0,
        "total_functions": 0,
        "models": [],
    }
    spec = load_gitignore(root)

    for file in root.rglob("*.py"):
        analysis = analyze_python_file(file)
        if is_ignored(file, root, spec):
            continue
        if not analysis:
            continue

        results["total_classes"] += len(analysis["classes"])
        results["total_functions"] += len(analysis["functions"])
        results["models"].extend(analysis["models"])

    return results
