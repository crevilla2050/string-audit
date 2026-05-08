import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from difflib import unified_diff, SequenceMatcher
import os
import hashlib
import unicodedata
import copy


# Schema constants
DIFF_SCHEMA_TYPE = "dennis.diff.v1"

# Ignored file extensions
IGNORED_EXTENSIONS = {'.png', '.dex', '.pub', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.svg'}


def normalize_line(text: str) -> str:
    """
    LOSSLESS CANONICAL DIFF RULES - Line Normalization

    1. Lines stored EXACTLY as sequences of Unicode code points
    2. Unicode normalized to NFC (required for determinism)
    3. Line endings normalized to LF
    4. No trimming, no normalization inside lines
    5. Encoding normalized to UTF-8 ONLY at boundary
    6. No collapsing of whitespace (trailing spaces, tabs, non-breaking spaces)
    7. Empty lines MUST be preserved
    8. Line ordering MUST be preserved

    Decision: Unicode NFC normalized, content preserved (practical over perfect)
    """
    # Normalize to NFC form for deterministic Unicode representation
    text = unicodedata.normalize("NFC", text)
    # Normalize line endings to LF
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    return text


def normalize_encoding(data: bytes) -> str:
    """
    ENCODING NORMALIZATION - Strict UTF-8

    Required at file read boundary to ensure all content is consistently encoded.
    Uses strict decoding to fail fast on invalid input rather than silently corrupting.
    """
    return data.decode("utf-8", errors="strict")


def canonical_json(obj: Any) -> str:
    """
    CANONICAL JSON SERIALIZATION - Frozen Rules

    Required for deterministic hashing and cross-system compatibility.

    Rules:
    - UTF-8 encoding (no BOM)
    - Keys sorted lexicographically
    - Arrays preserve order (DO NOT SORT)
    - No optional fields omitted
    - Empty arrays must be explicit
    - No trailing commas
    - No pretty-print whitespace (compact format)
    - Controlled separators: (",", ":")
    """
    return json.dumps(
        obj,
        sort_keys=True,           # Keys sorted lexicographically
        separators=(',', ':'),    # Controlled separators
        ensure_ascii=False        # Allow Unicode characters
    )


def is_binary_file(file_path: Path) -> bool:
    """Check if a file is binary by reading the first 1024 bytes."""
    try:
        with open(file_path, 'rb') as f:
            data = f.read(1024)
            # Check for null bytes or non-text characters
            text_chars = bytearray({7,8,9,10,12,13,27} | set(range(0x20, 0x100)) - {0x7f})
            return bool(data.translate(None, text_chars))
    except:
        return True


def is_git_repo(path: Path) -> bool:
    """Check if a directory is a git repository."""
    return (path / ".git").exists()


def get_git_tracked_files(path: Path) -> List[str]:
    """
    Get list of git-tracked files in a repository.
    Returns relative paths from the repository root.
    
    Falls back to empty list if git command fails.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "ls-files"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10  # Add timeout for safety
        )
        return result.stdout.splitlines()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        # Git not available, command failed, or timeout
        return []


def should_ignore_file(rel_path: Path) -> bool:
    path = rel_path.as_posix()

    # --------------------------------------------------
    # 1. Ignore git internals
    # --------------------------------------------------
    if path.startswith(".git/"):
        return True

    # --------------------------------------------------
    # 2. Ignore Dennis internal artifacts
    # --------------------------------------------------
    if path.startswith(".dennis/"):
        return True

    # --------------------------------------------------
    # 3. Ignore obvious binary / media outputs / keys
    # --------------------------------------------------
    if path.endswith((
        ".png", ".jpg", ".jpeg", ".gif", ".ico", ".key", ".pem", ".pub", ".svg",
        ".pdf", ".zip", ".tar", ".gz", ".dex", ".class", ".exe", ".dll", ".so"
    )):
        return True

    # --------------------------------------------------
    # 4. Ignore known generated Dennis artifacts
    # --------------------------------------------------
    if "dennis-plan" in path:
        return True

    if path.startswith("dictionary-"):
        return True

    if path.startswith("payload/"):
        return True

    if path.endswith(".json") and (
        "dennis" in path or
        "plan" in path or
        "manifest" in path
    ):
        return True

    # --------------------------------------------------
    # 5. OTHERWISE: KEEP IT
    # --------------------------------------------------
    return False


def group_changes_into_blocks(lines_a: List[str], lines_b: List[str]) -> List[Dict[str, Any]]:
    """
    BLOCK DETERMINISM - Maximal Contiguous Blocks

    BLOCK DEFINITION:
    A block is a maximal contiguous sequence of changed lines.

    RULES:
    - Adjacent changes MUST be merged into a single block
    - No two blocks may be contiguous
    - Blocks must be strictly separated by unchanged lines

    This guarantees uniqueness across all generators.
    """
    changes = []
    matcher = SequenceMatcher(None, lines_a, lines_b)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            continue

        # Convert to 1-based line numbers
        start_line = i1 + 1
        end_line = i2

        before_lines = lines_a[i1:i2] if i2 > i1 else []
        after_lines = lines_b[j1:j2] if j2 > j1 else []

        if tag == 'insert':
            change_type = 'insert'
        elif tag == 'delete':
            change_type = 'delete'
        elif tag == 'replace':
            change_type = 'replace'
        else:
            continue

        changes.append({
            'type': change_type,
            'start_line': start_line,
            'end_line': max(end_line, start_line),  # Ensure end_line >= start_line
            'before': before_lines,
            'after': after_lines
        })

    # POST-PROCESSING: Merge adjacent blocks
    # This ensures maximal contiguous blocks
    # Spec: Adjacent changes MUST be merged into a single block
    # Adjacency is ONLY defined by line position, NOT by change type
    if not changes:
        return changes

    merged_changes = [changes[0]]

    for current in changes[1:]:
        last = merged_changes[-1]

        # Check if blocks are adjacent (no unchanged lines between them)
        # Spec: Merge based ONLY on adjacency, not on type
        if last['end_line'] + 1 == current['start_line']:
            # Merge blocks - content defines the merge, not semantics
            last['end_line'] = current['end_line']
            last['before'].extend(current['before'])
            last['after'].extend(current['after'])
            
            # Infer merged type from contents
            if last['before'] and last['after']:
                last['type'] = 'replace'
            elif not last['before'] and last['after']:
                last['type'] = 'insert'
            elif last['before'] and not last['after']:
                last['type'] = 'delete'
        else:
            merged_changes.append(current)

    return merged_changes


def infer_file_status(changes):
    has_insert = any(c['type'] == 'insert' for c in changes)
    has_delete = any(c['type'] == 'delete' for c in changes)
    has_replace = any(c['type'] == 'replace' for c in changes)

    # File added: only inserts
    if has_insert and not has_delete and not has_replace:
        return 'added'

    # File removed: only deletes
    if has_delete and not has_insert and not has_replace:
        return 'removed'

    # Otherwise → modified
    return 'modified'


def normalize_to_dennis_diff_v1(diff_artifact: Dict[str, Any]) -> Dict[str, Any]:
    """
    CANONICALIZATION Layer - MANDATORY, LOSSLESS, MINIMAL

    CANONICAL DIFF MUST BE MINIMAL invariant:
    - No redundant changes
    - No duplicate blocks
    - No empty changes
    - No structural redundancy (but NOT semantic pruning)

    LOSSLESS RULES (preserved exactly):
    1. Lines as sequences of Unicode code points
    2. No trimming, no normalization inside lines
    3. Encoding normalized to UTF-8 ONLY at boundary
    4. No collapsing of whitespace (trailing spaces, tabs, non-breaking spaces)
    5. Empty lines MUST be preserved
    6. Line ordering MUST be preserved

    This is the identity-defining normalization.
    Idempotency: normalize_canonical(normalize_canonical(x)) == normalize_canonical(x)
    """
    if not isinstance(diff_artifact, dict) or diff_artifact.get('type') != DIFF_SCHEMA_TYPE:
        raise ValueError("Invalid diff artifact")

    payload = diff_artifact.get('payload', {})
    files = payload.get('files', [])

    # Sort files deterministically by path
    normalized_files = sorted(files, key=lambda f: f['path'])

    for file_info in normalized_files:
        changes = file_info.get('changes', [])

        # Normalize lines with NFC Unicode normalization and line ending normalization (lossless)
        for change in changes:
            change['before'] = [normalize_line(line) for line in change['before']]
            change['after'] = [normalize_line(line) for line in change['after']]

        # MINIMAL invariant: Remove empty changes (structural redundancy)
        # Empty changes have no before or after content
        filtered_changes = []
        for change in changes:
            if change['before'] or change['after']:  # Keep if has content
                filtered_changes.append(change)

        # Sort changes by start_line for deterministic ordering
        filtered_changes.sort(key=lambda c: c['start_line'])

        file_info['changes'] = filtered_changes

    # MINIMAL invariant: Remove files with no changes
    normalized_files = [f for f in normalized_files if f['changes']]

    return {
        'type': DIFF_SCHEMA_TYPE,
        'payload': {
            'files': normalized_files
        }
    }


def normalize_view(diff_artifact: Dict[str, Any], filters: Optional[Dict[str, bool]] = None) -> Dict[str, Any]:
    """
    VIEW Layer - OPTIONAL, LOSSY

    User-declared filtering for visualization/UI purposes.
    NOT used for identity, hashing, or DEX packaging.

    Available filters:
    - trim_whitespace: Remove trailing whitespace from lines
    - remove_zero_impact: Remove changes where before == after
    - remove_empty_files: Remove files with no changes after filtering
    """
    if filters is None:
        filters = {}

    # Start with canonical form
    canonical = normalize_to_dennis_diff_v1(diff_artifact)
    payload = canonical.get('payload', {})
    files = payload.get('files', [])

    filtered_files = []

    for file_info in files:
        changes = file_info.get('changes', [])

        filtered_changes = []
        for change in changes:
            # Deep copy to prevent mutation of nested structures
            filtered_change = copy.deepcopy(change)
            before_lines = filtered_change['before']
            after_lines = filtered_change['after']

            # Apply optional filters
            if filters.get('trim_whitespace', False):
                before_lines = [line.rstrip() for line in before_lines]
                after_lines = [line.rstrip() for line in after_lines]

            # Update change with filtered content
            filtered_change['before'] = before_lines
            filtered_change['after'] = after_lines

            # Optional: remove zero-impact changes
            if filters.get('remove_zero_impact', False):
                if before_lines == after_lines:
                    continue

            filtered_changes.append(filtered_change)

        # Optional: remove files with no changes
        if filtered_changes or not filters.get('remove_empty_files', False):
            # Deep copy to prevent mutation
            file_info_copy = copy.deepcopy(file_info)
            file_info_copy['changes'] = filtered_changes
            filtered_files.append(file_info_copy)

    return {
        'type': DIFF_SCHEMA_TYPE,
        'payload': {
            'files': filtered_files
        }
    }


def diff_hash(diff_artifact: Dict[str, Any]) -> str:
    """
    DIFF IDENTITY - Exact Definition

    diff_hash = sha256(canonical_json(normalize(diff)))

    CRITICAL: Hash MUST enforce canonicalization internally.
    This ensures consistent hashes even if caller passes non-canonical diff.

    Where:
    - canonical_json uses CANONICAL JSON RULES
    - ONLY canonical diff (not view)
    - INCLUDES "type": "dennis.diff.v1" for versioning
    - No metadata outside payload is included
    """
    # ENFORCE canonicalization - do not assume caller normalized
    canonical_diff = normalize_to_dennis_diff_v1(diff_artifact)
    canonical_json_str = canonical_json(canonical_diff)
    return hashlib.sha256(canonical_json_str.encode('utf-8')).hexdigest()


def generate_observed_diff_git() -> Dict[str, Any]:
    """
    Generate observed diff from git diff.
    """
    try:
        result = subprocess.run(
            ['git', 'diff', '--no-color', '--patch'],
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )

        if result.returncode != 0:
            raise RuntimeError(f"Git diff failed: {result.stderr}")

        diff_text = result.stdout
        if not diff_text.strip():
            return normalize_to_dennis_diff_v1({
                'type': DIFF_SCHEMA_TYPE,
                'payload': {'files': []}
            })

        artifact = parse_git_diff_to_canonical(diff_text)
        return normalize_to_dennis_diff_v1(artifact)

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to get git diff: {e}")


def parse_git_diff_to_canonical(diff_text: str) -> Dict[str, Any]:
    """
    Parse git diff output into canonical dennis.diff.v1 format.
    """
    files: List[Dict[str, Any]] = []
    current_file = None
    current_changes = []

    lines = diff_text.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i]

        if line.startswith('diff --git'):
            # Save previous file if exists
            if current_file:
                current_file['changes'] = current_changes
                files.append(current_file)

            # Parse new file
            parts = line.split()
            if len(parts) >= 3:
                path = parts[2][2:]  # Remove 'a/' prefix
                file_path = Path(path)

                if should_ignore_file(file_path):
                    current_file = None
                    current_changes = []
                    i += 1
                    continue

                # Determine status from diff
                status = 'modified'  # Default
                # Look ahead for file status
                j = i + 1
                while j < len(lines) and not lines[j].startswith('diff --git'):
                    if lines[j].startswith('new file mode'):
                        status = 'added'
                        break
                    elif lines[j].startswith('deleted file mode'):
                        status = 'removed'
                        break
                    j += 1

                current_file = {
                    'path': path,
                    'status': status,
                    'changes': []
                }
                current_changes = []

        elif line.startswith('@@'):
            # Parse hunk header
            # @@ -start,len +start,len @@
            parts = line.split()
            if len(parts) >= 3:
                old_info = parts[1][1:]  # Remove '-'
                new_info = parts[2][1:]  # Remove '+'

                old_start, old_len = (old_info.split(',') + ['1'])[:2]
                new_start, new_len = (new_info.split(',') + ['1'])[:2]

                old_start = int(old_start)
                new_start = int(new_start)
                old_len = int(old_len)
                new_len = int(new_len)

                # Collect lines for this hunk
                old_lines = []
                new_lines = []
                j = i + 1

                while j < len(lines) and not lines[j].startswith('@@') and not lines[j].startswith('diff --git'):
                    if lines[j].startswith('-'):
                        old_lines.append(lines[j][1:])
                    elif lines[j].startswith('+'):
                        new_lines.append(lines[j][1:])
                    elif lines[j].startswith(' '):
                        old_lines.append(lines[j][1:])
                        new_lines.append(lines[j][1:])
                    j += 1

                # Group into blocks
                blocks = group_changes_into_blocks(old_lines, new_lines)

                # Adjust line numbers
                for block in blocks:
                    block['start_line'] += old_start - 1
                    block['end_line'] += old_start - 1

                current_changes.extend(blocks)
                i = j - 1

        i += 1

    # Save last file
    if current_file:
        current_file['changes'] = current_changes
        files.append(current_file)

    return {
        'type': DIFF_SCHEMA_TYPE,
        'payload': {
            'files': files
        }
    }

def generate_observed_diff_directories(
        source_dir: Path,
        target_dir: Path,
        verbose: bool = False
    ) -> Dict[str, Any]:
    """
    Generate observed diff by comparing two directories.

    If source_dir is a git repository, compares git-tracked files + additions.
    Otherwise, scans all files in the target directory.
    """

    files = []

    # --------------------------------------------------
    # 1. DETERMINE FILE SCOPE
    # --------------------------------------------------

    file_paths = set()

    if is_git_repo(source_dir):
        try:
            tracked_files = get_git_tracked_files(source_dir)
            file_paths = set(Path(p) for p in tracked_files)
            if verbose:
                # print(f"[DEBUG] total file_paths: {len(file_paths)}")

            # include new files from target_dir
            for f in target_dir.rglob('*'):
                if not f.is_file():
                    continue

                rel = f.relative_to(target_dir)
                if not (source_dir / rel).exists():
                    file_paths.add(rel)

            print(f"[Dennis] Using git-tracked files + additions ({len(file_paths)} files)")

        except Exception:
            file_paths = {
                f.relative_to(target_dir)
                for f in target_dir.rglob('*') if f.is_file()
            }
            print(f"[Dennis] Git detected but failed, scanning full directory ({len(file_paths)} files)")
    else:
        file_paths = {
            f.relative_to(target_dir)
            for f in target_dir.rglob('*') if f.is_file()
        }

        print(f"[Dennis] No git repo detected, scanning full directory ({len(file_paths)} files)")

    # deterministic ordering
    file_paths = sorted(file_paths)

    # --------------------------------------------------
    # 2. PROCESS FILES (added / modified)
    # --------------------------------------------------

    for rel_path in file_paths:
        if verbose:
            # print(f"[DEBUG] checking: {rel_path}")
        if should_ignore_file(rel_path):
            if verbose:
                print(f"[SKIP ignore] {rel_path}")
            continue

        source_file = source_dir / rel_path
        target_file = target_dir / rel_path

        # skip binary files early
        if target_file.exists() and is_binary_file(target_file):
            if verbose:
                print(f"[SKIP binary target] {rel_path}")
            continue
        if source_file.exists() and is_binary_file(source_file):
            if verbose:
                print(f"[SKIP binary source] {rel_path}")
            continue

        # ------------------------
        # ADDED FILE
        # ------------------------
        if not source_file.exists() and target_file.exists():
            try:
                with open(target_file, 'rb') as f:
                    content = normalize_encoding(f.read())
                lines = content.splitlines()

                if not lines:
                    if verbose:
                        print(f"[SKIP empty] {rel_path}")   
                    continue

                files.append({
                    'path': rel_path.as_posix(),
                    'status': 'added',
                    'changes': [{
                        'type': 'insert',
                        'start_line': 1,
                        'end_line': len(lines),
                        'before': [],
                        'after': lines
                    }]
                })

            except Exception as e:
                if verbose:
                    print(f"[ERROR] {rel_path}: {e}")
                continue

        # ------------------------
        # MODIFIED FILE
        # ------------------------
        elif source_file.exists() and target_file.exists():
            try:
                with open(source_file, 'rb') as f:
                    source_content = normalize_encoding(f.read())
                with open(target_file, 'rb') as f:
                    target_content = normalize_encoding(f.read())

                source_lines = source_content.splitlines()
                target_lines = target_content.splitlines()

                changes = group_changes_into_blocks(source_lines, target_lines)

                if changes:
                    files.append({
                        'path': rel_path.as_posix(),
                        'status': 'modified',
                        'changes': changes
                    })

            except Exception:
                continue

    # --------------------------------------------------
    # 3. REMOVED FILES
    # --------------------------------------------------

    for rel_path in file_paths:

        if should_ignore_file(rel_path):
            continue

        source_file = source_dir / rel_path
        target_file = target_dir / rel_path

        # skip binary
        if source_file.exists() and is_binary_file(source_file):
            continue

        if source_file.exists() and not target_file.exists():
            try:
                with open(source_file, 'rb') as f:
                    content = normalize_encoding(f.read())
                lines = content.splitlines()

                if not lines:
                    continue

                files.append({
                    'path': rel_path.as_posix(),
                    'status': 'removed',
                    'changes': [{
                        'type': 'delete',
                        'start_line': 1,
                        'end_line': len(lines),
                        'before': lines,
                        'after': []
                    }]
                })

            except Exception:
                continue

    # --------------------------------------------------
    # 4. FINALIZE (deterministic)
    # --------------------------------------------------

    files = sorted(files, key=lambda x: x['path'])

    artifact = {
        'type': DIFF_SCHEMA_TYPE,
        'payload': {
            'files': files
        }
    }

    return normalize_to_dennis_diff_v1(artifact)


def normalize_plan_path(file_path_str: str, base_dir: Path) -> Path:
    """
    PLAN PATH NORMALIZATION - Resolves plan paths against source snapshot.

    This attempts to load the file from the source snapshot directory. If the
    path exists directly under base_dir, it is returned unchanged. Otherwise,
    this looks for a reasonable project root subdirectory and preserves the
    original path when the snapshot root already contains the file.

    Args:
        file_path_str: File path from plan
        base_dir: Project snapshot directory (e.g., hello-dennis_before/)

    Returns:
        Normalized Path that can be safely joined with base_dir
    """
    p = Path(file_path_str)
    direct_path = base_dir / p

    if direct_path.exists():
        return p

    try:
        # Search for a likely project root subdirectory containing the file path.
        for subdir in sorted(base_dir.iterdir()):
            if not subdir.is_dir():
                continue

            if subdir.name in {"payload", "helpers", ".git", "__pycache__"}:
                continue

            candidate = subdir / p
            if candidate.exists():
                return Path(subdir.name) / p
    except (OSError, StopIteration):
        pass

    # Fallback: return the original relative path.
    return p


def generate_planned_diff(plan_data: Dict[str, Any], base_dir: Path) -> Dict[str, Any]:
    """
    Generate planned diff from Dennis plan data.
    Converts plan changes to canonical diff format by:
    1. Loading actual file state from source snapshot (base_dir)
    2. Applying planned changes to reconstruct modified state
    3. Normalizing lines before diffing (encoding consistency)
    4. Generating explicit add/delete blocks for file-level changes
    5. Using canonical group_changes_into_blocks for modifications
    
    CRITICAL: base_dir MUST be the source snapshot directory, not current disk.
    This ensures circularity: plan diff == observed diff (same content)
    
    Args:
        plan_data: Plan artifact with changes
        base_dir: Source snapshot directory (required - original state before plan)
    
    Returns:
        Canonical dennis.diff.v1 artifact
    
    Raises:
        ValueError: If base_dir is None (source snapshot required for correctness)
    """
    if base_dir is None:
        raise ValueError("generate_planned_diff requires base_dir (source snapshot)")
    
    base_dir = Path(base_dir)
    
    def load_file_lines(file_path: Path) -> List[str]:
        """Load file lines from source snapshot, return empty list if not found."""
        try:
            full_path = base_dir / file_path
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read().splitlines()
        except FileNotFoundError:
            return []
    
    def load_helper_lines(change: Dict[str, Any]) -> List[str]:
        """Load helper file lines from deterministic helper sources."""
        helper_ref = change.get("helper_ref") or change.get("helper")
        helper_source = change.get("helper_source")

        candidates = []
        if helper_ref:
            candidates.append(base_dir / helper_ref)
            candidates.append(base_dir / "payload" / helper_ref)
        if helper_source:
            candidates.append(base_dir / helper_source)
            candidates.append(Path(helper_source))

        for candidate in candidates:
            if not candidate:
                continue
            try:
                if candidate.exists() and candidate.is_file():
                    return candidate.read_text(encoding="utf-8").splitlines()
            except Exception:
                continue

        return []

    def file_exists_in_source(file_path: Path) -> bool:
        """Check if file exists in source snapshot."""
        return (base_dir / file_path).exists()

    files = {}
    
    # Group changes by file path
    changes_by_file: Dict[str, List[Dict[str, Any]]] = {}
    for change in plan_data.get("changes", []):
        file_path = change.get("file")
        if not file_path:
            continue
        
        if file_path not in changes_by_file:
            changes_by_file[file_path] = []
        
        changes_by_file[file_path].append(change)
    
    # Process each file
    for file_path_str in sorted(changes_by_file.keys()):
        # NORMALIZE PATH: Strip project root prefix if present
        file_path = normalize_plan_path(file_path_str, base_dir)
        file_changes = changes_by_file[file_path_str]
        
        # Load original state from source snapshot
        original_lines = load_file_lines(file_path)
        modified_lines = original_lines.copy()
        
        # Apply plan changes to reconstruct modified state
        sorted_changes = sorted(file_changes, key=lambda c: c.get("line", 1))
        
        for change in sorted_changes:
            change_type = change.get("type", "replace")
            line_num = change.get("line", 1)
            idx = line_num - 1
            
            if change_type == "helper":
                # Load and insert helper content using the same helper wrapper as apply()
                helper_lines = load_helper_lines(change)
                helper_id = change.get("helper_id") or change.get("id") or Path(change.get("helper_ref", "")).stem
                if helper_lines:
                    wrapped = [
                        f"# >>> DENNIS HELPER START: {helper_id}",
                        *helper_lines,
                        f"# <<< DENNIS HELPER END: {helper_id}",
                    ]
                    insert_point = max(0, idx)
                    for i, helper_line in enumerate(wrapped):
                        modified_lines.insert(insert_point + i, helper_line)
            else:
                # Standard replacement by content, not raw index, to match runtime apply semantics.
                original_text = change.get("original", "").strip()
                replacement = change.get("replacement", "")
                normalized_lines = [line.strip() for line in modified_lines]
                match_index = None

                if 0 <= idx < len(modified_lines) and normalized_lines[idx] == original_text:
                    match_index = idx
                else:
                    candidates = [i for i, line in enumerate(normalized_lines) if line == original_text]
                    if candidates:
                        match_index = candidates[0]

                if match_index is not None:
                    if modified_lines[match_index] != replacement:
                        modified_lines[match_index] = replacement
                elif idx == len(modified_lines):
                    modified_lines.append(replacement)
        
        # Normalize lines BEFORE diffing (encoding consistency)
        # This ensures plan and observed diffs have identical content representation
        original_lines = [normalize_line(l) for l in original_lines]
        modified_lines = [normalize_line(l) for l in modified_lines]
        
        # Determine file status based on actual existence in source
        file_existed_before = file_exists_in_source(file_path)
        
        # Generate diff blocks (explicit add/delete cases, then modified)
        if not file_existed_before and modified_lines:
            # File added: explicit full-file insert block
            status = "added"
            diff_blocks = [{
                'type': 'insert',
                'start_line': 1,
                'end_line': len(modified_lines),
                'before': [],
                'after': modified_lines
            }]
        elif file_existed_before and not modified_lines:
            # File removed: explicit full-file delete block
            status = "removed"
            diff_blocks = [{
                'type': 'delete',
                'start_line': 1,
                'end_line': len(original_lines),
                'before': original_lines,
                'after': []
            }]
        else:
            # File modified: use canonical diff engine
            status = "modified"
            diff_blocks = group_changes_into_blocks(original_lines, modified_lines)
        
        # Only include files with actual changes
        if diff_blocks:
            files[file_path_str] = {
                "path": file_path_str,
                "status": status,
                "changes": diff_blocks
            }

    # --------------------------------------------------
    # Add helper file creations as explicit file additions
    # --------------------------------------------------
    helper_refs: Dict[str, Optional[str]] = {}
    for change in plan_data.get("changes", []):
        if change.get("type") != "helper":
            continue

        helper_ref = change.get("helper_ref")
        if not helper_ref:
            continue

        helper_refs.setdefault(helper_ref, change.get("helper_source"))

    for helper_ref, helper_source in sorted(helper_refs.items()):
        if helper_ref in files:
            continue

        helper_lines = load_helper_lines({
            "helper_ref": helper_ref,
            "helper_source": helper_source
        })

        if not helper_lines:
            continue

        files[helper_ref] = {
            "path": helper_ref,
            "status": "added",
            "changes": [{
                'type': 'insert',
                'start_line': 1,
                'end_line': len(helper_lines),
                'before': [],
                'after': helper_lines
            }]
        }

    # Build and normalize artifact
    artifact = {
        'type': DIFF_SCHEMA_TYPE,
        'payload': {
            'files': list(files.values())
        }
    }
    
    return normalize_to_dennis_diff_v1(artifact)


def generate_reconciliation_diff(planned_diff: Dict[str, Any], observed_diff: Dict[str, Any]) -> Dict[str, Any]:
    """
    RECONCILIATION MATCHING - Deterministic Content-Based

    MATCHING RULE:
    Two changes match if:
    1. same file path
    2. identical "before" content
    3. identical "after" content

    Line position:
    - ignored for identity
    - used only as heuristic tie-breaker

    STABLE MATCHING (handles duplicates):
    - Match in order of appearance
    - First unmatched planned → first unmatched observed
    """
    # Ensure both are in canonical form
    planned_norm = normalize_to_dennis_diff_v1(planned_diff)
    observed_norm = normalize_to_dennis_diff_v1(observed_diff)

    reconciliation_files = []

    # Index changes by content signature (ignoring line position)
    def index_changes_by_content(diff_artifact):
        index = {}
        for file_info in diff_artifact['payload']['files']:
            file_path = file_info['path']
            if file_path not in index:
                index[file_path] = {}

            for change in file_info['changes']:
                # Content signature: (type, before_content, after_content)
                # Line position is metadata, not identity
                content_sig = (
                    change['type'],
                    tuple(change['before']),
                    tuple(change['after'])
                )

                # Store change with its line position for reference
                if content_sig not in index[file_path]:
                    index[file_path][content_sig] = []

                index[file_path][content_sig].append({
                    'change': change,
                    'line_position': change['start_line']
                })

        return index

    planned_index = index_changes_by_content(planned_norm)
    observed_index = index_changes_by_content(observed_norm)

    # Get all files from both diffs
    all_files = set(planned_index.keys()) | set(observed_index.keys())

    for file_path in sorted(all_files):
        planned_changes = planned_index.get(file_path, {})
        observed_changes = observed_index.get(file_path, {})

        matched = []
        missing = []
        unexpected = []

        # STABLE MATCHING: Process in deterministic order
        # Get all unique content signatures from planned changes
        planned_sigs = list(planned_changes.keys())

        for content_sig in planned_sigs:
            planned_instances = planned_changes[content_sig]
            observed_instances = observed_changes.get(content_sig, [])

            # Match instances in order of appearance
            for planned_instance in planned_instances:
                if observed_instances:
                    # Match with first available observed instance
                    observed_instance = observed_instances.pop(0)

                    # Create matched change with line position info
                    matched_change = planned_instance['change'].copy()
                    matched_change['reconciliation_type'] = 'matched'
                    matched_change['planned_line'] = planned_instance['line_position']
                    matched_change['observed_line'] = observed_instance['line_position']

                    matched.append(matched_change)
                else:
                    # No more observed instances - this planned change is missing
                    missing_change = planned_instance['change'].copy()
                    missing_change['reconciliation_type'] = 'missing'
                    missing_change['planned_line'] = planned_instance['line_position']
                    missing.append(missing_change)

        # Find unexpected changes (observed but not planned)
        for content_sig, observed_instances in observed_changes.items():
            for observed_instance in observed_instances:
                unexpected_change = observed_instance['change'].copy()
                unexpected_change['reconciliation_type'] = 'unexpected'
                unexpected_change['observed_line'] = observed_instance['line_position']
                unexpected.append(unexpected_change)

        # Only include files with reconciliation data
        if matched or missing or unexpected:
            reconciliation_files.append({
                'path': file_path,
                'status': 'reconciled',
                'changes': matched + missing + unexpected,
                'reconciliation': {
                    'matched': len(matched),
                    'missing': len(missing),
                    'unexpected': len(unexpected)
                }
            })

    return {
        'type': DIFF_SCHEMA_TYPE,
        'payload': {
            'files': reconciliation_files,
            'reconciliation_summary': {
                'total_files': len(reconciliation_files),
                'matched_changes': sum(f['reconciliation']['matched'] for f in reconciliation_files),
                'missing_changes': sum(f['reconciliation']['missing'] for f in reconciliation_files),
                'unexpected_changes': sum(f['reconciliation']['unexpected'] for f in reconciliation_files)
            }
        }
    }


def validate_diff_artifact(artifact: Dict[str, Any]) -> bool:
    """
    Validate that an artifact conforms to dennis.diff.v1 schema.
    """
    if not isinstance(artifact, dict):
        return False

    if artifact.get('type') != DIFF_SCHEMA_TYPE:
        return False

    payload = artifact.get('payload')
    if not isinstance(payload, dict):
        return False

    files = payload.get('files')
    if not isinstance(files, list):
        return False

    # Basic validation of file structure
    for file_info in files:
        if not isinstance(file_info, dict):
            return False

        required_keys = {'path', 'status', 'changes'}
        if not all(key in file_info for key in required_keys):
            return False

        if file_info['status'] not in {'added', 'removed', 'modified', 'reconciled'}:
            return False

        if not isinstance(file_info['changes'], list):
            return False

        for change in file_info['changes']:
            if not isinstance(change, dict):
                return False

            if change.get('type') not in {'insert', 'delete', 'replace'}:
                return False

            if not all(isinstance(change.get(k), int) for k in ['start_line', 'end_line']):
                return False

            if not all(isinstance(change.get(k), list) for k in ['before', 'after']):
                return False

    return True


def test_determinism() -> Dict[str, Any]:
    """
    COMPREHENSIVE DETERMINISM TESTING

    Tests:
    1. Idempotency: normalize(normalize(x)) == normalize(x)
    2. Cross-input determinism: Different raw inputs → Same canonical output
    3. Hash stability: Same canonical form → Same hash
    4. Minimal invariant: No structural redundancy
    5. Block determinism: Adjacent changes merged correctly

    DETERMINISM RULE:
    Any two inputs representing the same transformation MUST produce identical canonical diffs.
    """
    results = {
        'idempotency': False,
        'cross_input_determinism': False,
        'hash_stability': False,
        'minimal_invariant': False,
        'block_determinism': False,
        'details': []
    }

    # Test 1: Idempotency
    try:
        test_diff = {
            'type': DIFF_SCHEMA_TYPE,
            'payload': {
                'files': [{
                    'path': 'test.py',
                    'status': 'modified',
                    'changes': [{
                        'type': 'replace',
                        'start_line': 1,
                        'end_line': 1,
                        'before': ['hello'],
                        'after': ['hola']
                    }]
                }]
            }
        }

        once = normalize_to_dennis_diff_v1(test_diff)
        twice = normalize_to_dennis_diff_v1(once)

        if once == twice:
            results['idempotency'] = True
            results['details'].append("✓ Idempotency: normalize(normalize(x)) == normalize(x)")
        else:
            results['details'].append("✗ Idempotency failed")

    except Exception as e:
        results['details'].append(f"✗ Idempotency test error: {e}")

    # Test 2: Cross-input determinism (file ordering)
    try:
        input1 = {
            'type': DIFF_SCHEMA_TYPE,
            'payload': {
                'files': [{
                    'path': 'a.py',
                    'status': 'modified',
                    'changes': [{
                        'type': 'replace',
                        'start_line': 5,
                        'end_line': 5,
                        'before': ['print("hello")'],
                        'after': ['print("hola")']
                    }]
                }, {
                    'path': 'b.py',
                    'status': 'modified',
                    'changes': [{
                        'type': 'replace',
                        'start_line': 1,
                        'end_line': 1,
                        'before': ['x = 1'],
                        'after': ['x = 2']
                    }]
                }]
            }
        }

        # Same content, different file order
        input2 = {
            'type': DIFF_SCHEMA_TYPE,
            'payload': {
                'files': [{
                    'path': 'b.py',  # Different order
                    'status': 'modified',
                    'changes': [{
                        'type': 'replace',
                        'start_line': 1,
                        'end_line': 1,
                        'before': ['x = 1'],
                        'after': ['x = 2']
                    }]
                }, {
                    'path': 'a.py',  # Different order
                    'status': 'modified',
                    'changes': [{
                        'type': 'replace',
                        'start_line': 5,
                        'end_line': 5,
                        'before': ['print("hello")'],
                        'after': ['print("hola")']
                    }]
                }]
            }
        }

        canonical1 = normalize_to_dennis_diff_v1(input1)
        canonical2 = normalize_to_dennis_diff_v1(input2)

        if canonical1 == canonical2:
            results['cross_input_determinism'] = True
            results['details'].append("✓ Cross-input determinism: Different file orders → Same canonical form")
        else:
            results['details'].append("✗ Cross-input determinism failed")

    except Exception as e:
        results['details'].append(f"✗ Cross-input determinism test error: {e}")

    # Test 3: Hash stability
    try:
        test_diff = {
            'type': DIFF_SCHEMA_TYPE,
            'payload': {
                'files': [{
                    'path': 'test.py',
                    'status': 'modified',
                    'changes': [{
                        'type': 'replace',
                        'start_line': 1,
                        'end_line': 1,
                        'before': ['hello'],
                        'after': ['hola']
                    }]
                }]
            }
        }

        canonical = normalize_to_dennis_diff_v1(test_diff)
        hash1 = diff_hash(canonical)
        hash2 = diff_hash(canonical)

        if hash1 == hash2 and len(hash1) == 64:  # SHA256 hex length
            results['hash_stability'] = True
            results['details'].append(f"✓ Hash stability: {hash1[:16]}...")
        else:
            results['details'].append("✗ Hash stability failed")

    except Exception as e:
        results['details'].append(f"✗ Hash stability test error: {e}")

    # Test 4: Minimal invariant
    try:
        # Test diff with empty changes and empty files
        test_diff = {
            'type': DIFF_SCHEMA_TYPE,
            'payload': {
                'files': [{
                    'path': 'empty.py',
                    'status': 'modified',
                    'changes': []  # Empty file
                }, {
                    'path': 'redundant.py',
                    'status': 'modified',
                    'changes': [{
                        'type': 'replace',
                        'start_line': 1,
                        'end_line': 1,
                        'before': [],  # Empty change
                        'after': []
                    }, {
                        'type': 'replace',
                        'start_line': 2,
                        'end_line': 2,
                        'before': ['hello'],
                        'after': ['hola']  # Valid change
                    }]
                }]
            }
        }

        canonical = normalize_to_dennis_diff_v1(test_diff)

        # Should only have the valid change, empty file removed
        if (len(canonical['payload']['files']) == 1 and
            canonical['payload']['files'][0]['path'] == 'redundant.py' and
            len(canonical['payload']['files'][0]['changes']) == 1):
            results['minimal_invariant'] = True
            results['details'].append("✓ Minimal invariant: Empty changes/files removed")
        else:
            results['details'].append("✗ Minimal invariant failed")

    except Exception as e:
        results['details'].append(f"✗ Minimal invariant test error: {e}")

    # Test 5: Block determinism (adjacent changes merged)
    try:
        # Test adjacent changes that should be merged
        lines_a = ['line1', 'line2', 'line3', 'line4']
        lines_b = ['line1', 'changed2', 'changed3', 'line4']

        blocks = group_changes_into_blocks(lines_a, lines_b)

        # Should be one block (lines 2-3 changed, adjacent)
        if (len(blocks) == 1 and
            blocks[0]['start_line'] == 2 and
            blocks[0]['end_line'] == 3 and
            blocks[0]['before'] == ['line2', 'line3'] and
            blocks[0]['after'] == ['changed2', 'changed3']):
            results['block_determinism'] = True
            results['details'].append("✓ Block determinism: Adjacent changes merged")
        else:
            results['details'].append("✗ Block determinism failed")

    except Exception as e:
        results['details'].append(f"✗ Block determinism test error: {e}")

    return results