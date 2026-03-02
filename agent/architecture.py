import ast
from collections import defaultdict
from pathlib import Path

from agent.ignore import is_ignored, load_gitignore


def extract_imports(tree):
    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                imports.append(n.name)

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

    return imports


def analyze_architecture(project_path: str):
    root = Path(project_path)

    dependency_graph = defaultdict(list)
    entry_points = []
    spec = load_gitignore(root)

    for file in root.rglob("*.py"):
        if is_ignored(file, root, spec):
            continue
        module_name = (
            file.relative_to(root).with_suffix("").as_posix().replace("/", ".")
        )

        if file.name == "main.py":
            entry_points.append(module_name)

        try:
            tree = ast.parse(file.read_text())
        except Exception:
            continue

        imports = extract_imports(tree)
        dependency_graph[module_name].extend(imports)

    return {
        "entry_points": entry_points,
        "dependencies": dict(dependency_graph),
    }
