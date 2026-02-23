import subprocess
from pathlib import Path
from typing import Iterable

def is_git_repo(root: Path) -> bool:
    try:
        subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except Exception:
        return False


def git_tracked_files(root: Path) -> Iterable[Path]:
    """
    Yield all Git-tracked files under root.
    Fully respects:
    - .gitignore
    - core.excludes
    - nested repos
    """
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        capture_output=True,
        text=False,
        check=True,
    )

    for entry in result.stdout.split(b"\x00"):
        if not entry:
            continue
        yield root / entry.decode("utf-8", errors="ignore")


def git_tracked_python_files(root: Path) -> Iterable[Path]:
    for path in git_tracked_files(root):
        if path.suffix == ".py" and path.exists():
            yield path

def load_gitignore(root: Path):
    gitignore = root / ".gitignore"
    patterns = []

    if gitignore.exists():
        for line in gitignore.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.append(line)

    return patterns

def is_ignored(path: Path, root: Path, patterns):
    rel = path.relative_to(root).as_posix()

    for pattern in patterns:
        if rel.startswith(pattern.rstrip("/")):
            return True
    return False

def iter_python_files(root: Path, git_aware: bool = True):
    """
    Enumerate Python files.

    Modes:
    - Git-aware (default): use git ls-files
    - Fallback: filesystem scan
    """
    if git_aware and is_git_repo(root):
        yield from git_tracked_python_files(root)
        return

    # Fallback for non-git directories
    for path in root.rglob("*.py"):
        if path.is_file():
            yield path