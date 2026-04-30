import subprocess
import tempfile
from pathlib import Path

from dennis.utils import iter_files


def test_iter_files_use_git_changed_falls_back_to_git_ignored_scan():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)

        (root / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
        (root / "a.py").write_text("print('hello')\n", encoding="utf-8")
        (root / "b.py").write_text("print('untracked')\n", encoding="utf-8")
        (root / "ignored.txt").write_text("secret\n", encoding="utf-8")

        subprocess.run(["git", "add", "a.py", ".gitignore"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)

        paths = list(iter_files(root, git_mode="changed"))
        path_set = {p.resolve() for p in paths}

        assert (root / "a.py").resolve() in path_set
        assert (root / "b.py").resolve() in path_set
        assert (root / "ignored.txt").resolve() not in path_set
