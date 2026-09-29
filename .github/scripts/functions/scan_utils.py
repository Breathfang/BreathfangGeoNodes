"""Filesystem and git plumbing shared by the two security scanners.

Both scanners walk a tree, diff it against a base commit, and read raw bytes.
The behaviour is identical for either, so it lives here: the scanners keep only
the policy that is actually specific to them.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from functions import env_utils, path_utils

# SHA-1 of git's empty tree, the safe "diff against nothing" base.
EMPTY_TREE = env_utils.get_str("EMPTY_TREE_SHA", "4b825dc642cb6eb9a060e54bf8d69288fbee4904")

GIT_TIMEOUT = env_utils.get_int("GIT_TIMEOUT", 60)
GIT_DIFF_FILTER = env_utils.get_str("GIT_DIFF_FILTER", "ACMRTUXB")

# Never walked, whatever the scan root is. The shared helpers under functions/
# are trusted maintainer tooling and legitimately use os/sys/subprocess.
DEFAULT_SKIP_DIRS = env_utils.get_list(
    "SCAN_SKIP_DIRS",
    (
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        "functions",
        "DragonGraph's Project Utilities/functions",
        ".github/scripts/functions",
    ),
)


def resolve_repo(value: str | Path = ".") -> Path:
    """Expand and resolve a ``--repo`` value against the repository root."""
    return path_utils.resolve_under_root(value)


def is_git_repo(repo: Path) -> bool:
    return repo.is_dir() and (repo / ".git").exists()


def is_binary_bytes(data: bytes) -> bool:
    """A Python source file that contains NUL bytes is bytecode, not source."""
    return b"\x00" in data


def read_bytes(path: Path) -> bytes:
    with open(path, "rb") as handle:
        return handle.read()


def run_git(repo: Path, arguments: list[str]) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ["git", "-C", str(repo), *arguments],
            capture_output=True,
            text=True,
            check=False,
            timeout=GIT_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"[git] {' '.join(arguments)} failed: {exc}", file=sys.stderr)
        return None


def git_diff_names(repo: Path, base: str, path_filter: str | None = None) -> list[str] | None:
    """Repo-relative names changed since ``base``; None when git fails."""
    arguments = ["diff", "--name-only", f"--diff-filter={GIT_DIFF_FILTER}", base]
    if path_filter:
        arguments += ["--", path_filter]
    result = run_git(repo, arguments)
    if result is None or result.returncode != 0:
        detail = (result.stderr if result else "").strip()
        print(
            f"[git] diff against {base} failed ({detail or 'git unavailable'}); "
            "falling back to a full-tree scan",
            file=sys.stderr,
        )
        return None
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def git_untracked_names(repo: Path, path_filter: str | None = None) -> list[str]:
    """Repo-relative names of files that exist on disk but are not tracked."""
    arguments = ["ls-files", "--others", "--exclude-standard"]
    if path_filter:
        arguments += ["--", path_filter]
    result = run_git(repo, arguments)
    if result is None or result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def rev_parse(repo: Path, rev: str) -> str | None:
    """Resolve ``rev`` to a commit SHA, or None when it does not exist."""
    result = run_git(repo, ["rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}"])
    if result is None or result.returncode != 0:
        return None
    sha = result.stdout.strip()
    return sha or None


def resolve_scan_base(repo: Path) -> str | None:
    """Pick the commit a change-only scan should diff against.

    A change-only scan is only as trustworthy as its base: diff against
    something too recent and a payload committed earlier is never re-checked.
    The base is therefore the newest commit reachable from the repository's
    remote-tracking default branch, i.e. the newest work that has already been
    published, so everything not yet published is what gets scanned.

    Returns None when no published commit can be found (a fresh clone with no
    remote, or a detached CI checkout). Callers must treat None as "scan
    everything" rather than "scan nothing", so a missing base degrades to the
    slower, stricter full-tree scan instead of silently passing.
    """
    # Ordered by trustworthiness. A remote-tracking ref is published work, so it
    # is preferred; the local default branch is a weaker fallback that is still
    # real history rather than a guess.
    for candidate in ("@{upstream}", "origin/HEAD", "origin/main", "origin/master"):
        sha = rev_parse(repo, candidate)
        if sha is not None:
            return sha
    return None


def is_skipped(rel_parts: tuple[str, ...], skip_dirs: tuple[str, ...]) -> bool:
    """True when any path part is a skip directory."""
    return any(part in skip_dirs for part in rel_parts)


def walk_files(repo: Path, root: Path, suffix: str, skip_dirs: tuple[str, ...]) -> list[str]:
    """Repo-relative paths of every ``suffix`` file under ``root``, sorted."""
    found: list[str] = []
    for path in root.rglob(f"*{suffix}"):
        if path.is_symlink() or not path.is_file():
            continue
        try:
            rel = path.relative_to(repo)
        except ValueError:
            continue
        if is_skipped(rel.parts, skip_dirs):
            continue
        found.append(rel.as_posix())
    return sorted(found)
