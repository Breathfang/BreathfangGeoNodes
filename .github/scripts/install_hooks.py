#!/usr/bin/env python3
"""Install the tracked pre-push hook into .git/hooks/.

``.git/hooks`` is not version controlled, so the hook itself lives in
``.github/hooks/pre-push`` and this script copies it into place. Run it once
per clone:

    python .github/scripts/install_hooks.py

It is safe to re-run: an existing hook you did not write is never silently
overwritten, it is backed up first and you are told where.
"""

from __future__ import annotations

import argparse
import os
import shutil
import stat
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent

if str(_SCRIPT_DIR) not in sys.path:  # importable from any working directory
    sys.path.insert(0, str(_SCRIPT_DIR))

from functions import scan_utils  # noqa: E402

HOOK_NAME = "pre-push"
SOURCE = _SCRIPT_DIR.parent / "hooks" / HOOK_NAME
MARKER = "Pre-push security scan"


def is_ours(path: Path) -> bool:
    try:
        return MARKER in path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False


def has_crlf(path: Path) -> bool:
    """True when the file contains Windows line endings.

    A CRLF shebang makes bash abort with "bad interpreter: ...bash^M", which is
    the single most common reason this hook appears to do nothing. .gitattributes
    pins the file to LF in the repository, but a checkout made before that rule
    existed, or a manual copy, can still be CRLF.
    """
    try:
        data = path.read_bytes()
    except OSError:
        return False
    return b"\r\n" in data


def make_executable(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install the pre-push security hook.")
    parser.add_argument("--repo", default=".", help="Repository root (default: auto-detect)")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing hook that this project did not write.",
    )
    args = parser.parse_args(argv)

    if not SOURCE.is_file():
        print(f"[install-hooks] missing hook source: {SOURCE}", file=sys.stderr)
        return 2

    if has_crlf(SOURCE):
        print(
            f"[install-hooks] FATAL: {SOURCE} has Windows (CRLF) line endings.\n"
            f"[install-hooks] bash cannot run a CRLF shebang, so the hook would\n"
            f"[install-hooks] fail silently on every push. Fix it with:\n"
            f"[install-hooks]     git add --renormalize .gitattributes\n"
            f"[install-hooks]     git checkout -- .github/hooks/pre-push\n"
            f"[install-hooks] then run this script again.",
            file=sys.stderr,
        )
        return 2

    repo = scan_utils.resolve_repo(args.repo)
    if not scan_utils.is_git_repo(repo):
        print(f"[install-hooks] not a git repository: {repo}", file=sys.stderr)
        return 2

    hooks_dir = repo / ".git" / "hooks"
    if not hooks_dir.is_dir():
        print(
            f"[install-hooks] {hooks_dir} does not exist. This happens with a "
            f"worktree or a custom GIT_DIR; copy {SOURCE} to your hooks "
            f"directory manually.",
            file=sys.stderr,
        )
        return 2
    hooks_dir.mkdir(parents=True, exist_ok=True)

    target = hooks_dir / HOOK_NAME
    if target.exists() and not is_ours(target) and not args.force:
        backup = target.with_name(f"{HOOK_NAME}.backup")
        counter = 1
        while backup.exists():
            backup = target.with_name(f"{HOOK_NAME}.backup.{counter}")
            counter += 1
        shutil.copy2(target, backup)
        print(f"[install-hooks] existing hook backed up to {backup.name}")

    shutil.copy2(SOURCE, target)
    make_executable(target)

    if os.name == "nt":
        # Windows has no exec bit; Git for Windows runs hooks through its
        # bundled bash whenever the shebang is present, which it now is.
        print("[install-hooks] note: on Windows the executable bit is not stored;")
        print("[install-hooks]       Git for Windows runs this through its own bash.")

    print(f"[install-hooks] installed {target}")
    print("[install-hooks] it will run on your next 'git push'.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except KeyboardInterrupt:
        print("[install-hooks] interrupted.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:  # unexpected crash -> fail closed
        print(f"[install-hooks] unexpected crash: {exc!r}", file=sys.stderr)
        raise SystemExit(2)
