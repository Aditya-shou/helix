from pathlib import Path

import pathspec


def load_gitignore(root: Path):
    gitignore = root / ".gitignore"

    if not gitignore.exists():
        return None

    patterns = gitignore.read_text().splitlines()

    return pathspec.PathSpec.from_lines(
        "gitwildmatch",
        patterns,
    )


def is_ignored(path: Path, root: Path, spec):
    if not spec:
        return False

    relative = path.relative_to(root).as_posix()
    return spec.match_file(relative)
