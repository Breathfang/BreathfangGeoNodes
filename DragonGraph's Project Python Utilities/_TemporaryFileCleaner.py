#!/usr/bin/env python3
"""Interactive temporary-file cleaner for the "Breathfang's Nodes" repository.

Scans the repository root for temporary/leftover files and, after listing them
in pages of 10 and showing a final preview, deletes them on an explicit "Y".

Safety:
  - The search is rooted at the repository root (parent of this script's
    directory), so it can never go above "Breathfang's Nodes".
  - Every candidate is re-validated to still be inside the repository root just
    before deletion; anything outside (or a symlink, or a .git entry) is skipped.
  - Nothing is deleted without an explicit confirmation (preview first).

Temporary-file policy (same suffixes that are excluded from the toolset packs):
  - *.log, *.tmp
  - Editor backups: '*~' (e.g. blender_assets.cats.txt~), '*.orig', '*.rej'
  - Blender autosaves: '*.blend1' .. '*.blend9'

Exit codes: 0 = finished (deleted or aborted), 130 = interrupted.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = _SCRIPT_DIR.parent

PAGE_SIZE = 10  # entries shown per page in the CLI listing

# Same suffix policy shared with the ZIP builders.
BLEND_AUTOSAVE_SUFFIXES = tuple(f".blend{d}" for d in range(1, 10))  # .blend1..9
TEMP_SUFFIXES = (".log", ".tmp", "~", ".orig", ".rej") + BLEND_AUTOSAVE_SUFFIXES


def prompt_read(prompt_text: str) -> str:
    """Print a prompt, flush it, then read one line from the user."""
    sys.stdout.write(prompt_text)
    sys.stdout.flush()
    return input().strip()


def fmt_size(num_bytes: int) -> str:
    """Format a byte count into a short human-readable string."""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KiB"
    return f"{num_bytes / (1024 * 1024):.1f} MiB"


def is_inside_repo(path: Path) -> bool:
    """True only when the resolved path is really below the repository root."""
    try:
        resolved = path.resolve()
    except OSError:
        return False
    try:
        resolved.relative_to(REPO_ROOT)
    except ValueError:
        return False
    return True


def rel(path: Path) -> str:
    """Short repository-relative display path."""
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except (OSError, ValueError):
        return str(path)


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
    return sorted(candidates, key=lambda p: rel(p))


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
        answer = prompt_read("more [Enter] / quit listing [q]: ")
        if answer.lower() == "q":
            break


def delete_candidates(candidates: list[Path], dry_run: bool) -> int:
    deleted = 0
    for path in candidates:
        if not is_inside_repo(path):
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
    args = parser.parse_args(argv)

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

    # Step 1: list everything, 10 entries per page.
    paginate(candidates, "Temporary files")

    # Step 2: explicit preview right before confirmation.
    print()
    paginate(candidates, "PREVIEW - files that WILL be deleted")

    print()
    what = "would delete" if args.dry_run else "delete"
    try:
        answer = prompt_read(f"{what} {len(candidates)} file(s) [y/N]: ")
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