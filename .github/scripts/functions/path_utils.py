"""Repository-anchored path helpers for the maintainer scripts.

Every tool resolves paths against the repository root rather than the shell's
working directory, so the same command behaves identically from the repo root,
from a subfolder, from an IDE run configuration or from CI. The root is the
first ancestor of this package that contains a ``.git`` entry, which walks past
``.github/`` up to the repository root. Set ``REPO_ROOT`` in ``.env`` to pin it
explicitly.
"""

from __future__ import annotations

from pathlib import Path

from functions import env_utils

TOOL_ROOT = env_utils.TOOL_ROOT


def _discover_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return start.parent  # no .git anywhere: fall back to one level up


def repo_root() -> Path:
    """The repository root, resolved once per interpreter."""
    override = env_utils.get_str("REPO_ROOT", "")
    if override:
        candidate = Path(override).expanduser()
        if not candidate.is_absolute():
            candidate = TOOL_ROOT / candidate
        return candidate.resolve()
    return _discover_repo_root(TOOL_ROOT)


def resolve_against(base: Path, value: str | Path) -> Path:
    """Resolve ``value``; a relative path is taken relative to ``base``.

    The order matters: ``Path(value).resolve()`` would first anchor a relative
    path at the process working directory, which is not the same thing as
    ``base`` and silently breaks every --root/--output-dir passed from outside
    the repository.
    """
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def resolve_under_root(value: str | Path) -> Path:
    """Resolve ``value``; a relative path is taken relative to the repo root."""
    return resolve_against(repo_root(), value)


def is_inside(path: Path, root: Path | None = None) -> bool:
    """True only when ``path`` really resolves to something below the root."""
    base = repo_root() if root is None else root
    try:
        path.resolve().relative_to(base.resolve())
    except (OSError, ValueError):
        return False
    return True


def relative_to_root(path: Path) -> Path:
    """``path`` relative to the repo root, or the path itself when outside."""
    try:
        return path.resolve().relative_to(repo_root())
    except (OSError, ValueError):
        return path


def display(path: Path) -> str:
    """Short repository-relative, forward-slashed path for logs and prompts."""
    return relative_to_root(path).as_posix()


def inside_repo(path: Path) -> bool:
    """True when the first path part is ``.git`` (never touch the git dir)."""
    parts = relative_to_root(path).parts
    return bool(parts) and parts[0] == ".git"
