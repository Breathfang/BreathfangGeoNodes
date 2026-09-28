#!/usr/bin/env python3
"""Rotation and cleanup for nightly build archives.

Deletes the oldest matching archives under TARGET_DIR until both of the elastic
limits below are satisfied. Archives are sorted chronologically (oldest first,
ties broken by name).

Rotation rules:
  Rule 1 (count): delete the oldest archive repeatedly until the number of
      matching archives is <= MAX_BUILD_COUNT.
  Rule 2 (size): delete the oldest archive repeatedly until the total size of
      the matching archives drops safely below MAX_TOTAL_SIZE_MB.

The policy is list-agnostic, so raising or lowering the elastic variables below
is enough to capture more or fewer historical builds.

Exit codes: always 0 when the directory was inspected successfully.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import sys
from pathlib import Path

# Shares the single master toggle with the builder: when BUILDS_ENABLED is False
# this script refuses to run under CI (defense-in-depth on top of the workflow
# gate), so no archives are ever cleaned while the pipeline is paused.
from nightly_builder import BUILDS_ENABLED

# --------------------------------------------------------------------------
# Elastic configuration (edit here)
# --------------------------------------------------------------------------
TARGET_DIR = Path("DragonGraph's Nighty Build")
MAX_BUILD_COUNT = 10  # maximum number of matching ZIP files to keep
MAX_TOTAL_SIZE_MB = 300.0  # maximum total directory size of matching ZIP files
FILE_PATTERN = "Dragongraph's Toolset Pack NightlyBuilds_*.zip"
# --------------------------------------------------------------------------

_MIB = 1024 * 1024


def collect_archives(target: Path, pattern: str) -> list[Path]:
    if not target.is_dir():
        return []
    matches = [
        p
        for p in target.iterdir()
        if p.is_file() and fnmatch.fnmatch(p.name, pattern)
    ]
    # Chronological order: oldest first, then by name for deterministic ties.
    return sorted(
        matches,
        key=lambda p: (p.stat().st_mtime, p.name),
    )


def total_size(archives: list[Path]) -> int:
    return sum(p.stat().st_size for p in archives)


def rotate(
    target: Path,
    *,
    max_count: int,
    max_size_bytes: int,
    pattern: str,
    dry_run: bool,
    quiet: bool,
) -> list[Path]:
    archives = collect_archives(target, pattern)
    deleted: list[Path] = []

    if not archives:
        if not quiet:
            print(f"[nightly-cleaner] no archives matching {pattern!r} in {target}")
        return deleted

    kept = archives[:]

    # Rule 1: count limit (delete oldest until count <= max_count).
    while len(kept) > max_count:
        deleted.append(kept.pop(0))

    # Rule 2: total size limit (delete oldest until size safely below limit).
    size = total_size(kept)
    while size > max_size_bytes and kept:
        size -= kept[0].stat().st_size
        deleted.append(kept.pop(0))

    deleted.sort(key=lambda p: (p.stat().st_mtime, p.name))

    if not quiet:
        kept_mb = total_size(kept) / _MIB
        print(
            f"[nightly-cleaner] {len(archives)} archive(s), "
            f"{len(kept)} kept ({kept_mb:.1f} MiB), {len(deleted)} removed"
        )

    if dry_run:
        prefix = "would delete"
    else:
        prefix = "deleted"
        for victim in deleted:
            victim.unlink(missing_ok=True)
    for victim in deleted:
        print(f"  - {prefix}: {victim.name}")
    return deleted


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Rotate nightly build archives under DragonGraph's Nighty Build/."
    )
    parser.add_argument("--repo", default=".", help="Path to the git repository root")
    parser.add_argument(
        "--target-dir",
        default=None,
        help=f"Target directory (default: {TARGET_DIR})",
    )
    parser.add_argument(
        "--max-count",
        type=int,
        default=None,
        help=f"Max archives to keep (default: {MAX_BUILD_COUNT})",
    )
    parser.add_argument(
        "--max-size-mb",
        type=float,
        default=None,
        help=f"Max total size in MiB (default: {MAX_TOTAL_SIZE_MB})",
    )
    parser.add_argument(
        "--pattern",
        default=None,
        help=f"Filename pattern (default: {FILE_PATTERN!r})",
    )
    parser.add_argument("--dry-run", action="store_true", help="Report only, delete nothing")
    parser.add_argument("-q", "--quiet", action="store_true")
    args = parser.parse_args(argv)

    # CI pause switch: mirrors nightly_builder.BUILDS_ENABLED so this script can
    # never delete archives (or end up committed) while nightly builds are
    # paused. Local/manual runs are still allowed.
    ci_run = os.environ.get("GITHUB_ACTIONS") == "true"
    if ci_run and not BUILDS_ENABLED:
        print(
            "[nightly-cleaner] nightly builds are DISABLED "
            "(BUILDS_ENABLED = False in .github/scripts/nightly_builder.py); "
            "cleanup skipped, nothing was deleted",
            file=sys.stderr,
        )
        return 0

    repo = Path(args.repo).expanduser().resolve()
    target = Path(args.target_dir).expanduser().resolve() if args.target_dir else (repo / TARGET_DIR).resolve()

    max_count = MAX_BUILD_COUNT if args.max_count is None else args.max_count
    max_size_bytes = int((MAX_TOTAL_SIZE_MB if args.max_size_mb is None else args.max_size_mb) * _MIB)
    pattern = FILE_PATTERN if args.pattern is None else args.pattern

    if not target.is_dir():
        if not args.quiet:
            print(f"[nightly-cleaner] target directory not found: {target}", file=sys.stderr)
        return 0

    rotate(
        target,
        max_count=max_count,
        max_size_bytes=max_size_bytes,
        pattern=pattern,
        dry_run=args.dry_run,
        quiet=args.quiet,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except KeyboardInterrupt:
        print("[nightly-cleaner] interrupted.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:  # unexpected crash -> bypass, never abort CI
        print(f"[nightly-cleaner] unexpected crash: {exc!r}; bypassed (exit 2).", file=sys.stderr)
        raise SystemExit(2)