#!/usr/bin/env python3
"""Nightly ZIP builder for "DragonGraph's Toolset Pack".

Packages every project asset below a source directory recursively into a single
versioned snapshot archive:

    DragonGraph's Toolset Pack NightlyBuilds_<8-hex>_<YYYYMMDD-HHMMSS>.zip

The 8-hex identifier is derived, in order of preference, from the GITHUB_SHA
environment variable (CI), a ``git rev-parse --short=8 HEAD`` lookup, or a
cryptographically random 8-hex value. The timestamp is always UTC.

ZIP contents: every regular file below the source directory (all file types,
including Collabs/ subfolders), except the exclusion policy configured in this
folder's ``.env`` - by default .md/.log/.tmp, the editor backups '*~', '*.orig'
and '*.rej', and the Blender autosaves '*.blend1' .. '*.blend9'. Those
exclusions do not depend on how the script is invoked.

By default the archive is written to "DragonGraph's Nighty Build/" so it can be
committed to the repository while still being stored as a GitHub artifact.

Exit codes: 0 = archive written, 2 = usage / environment error.
"""

from __future__ import annotations

import argparse
import datetime
import os
import secrets
import sys
import zipfile
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:  # importable from any working directory
    sys.path.insert(0, str(_SCRIPT_DIR))

from functions import ci_utils, env_utils, path_utils, scan_utils  # noqa: E402

# Re-exported under its historical name: the workflow's import-time gate reads
# nightly_builder.BUILDS_ENABLED to decide whether to run the pipeline at all.
BUILDS_ENABLED = ci_utils.BUILDS_ENABLED

SOURCE_DIR_NAME = env_utils.get_str("SOURCE_DIR", "DragonGraph's Project")
OUTPUT_DIR_NAME = env_utils.get_str("NIGHTLY_OUTPUT_DIR", "DragonGraph's Nighty Build")
ZIP_NAME_TEMPLATE = env_utils.get_str(
    "NIGHTLY_ZIP_NAME", "DragonGraph's Toolset Pack NightlyBuilds_{hex}_{timestamp}.zip"
)
COMPRESSION_LEVEL = env_utils.get_int("ZIP_COMPRESSION_LEVEL", 9)

# Explicit exclusion policy (see .env).
EXCLUDED_SUFFIXES = env_utils.get_suffixes(
    "ZIP_EXCLUDED_SUFFIXES",
    (".md", ".log", ".tmp", "~", ".orig", ".rej")
    + tuple(f".blend{index}" for index in range(1, 10)),
)


def build_hex_ident() -> str:
    sha = os.environ.get("GITHUB_SHA")
    if sha:
        return sha[:8]
    short = ci_utils.short_sha()
    if short:
        return short
    return secrets.token_hex(4)


def build_timestamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")


def is_excluded(rel_parts: tuple[str, ...]) -> bool:
    """True when the relative path ends with an excluded suffix."""
    return rel_parts[-1].lower().endswith(EXCLUDED_SUFFIXES)


def collect_entries(source_dir: Path):
    """Yield (absolute path, arcname) for every non-symlink regular file below
    the source directory.

    The source directory becomes the archive root: entries use their path
    relative to the source dir (no "<source dir>/..." prefix is stored), and
    nothing from sibling or parent folders is ever included.
    """
    for path in sorted(source_dir.rglob("*")):
        if not (path.is_file() and not path.is_symlink()):
            continue
        try:
            rel = path.relative_to(source_dir)  # archive root = source dir
        except ValueError:
            continue  # outside the source root: never package
        if is_excluded(rel.parts):
            continue
        yield path, rel.as_posix()


def build_archive(output_path: Path, entries) -> None:
    with zipfile.ZipFile(
        output_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=COMPRESSION_LEVEL,
    ) as zipf:
        for path, arcname in entries:
            zipf.write(path, arcname=arcname)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Package DragonGraph's Project assets into a nightly .zip "
        "under DragonGraph's Nighty Build/."
    )
    parser.add_argument(
        "--repo", default=".", help="Path to the git repository root (default: the repo root)"
    )
    parser.add_argument(
        "--source-dir",
        default=SOURCE_DIR_NAME,
        help=f"Source assets directory (default: {SOURCE_DIR_NAME!r})",
    )
    parser.add_argument(
        "--output-dir",
        default=OUTPUT_DIR_NAME,
        help=f"Output directory (default: {OUTPUT_DIR_NAME!r})",
    )
    parser.add_argument(
        "--hex",
        default=None,
        help="Override the 8-char hex identifier (for deterministic tests)",
    )
    parser.add_argument(
        "--timestamp",
        default=None,
        help="Override the UTC timestamp YYYYMMDD-HHMMSS (for deterministic tests)",
    )
    parser.add_argument(
        "--show-settings",
        action="store_true",
        help="Print the resolved .env settings and exit",
    )
    parser.add_argument("-q", "--quiet", action="store_true")
    args = parser.parse_args(argv)

    # CI pause switch: when BUILDS_ENABLED is False, GitHub Actions runs bail
    # out early (belt-and-suspenders on top of the workflow gate). Local and
    # manual invocations still build normally.
    if ci_utils.in_ci() and not BUILDS_ENABLED:
        print(
            "[nightly-builder] nightly builds are DISABLED "
            "(NIGHTLY_BUILDS_ENABLED = false in .github/scripts/.env); "
            "nothing was created or pushed"
        )
        return 0

    if args.show_settings:
        print(f"Settings: {env_utils.source_description()}")
        print(f"  NIGHTLY_BUILDS_ENABLED = {BUILDS_ENABLED}")
        print(f"  SOURCE_DIR = {SOURCE_DIR_NAME!r}")
        print(f"  NIGHTLY_OUTPUT_DIR = {OUTPUT_DIR_NAME!r}")
        print(f"  ZIP_COMPRESSION_LEVEL = {COMPRESSION_LEVEL}")
        print(f"  ZIP_EXCLUDED_SUFFIXES = {', '.join(EXCLUDED_SUFFIXES)}")
        return 0

    repo = scan_utils.resolve_repo(args.repo)
    source_dir = path_utils.resolve_against(repo, args.source_dir)
    output_dir = path_utils.resolve_against(repo, args.output_dir)

    if not source_dir.is_dir():
        print(f"[nightly-builder] source directory not found: {source_dir}", file=sys.stderr)
        return 2

    output_dir.mkdir(parents=True, exist_ok=True)
    zip_name = ZIP_NAME_TEMPLATE.format(
        hex=(args.hex or build_hex_ident()),
        timestamp=(args.timestamp or build_timestamp()),
    )
    output_path = output_dir / zip_name

    entries = list(collect_entries(source_dir))
    if not entries:
        print(f"[nightly-builder] no files found below {source_dir}", file=sys.stderr)
        return 2

    build_archive(output_path, entries)

    if not args.quiet:
        print(
            f"[nightly-builder] wrote {zip_name} "
            f"({output_path.stat().st_size} bytes, {len(entries)} entries)"
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except KeyboardInterrupt:
        print("[nightly-builder] interrupted.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:  # unexpected crash -> bypass, never abort CI
        print(f"[nightly-builder] unexpected crash: {exc!r}; bypassed (exit 2).", file=sys.stderr)
        raise SystemExit(2)
