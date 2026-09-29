#!/usr/bin/env python3
"""Interactive temporary-file cleaner for the "Breathfang's Nodes" repository.

Scans the repository root for temporary/leftover files and, after listing them
in pages of ``CLEANER_PAGE_SIZE`` and showing a final preview, deletes them on
an explicit "Y". The suffix policy, the page size and the repository anchor
come from the single ``.env`` in this folder, read through ``functions/``.

Safety:
  - The search is rooted at the repository root, so it can never go above
    "Breathfang's Nodes".
  - Every candidate is re-validated to still be inside the repository root just
    before deletion; anything outside (or a symlink, or a .git entry) is skipped.
  - Nothing is deleted without an explicit confirmation (preview first).

Temporary-file policy (the same suffixes that are excluded from the toolset
packs, minus .md):
  - *.log, *.tmp
  - Editor backups: '*~' (e.g. blender_assets.cats.txt~), '*.orig', '*.rej'
  - Blender autosaves: '*.blend1' .. '*.blend9'

Exit codes: 0 = finished (deleted or aborted), 2 = bad environment, 130 = interrupted.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:  # importable from any working directory
    sys.path.insert(0, str(_SCRIPT_DIR))

from functions import env_utils, log_utils, path_utils, prompt_utils  # noqa: E402

REPO_ROOT = path_utils.repo_root()

PAGE_SIZE = env_utils.get_int("CLEANER_PAGE_SIZE", 10)  # entries per page in the listing
TEMP_SUFFIXES = env_utils.get_suffixes(
    "CLEANER_SUFFIXES",
    (".log", ".tmp", "~", ".orig", ".rej")
    + tuple(f".blend{index}" for index in range(1, 10)),
)

fmt_size = log_utils.fmt_size


def rel(path: Path) -> str:
    """Short repository-relative display path."""
    return path_utils.display(path)


def collect_candidates() -> list[Path]:
    """Every temporary file below the repo root, excluding .git and symlinks."""
    candidates: list[Path] = []
    for path in REPO_ROOT.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        try:
            rel_parts = path.relative_to(REPO_ROOT).parts
        except ValueError:
            continue  # outside the repo root: never a candidate
        if rel_parts and rel_parts[0] == ".git":
            continue  # never touch the git directory
        if path.name.lower().endswith(TEMP_SUFFIXES):
            candidates.append(path)
    return sorted(candidates, key=rel)


def total_size(candidates: list[Path]) -> int:
    total = 0
    for path in candidates:
        try:
            total += path.stat().st_size
        except OSError:
            pass
    return total


def paginate(candidates: list[Path], title: str) -> None:
    """Show the entries, PAGE_SIZE per page, waiting for Enter between pages."""
    index = 0
    total = len(candidates)
    while index < total:
        chunk = candidates[index : index + PAGE_SIZE]
        end = min(index + PAGE_SIZE, total)
        header = f"{title} ({index + 1}-{end} of {total})"
        print(f"--- {header} ---")
        offset = index
        for path in chunk:
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            print(f"  [{offset:3d}] {rel(path)}  ({fmt_size(size)})")
            offset += 1
        index = end
        if index >= total:
            break
        try:
            answer = prompt_utils.prompt_read("more [Enter] / quit listing [q]: ")
        except EOFError:
            break  # no interactive input: show the rest without pausing
        if answer.lower() == "q":
            break


def delete_candidates(candidates: list[Path], dry_run: bool) -> int:
    deleted = 0
    for path in candidates:
        if not path_utils.is_inside(path, REPO_ROOT):
            print(f"  SKIP (outside repo): {path}", file=sys.stderr)
            continue
        if path.is_symlink():
            print(f"  SKIP (symlink): {rel(path)}", file=sys.stderr)
            continue
        try:
            rel_parts = path.relative_to(REPO_ROOT).parts
        except ValueError:
            print(f"  SKIP (outside repo): {rel(path)}", file=sys.stderr)
            continue
        if rel_parts and rel_parts[0] == ".git":
            print(f"  SKIP (.git entry): {rel(path)}", file=sys.stderr)
            continue
        if dry_run:
            print(f"  would delete: {rel(path)}")
        else:
            path.unlink(missing_ok=True)
            print(f"  deleted: {rel(path)}")
        deleted += 1
    return deleted


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Interactively delete temporary files below the repository root "
        "(only inside Breathfang's Nodes)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without deleting anything",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print the resolved .env settings and exit",
    )
    args = parser.parse_args(argv)

    if args.list:
        print(f"Settings: {env_utils.source_description()}")
        print(f"  REPO_ROOT = {REPO_ROOT}")
        print(f"  CLEANER_PAGE_SIZE = {PAGE_SIZE}")
        print(f"  CLEANER_SUFFIXES = {', '.join(TEMP_SUFFIXES)}")
        return 0

    if not REPO_ROOT.is_dir():
        print(f"[temp-cleaner] repository root not found: {REPO_ROOT}", file=sys.stderr)
        return 2

    candidates = collect_candidates()
    if not candidates:
        print("[temp-cleaner] nothing to clean (no temporary files found).")
        return 0

    print(
        f"[temp-cleaner] found {len(candidates)} temporary file(s) "
        f"({fmt_size(total_size(candidates))}) in {REPO_ROOT.name}"
    )
    print()

    # Step 1: list everything, PAGE_SIZE entries per page.
    paginate(candidates, "Temporary files")

    # Step 2: explicit preview right before confirmation.
    print()
    paginate(candidates, "PREVIEW - files that WILL be deleted")

    print()
    what = "would delete" if args.dry_run else "delete"
    try:
        answer = prompt_utils.prompt_read(f"{what} {len(candidates)} file(s) [y/N]: ")
    except EOFError:
        print("\n[temp-cleaner] no interactive input; aborting, nothing deleted.")
        return 0
    if answer.lower() not in ("y", "yes"):
        print("[temp-cleaner] aborted; nothing deleted.")
        return 0

    deleted = delete_candidates(candidates, dry_run=args.dry_run)
    print(
        f"[temp-cleaner] {'would delete' if args.dry_run else 'deleted'} "
        f"{deleted} file(s)."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except KeyboardInterrupt:
        print("\n[temp-cleaner] interrupted.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:
        print(f"[temp-cleaner] unexpected crash: {exc!r}; bypassed (exit 2).", file=sys.stderr)
        raise SystemExit(2)
