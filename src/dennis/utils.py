import subprocess
from pathlib import Path
from typing import Iterable

from datetime import datetime

from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern

def get_dennis_home() -> Path:
    return Path.home() / ".dennis"


def get_plugin_dir() -> Path:
    return get_dennis_home() / "plugins"


def get_dict_dir() -> Path:
    return get_dennis_home() / "dictionaries"


def get_backup_dir() -> Path:
    return get_dennis_home() / "backups"


def ensure_dennis_dirs():
    get_plugin_dir().mkdir(parents=True, exist_ok=True)
    get_dict_dir().mkdir(parents=True, exist_ok=True)
    get_backup_dir().mkdir(parents=True, exist_ok=True)


def build_clean_filename(original_path, filters):
    path = original_path

    base = path.stem  # tacosroy
    suffix = path.suffix  # .json

    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M")

    filters_str = "-".join(filters)

    new_name = f"{base}.cleaned.{filters_str}.{timestamp}{suffix}"

    return path.with_name(new_name)

def get_scope_files(path: str | Path) -> list[str]:
    """
    Return the canonical file list used to generate .dexscope.

    Git is authoritative when the project is a Git repository.
    Dennis includes tracked files and untracked files that are
    not excluded by Git's ignore rules.

    Otherwise Dennis falls back to a native Python filesystem walk.
    """
    root = Path(path).resolve()

    if is_git_repo(root):
        try:
            return sorted(
                p.relative_to(root).as_posix()
                for p in git_unignored_files(root)
            )
        except (subprocess.SubprocessError, OSError):
            print(
                "[Dennis] WARNING: Git scope discovery failed; "
                "falling back to filesystem scan."
            )

    return get_filesystem_scope(root)


def create_dexscope(root: Path) -> bool:
    """
    Create .dexscope if it does not already exist.

    Scope discovery is performed here so this utility remains independent
    of the CLI layer.

    Git is authoritative when the project is a Git repository.
    Otherwise, native filesystem discovery is used.

    Returns:
        True if .dexscope was created.
        False if it already existed.
    """
    root = Path(root).resolve()
    scope_file = root / ".dexscope"

    if scope_file.exists():
        return False

    if is_git_repo(root):
        try:
            files = sorted(
                p.relative_to(root).as_posix()
                for p in git_unignored_files(root)
            )
        except (subprocess.SubprocessError, OSError):
            print(
                "[Dennis] WARNING: Git scope discovery failed; "
                "falling back to filesystem scan."
            )
            files = get_filesystem_scope(root)
    else:
        files = get_filesystem_scope(root)

    lines = [
        "# Dennis Scope v1",
        "",
        *files,
    ]

    scope_file.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    return True


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


def git_unignored_files(root: Path) -> Iterable[Path]:
    """
    Yield all files in the repository that are not ignored by Git.

    This includes tracked files and untracked files that are
    not excluded by Git's ignore rules.
    """
    yield from git_tracked_files(root)

    result = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=root,
        capture_output=True,
        text=False,
        check=True,
    )

    for entry in result.stdout.split(b"\x00"):
        if entry:
            yield root / entry.decode("utf-8", errors="ignore")


def get_filesystem_scope(root: Path) -> list[str]:
    """
    Return the canonical project file list using a native filesystem walk.

    This is the platform-independent fallback used when Git is unavailable
    or the project is not a Git repository.

    Paths are returned relative to the project root and normalized to POSIX
    separators so .dexscope remains deterministic across operating systems.

    .gitignore is honored when present.
    """
    root = Path(root).resolve()

    gitignore = root / ".gitignore"
    spec = None

    if gitignore.exists():
        lines = gitignore.read_text(
            encoding="utf-8"
        ).splitlines()

        spec = PathSpec.from_lines(
            GitWildMatchPattern,
            lines,
        )

    files = []

    for path in root.rglob("*"):

        if not path.is_file():
            continue

        relative = path.relative_to(root)
        normalized = relative.as_posix()

        if spec and spec.match_file(normalized):
            continue

        files.append(normalized)

    return sorted(files)


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

def git_changed_files(root: Path) -> Iterable[Path]:
    """
    Yield files changed in working tree (staged + unstaged).
    """
    try:
        files = set()

        # Unstaged changes
        result = subprocess.run(
            ["git", "diff", "--name-only"],
            cwd=root,
            capture_output=True,
            check=True,
        )

        for line in result.stdout.splitlines():
            if line.strip():
                files.add(line.strip())

        # Staged changes
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=root,
            capture_output=True,
            check=True,
        )

        for line in result.stdout.splitlines():
            if line.strip():
                files.add(line.strip())

        for f in files:
            path = root / f
            if path.exists() and path.is_file():
                yield path

    except Exception:
        return


def iter_files(root: Path, git_mode: str = "tracked"):
    """
    Enumerate files.

    Modes:
    - tracked (default): git ls-files
    - changed: staged + unstaged changes
    - fallback: filesystem scan
    """

    # ----------------------------------------
    # Git-aware modes
    # ----------------------------------------
    if is_git_repo(root):

        try:
            # ----------------------------------------
            # MODE: changed files only
            # ----------------------------------------
            if git_mode == "changed":

                changed = list(git_changed_files(root))

                if changed:
                    print(f"[Dennis] Git changed files detected ({len(changed)})")
                    for f in changed:
                        yield f
                    return

                print("[Dennis] No git changes detected. Scanning git repository files excluding .gitignore.")
                yield from git_unignored_files(root)
                return

            # ----------------------------------------
            # MODE: tracked files (default)
            # ----------------------------------------
            result = subprocess.run(
                ["git", "ls-files", "-z"],
                cwd=root,
                capture_output=True,
                text=False,
                check=True,
            )

            for entry in result.stdout.split(b"\x00"):
                if entry:
                    yield root / entry.decode("utf-8", errors="ignore")

            return

        except Exception:
            print("[Dennis] WARNING: git failed, falling back to filesystem scan")

    # ----------------------------------------
    # Fallback: filesystem scan
    # ----------------------------------------
    for path in root.rglob("*"):
        if path.is_file():
            yield path


def load_wordlist(path: Path) -> set[str]:
    words = set()
    

    if not path.exists():
        return words

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            words.add(line.lower())

    return words

def load_dictionary(name: str) -> set[str]:
    """
    Load dictionary by name (e.g. 'sql.dict')

    Merges:
    - core dictionary
    - user dictionary (~/.dennis/dictionaries/)
    """

    base_dir = Path(__file__).resolve().parent

    core_path = base_dir / "dictionaries" / name
    user_path = get_dict_dir() / name

    core_words = load_wordlist(core_path)
    user_words = load_wordlist(user_path)

    return core_words | user_words
    

def cleaned_filename(path: Path) -> Path:
    from datetime import datetime

    ts = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")

    return path.with_name(f"{path.stem}.cleaned.{ts}{path.suffix}")
    

def looks_like_binary(text: str) -> bool:
    if not text:
        return False

    # high ratio of non-printable chars
    non_printable = sum(1 for c in text if ord(c) < 32 or ord(c) > 126)
    ratio = non_printable / len(text)

    if ratio > 0.3:
        return True

    # contains many null bytes or weird unicode blocks
    if "\x00" in text:
        return True

    # long string with very low whitespace
    if len(text) > 20 and text.count(" ") == 0:
        weird = sum(1 for c in text if not c.isalnum())
        if weird / len(text) > 0.4:
            return True

    return False

def looks_like_html(text: str) -> bool:
    if not text:
        return False

    t = text.strip().lower()

    # basic tags
    if "<" in t and ">" in t:
        return True

    # common html patterns
    if any(x in t for x in [
        "<div", "<span", "<button", "<table",
        "<tr", "<td", "<form", "<input",
        "class=", "style=", "id="
    ]):
        return True

    return False

def contains_sql_token_like(text: str) -> bool:
    for word in text.split():
        if "_" in word and word.isupper():
            return True
    return False

CSS_KEYWORDS = {
    "display", "flex", "block", "inline",
    "padding", "margin", "color", "background",
    "font", "border", "width", "height",
    "align-items", "justify-content", "gap", "font", "div", "div style", "class", "style",
    "flex:", "background-color", "align-items", "justify-content", "div class", "span class",
    "div id", "span id", "text-align", "display:", "position:", "top:", "left:", "right:", "bottom:",
    "overflow:", "z-index:", "float:", "clear:", "cursor:", "visibility:", "opacity:"
}

def looks_like_css(text: str) -> bool:
    if not text:
        return False

    lower = text.lower()

    # inline style attribute
    if "style=" in lower:
        return True

    # typical CSS structure
    if ":" in text and ";" in text:
        return True

    # CSS units
    if any(unit in lower for unit in ["px", "%", "rem", "em"]):
        return True

    # multiple CSS keywords
    matches = sum(1 for k in CSS_KEYWORDS if k in lower)
    if matches >= 2:
        return True

    return False

def sql_score(text: str, sql_words: set) -> int:
    score = 0
    upper = text.upper()

    # ----------------------------------------
    # 1. Dictionary matches (strong signal)
    # ----------------------------------------
    for word in sql_words:
        if word in upper:
            score += 3

    # ----------------------------------------
    # 2. SQL structure patterns
    # ----------------------------------------
    if "(" in text and ")" in text:
        score += 2

    if "=" in text:
        score += 1

    if "?" in text:
        score += 2

    # ----------------------------------------
    # 3. SQL formatting clues
    # ----------------------------------------
    if "," in text and " AS " in upper:
        score += 2

    if "`" in text:
        score += 2

    # ----------------------------------------
    # 4. underscore-heavy identifiers
    # ----------------------------------------
    if "_" in text:
        score += 1

    return score

def contains_dict_word(text: str, words: set) -> bool:
    upper = text.upper()

    for word in words:
        if "_" in word and word in upper:
            return True

    return False

def apply_all_filters(mapping: dict) -> dict:
    cleaned = {}

    from dennis.classifiers.url import is_url

    sql_words = load_sql_dictionary()

    for key, value in mapping.items():
        if not isinstance(value, str):
            continue

        if looks_like_binary(value):
            continue

        if is_url(value):
            continue

        if looks_like_css(value):
            continue

        score = sql_score(value, sql_words)

        if contains_dict_word(value, sql_words):
            score += 3

        if score >= 4:
            continue

        cleaned[key] = value

    return cleaned

# load sql dictionary safely
def load_sql_dictionary():
    raw = load_dictionary("sql.dict")

    if isinstance(raw, dict):
        return set(raw.keys())
    elif isinstance(raw, (set, list)):
        return set(raw)
    return set()
