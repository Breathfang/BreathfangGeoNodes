#!/usr/bin/env python3
"""Package the DragonGraph's Blender Add-on into an installable .zip.

Runs interactively (no options) or non-interactively (any --option, or under GitHub
Actions). Paths, naming templates, the ZIP exclusion policy and the logging setup all
come from the single ``.env`` in this folder, read through ``functions/``; every one of
them falls back to a built-in default, so the script also runs with no ``.env``
present.

Unlike ``nodepack_zip_generator.py`` (which packages the node ``.blend`` files) this
one packages the add-on source, so it enforces the two rules Blender's installers
actually care about:

* the archive root holds ``blender_manifest.toml`` (extension layout, Blender 4.2+),
  or a single ``<manifest id>/`` folder holding it (legacy add-on layout);
* the version in the manifest, the version in ``bl_info`` and the version the user
  typed all have to agree, because a mislabelled release is the one packaging bug that
  installs cleanly and then reports the wrong version in the UI.
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import sys
import tomllib
import zipfile
from dataclasses import dataclass
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:  # importable from any working directory
    sys.path.insert(0, str(_SCRIPT_DIR))

from functions import env_utils, log_utils, path_utils, prompt_utils  # noqa: E402

REPO_ROOT = path_utils.repo_root()

LOG_FILE = path_utils.resolve_under_root(
    env_utils.get_str("ADDON_GENERATOR_LOG", "nodepack_addon_generator.log")
)

SOURCE_DIR = path_utils.resolve_under_root(
    env_utils.get_str("ADDON_SOURCE_DIR", "DragonGraph's Blender Addon")
)
RELEASE_OUTPUT_DIR = path_utils.resolve_under_root(
    env_utils.get_str("ADDON_RELEASE_OUTPUT_DIR", "Generated Addons")
)

ADDON_VERSION = env_utils.get_str("ADDON_VERSION", "")
ZIP_NAME_TEMPLATE = env_utils.get_str(
    "ADDON_ZIP_NAME_TEMPLATE", "DragonGraph's Toolset Pack Addon {addon_version}"
)
DEFAULT_ZIP_LAYOUT = env_utils.get_str("ADDON_ZIP_LAYOUT", "extension").lower()
COMPRESSION_LEVEL = env_utils.get_int("ZIP_COMPRESSION_LEVEL", 9)

# Junk never belongs in a release. ``.md`` is deliberately absent from this list (unlike
# the node-pack policy): the add-on ships assets/README.md and library/README.md, which
# tell the person who installed it what to put in each folder.
EXCLUDED_SUFFIXES = env_utils.get_suffixes(
    "ADDON_ZIP_EXCLUDED_SUFFIXES",
    (".log", ".tmp", "~", ".orig", ".rej", ".pyc", ".pyo", ".blend1-9"),
)
# ``extracted`` is the loader's manual-load target: whatever the user unpacked
# into ``assets/extracted/`` is their content, not add-on source, and must never
# be republished inside a release.
EXCLUDED_DIR_NAMES = (
    "__pycache__",
    ".git",
    ".idea",
    ".vscode",
    ".mypy_cache",
    ".pytest_cache",
    "extracted",
)

LAYOUT_EXTENSION = "extension"
LAYOUT_LEGACY = "legacy"
LAYOUTS = (LAYOUT_EXTENSION, LAYOUT_LEGACY)

MANIFEST_FILENAME = "blender_manifest.toml"
INIT_FILENAME = "__init__.py"

# Windows refuses these in a filename, and a zip name is a filename. A leading dot is
# fine, a trailing dot or space is not.
_ILLEGAL_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WINDOWS_RESERVED = frozenset(
    {"CON", "PRN", "AUX", "NUL", *(f"COM{n}" for n in range(1, 10)), *(f"LPT{n}" for n in range(1, 10))}
)
_SMART_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"'})


class AddonPackagingError(RuntimeError):
    """Raised when the add-on source cannot be packaged as-is."""


@dataclass(frozen=True)
class ArchiveEntry:
    source: Path
    relative: str

    def exists(self) -> bool:
        return self.source.is_file()

    @property
    def size(self) -> int:
        return self.source.stat().st_size if self.source.is_file() else 0


def setup_logging():
    return log_utils.setup_logging("nodepack_addon_generator", LOG_FILE)


# ---------------------------------------------------------------------------
# Naming
# ---------------------------------------------------------------------------


def sanitize_zip_name(raw: str) -> str:
    """Turn whatever was typed into a safe ``*.zip`` file name.

    A pack name is prose ("DragonGraph's Toolset Pack 1.0.0"), so it is never trusted to
    already be a file name: path components are dropped, illegal characters are
    replaced, and a ``.zip`` suffix is added when missing. Trailing dots and spaces are
    stripped because Windows silently drops them, which would make the written file
    unreachable by the name the user just chose.
    """
    name = raw.translate(_SMART_QUOTES).strip()
    if len(name) >= 2 and name[0] == name[-1] and name[0] in "\"'":
        name = name[1:-1]  # unwrap "quoted", but keep a name like smart 'quote'
    name = re.split(r"[/\\]", name)[-1]  # a name is never a path
    # Collapse whitespace before filtering, so a tab typed by accident reads as a
    # space instead of becoming an underscore next to a real word.
    name = re.sub(r"\s+", " ", name).strip()
    name = _ILLEGAL_CHARS.sub("_", name)
    name = re.sub(r"\s+", " ", name).strip().rstrip(". ")
    if not name or set(name) <= {".", " "}:
        raise AddonPackagingError(f"{raw!r} is not a usable zip name.")
    if not name.lower().endswith(".zip"):
        name = f"{name}.zip"
    if name[: -len(".zip")].upper() in _WINDOWS_RESERVED:
        name = f"_{name}"
    return name


def format_size(num_bytes: int) -> str:
    return log_utils.fmt_size(num_bytes)


# ---------------------------------------------------------------------------
# Reading the add-on source
# ---------------------------------------------------------------------------


def is_excluded(relative_parts: tuple[str, ...], name: str) -> bool:
    if any(part in EXCLUDED_DIR_NAMES for part in relative_parts[:-1]):
        return True
    if name.endswith(EXCLUDED_SUFFIXES):
        return True
    return not name.lower().endswith((".py", ".toml", ".md", ".txt", ".blend", ".png", ".jpg", ".jpeg", ".svg", ".json"))


def collect_entries() -> list[ArchiveEntry]:
    """Manifest of every packaged file, sorted for a reproducible archive.

    Symlinks are skipped: a link inside the source would otherwise either dangle in the
    release or pull in a file from outside the add-on.
    """
    if not SOURCE_DIR.is_dir():
        raise AddonPackagingError(f"Add-on source directory not found: {SOURCE_DIR}")

    entries: list[ArchiveEntry] = []
    for path in sorted(SOURCE_DIR.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        relative_parts = path.relative_to(SOURCE_DIR).parts
        if is_excluded(relative_parts, path.name):
            continue
        entries.append(ArchiveEntry(source=path, relative=path.relative_to(SOURCE_DIR).as_posix()))
    if not entries:
        raise AddonPackagingError(f"No files to package in {SOURCE_DIR}.")
    return entries


def read_manifest() -> dict:
    manifest_path = SOURCE_DIR / MANIFEST_FILENAME
    if not manifest_path.is_file():
        raise AddonPackagingError(
            f"{MANIFEST_FILENAME} is missing from {SOURCE_DIR}. Without it Blender "
            f"cannot install the add-on as an extension."
        )
    with manifest_path.open("rb") as handle:
        manifest = tomllib.load(handle)
    for key in ("id", "version", "name"):
        if not str(manifest.get(key, "")).strip():
            raise AddonPackagingError(f"{MANIFEST_FILENAME} has no {key!r}.")
    return manifest


def read_bl_info_version() -> tuple[int, ...]:
    """Pull ``bl_info["version"]`` out of ``__init__.py`` without importing it.

    Importing would need ``bpy``, which only exists inside Blender, so the literal is
    read with :mod:`ast` instead.
    """
    init_path = SOURCE_DIR / INIT_FILENAME
    if not init_path.is_file():
        raise AddonPackagingError(f"{INIT_FILENAME} is missing from {SOURCE_DIR}.")
    tree = ast.parse(init_path.read_text(encoding="utf-8"), filename=INIT_FILENAME)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "bl_info" for t in node.targets):
            continue
        try:
            bl_info = ast.literal_eval(node.value)
        except ValueError:
            continue
        version = bl_info.get("version") if isinstance(bl_info, dict) else None
        if isinstance(version, tuple) and version:
            return tuple(int(part) for part in version)
    raise AddonPackagingError(f"bl_info has no 'version' tuple in {init_path}.")


def check_versions(manifest: dict, bl_info_version: tuple[int, ...], zip_name: str) -> list[str]:
    """Return warnings about anything that would ship a misleading version."""
    warnings: list[str] = []
    manifest_version = str(manifest["version"]).strip()
    bl_info_string = ".".join(str(part) for part in bl_info_version)
    if manifest_version != bl_info_string:
        warnings.append(
            f"manifest version {manifest_version!r} != bl_info version {bl_info_string!r}."
        )
    if ADDON_VERSION and manifest_version != ADDON_VERSION:
        warnings.append(f"ADDON_VERSION in .env is {ADDON_VERSION!r}, manifest says {manifest_version!r}.")
    stem = zip_name[: -len(".zip")]
    if manifest_version and manifest_version not in stem:
        warnings.append(
            f"zip name {stem!r} does not contain the version {manifest_version!r}; users "
            f"cannot tell which build they installed."
        )
    return warnings


def resolve_layout(requested: str) -> str:
    if requested not in LAYOUTS:
        raise AddonPackagingError(
            f"Unknown layout {requested!r}; choose one of {', '.join(LAYOUTS)}."
        )
    return requested


def check_required_files(entries: list[ArchiveEntry], manifest: dict, layout: str) -> None:
    """Fail before writing anything if the archive would not actually install.

    Both layouts package the same flat source: the extension layout writes it at the
    archive root, the legacy layout prefixes every path with the manifest id, so
    ``__init__.py`` has to be at the top of the source for either to work.
    """
    names = {entry.relative for entry in entries}
    if INIT_FILENAME not in names:
        raise AddonPackagingError(
            f"{INIT_FILENAME} is excluded or missing from the top level of "
            f"{SOURCE_DIR.name}; it is what makes this an add-on."
        )
    if f"{MANIFEST_FILENAME}" not in names:
        raise AddonPackagingError(
            f"{MANIFEST_FILENAME} is excluded or missing from the top level of "
            f"{SOURCE_DIR.name}."
        )
    if layout == LAYOUT_LEGACY and not str(manifest["id"]).strip():
        raise AddonPackagingError("The legacy layout needs the manifest id to name the top folder.")
    if not any(name.endswith((".blend", ".md")) for name in names):
        raise AddonPackagingError(
            "Nothing packageable found in the source folder besides Python. Expected "
            "assets/*.blend or library/*.blend for the node pack."
        )


# ---------------------------------------------------------------------------
# Writing the archive
# ---------------------------------------------------------------------------


def arcname_for(entry: ArchiveEntry, layout: str, legacy_root: str) -> str:
    if layout == LAYOUT_LEGACY:
        return f"{legacy_root}/{entry.relative}"
    return entry.relative


def build_archive(entries, output_path: Path, layout: str, legacy_root: str, logger) -> int:
    """Write the zip atomically: a half-written archive is never left behind.

    The archive is built beside its final name and moved into place only after the
    handle closes cleanly, so an interrupted run cannot leave a ``.zip`` that Blender
    will happily try to install.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    staging = output_path.with_name(f"{output_path.name}.part")
    if staging.exists():
        staging.unlink()

    total = 0
    try:
        with zipfile.ZipFile(
            staging,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=COMPRESSION_LEVEL,
        ) as zipf:
            for entry in entries:
                arcname = arcname_for(entry, layout, legacy_root)
                zipf.write(entry.source, arcname=arcname)
                total += entry.size
                logger.info("Inserted %s into zip as %s", entry.source, arcname)
        os.replace(staging, output_path)
    finally:
        if staging.exists():
            staging.unlink()
    return total


def verify_archive(output_path: Path, entries, layout: str, legacy_root: str) -> None:
    """Re-open what was just written and confirm it is installable."""
    with zipfile.ZipFile(output_path) as zipf:
        broken = zipf.testzip()
        if broken is not None:
            raise AddonPackagingError(f"{broken!r} in the archive is corrupt.")
        names = set(zipf.namelist())
        if layout == LAYOUT_EXTENSION:
            if MANIFEST_FILENAME not in names:
                raise AddonPackagingError(f"{MANIFEST_FILENAME} is not at the archive root.")
        elif f"{legacy_root}/{MANIFEST_FILENAME}" not in names:
            raise AddonPackagingError(f"{MANIFEST_FILENAME} is missing from {legacy_root}/.")
        stray = sorted(name for name in names if "__pycache__" in name or name.endswith(".pyc"))
        if stray:
            raise AddonPackagingError(f"Cached bytecode leaked into the archive: {stray}")
        expected = {arcname_for(entry, layout, legacy_root) for entry in entries}
        missing = expected - names
        if missing:
            raise AddonPackagingError(f"{len(missing)} file(s) missing from the archive: {sorted(missing)[:5]}")


# ---------------------------------------------------------------------------
# Flows
# ---------------------------------------------------------------------------


def describe_plan(entries, manifest, layout, legacy_root, zip_name, out_dir, logger) -> None:
    total = sum(entry.size for entry in entries)
    logger.info("Add-on source: %s", path_utils.display(SOURCE_DIR))
    logger.info("Manifest: %s v%s", manifest["id"], manifest["version"])
    logger.info("Layout: %s%s", layout, f" (folder {legacy_root}/)" if layout == LAYOUT_LEGACY else "")
    logger.info("Collected %d file(s), %s raw.", len(entries), format_size(total))
    for entry in entries:
        logger.info("  %-44s %8s", entry.relative, format_size(entry.size))
    logger.info("Output: %s", out_dir / zip_name)
    logger.info("Install it with Edit > Preferences > Get Extensions > (dropdown) > Install from Disk.")


def build(entries, manifest, layout, legacy_root, zip_name, out_dir, logger) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / zip_name
    build_archive(entries, output_path, layout, legacy_root, logger)
    verify_archive(output_path, entries, layout, legacy_root)

    with zipfile.ZipFile(output_path) as zipf:
        archive_size = sum(info.file_size for info in zipf.infolist())
    logger.info("Wrote %s (%s on disk, %s uncompressed)", output_path, format_size(output_path.stat().st_size), format_size(archive_size))
    logger.info("Done!")
    return 0


def interactive_build(logger) -> int:
    """Guided CLI UI: the zip name is typed, not guessed."""
    manifest = read_manifest()
    bl_info_version = read_bl_info_version()
    entries = collect_entries()

    default_name = sanitize_zip_name(
        ZIP_NAME_TEMPLATE.format(addon_version=manifest["version"])
    )
    print("")
    print("DragonGraph's Blender Add-on - ZIP generator")
    print("============================================")
    print(f"Settings: {env_utils.source_description()}")
    print(f"Add-on: {manifest['name']} v{manifest['version']} (bl_info {bl_info_version})")
    print(f"Source: {path_utils.display(SOURCE_DIR)}")
    print("")
    print("Type the name you want the .zip to have. The .zip suffix is added for you,")
    print("and the name must contain the version so users can tell builds apart.")

    zip_name = sanitize_zip_name(prompt_utils.ask("ZIP name", default_name))
    layout = resolve_layout(
        prompt_utils.ask(f"Layout [{LAYOUT_EXTENSION}/{LAYOUT_LEGACY}]", DEFAULT_ZIP_LAYOUT).lower()
    )
    legacy_root = str(manifest["id"]).strip()
    out_dir = path_utils.resolve_under_root(
        prompt_utils.ask("Output directory", RELEASE_OUTPUT_DIR.as_posix())
    )

    for warning in check_versions(manifest, bl_info_version, zip_name):
        logger.warning("Version check: %s", warning)
    try:
        check_required_files(entries, manifest, layout)
    except AddonPackagingError as error:
        logger.error("%s", error)
        return 1

    describe_plan(entries, manifest, layout, legacy_root, zip_name, out_dir, logger)
    if not prompt_utils.ask_yes_no("Continue?", default=True):
        logger.info("Cancelled by user.")
        return 0

    return build(entries, manifest, layout, legacy_root, zip_name, out_dir, logger)


def main(args, logger) -> int:
    """Non-interactive build driven entirely by --options (used in CI/scripts)."""
    manifest = read_manifest()
    bl_info_version = read_bl_info_version()
    entries = collect_entries()
    logger.info("Collected %d source file(s).", len(entries))
    logger.info("Settings: %s", env_utils.source_description())

    zip_name = sanitize_zip_name(
        args.zip_name or ZIP_NAME_TEMPLATE.format(addon_version=manifest["version"])
    )
    layout = resolve_layout(args.layout or DEFAULT_ZIP_LAYOUT)
    legacy_root = str(manifest["id"]).strip()
    out_dir = path_utils.resolve_under_root(args.output_dir) if args.output_dir else RELEASE_OUTPUT_DIR

    for warning in check_versions(manifest, bl_info_version, zip_name):
        logger.warning("Version check: %s", warning)
    check_required_files(entries, manifest, layout)

    if args.dry_run:
        describe_plan(entries, manifest, layout, legacy_root, zip_name, out_dir, logger)
        logger.info("Dry run: nothing written.")
        return 0

    return build(entries, manifest, layout, legacy_root, zip_name, out_dir, logger)


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Package DragonGraph's Blender Add-on into an installable .zip. Run "
        "without options to launch the interactive wizard (terminal or IDE), where you "
        "type the zip name; pass --options - or run under GitHub Actions - to build "
        "non-interactively."
    )
    parser.add_argument(
        "--zip-name",
        default=None,
        help="Name of the archive, with or without the .zip suffix. When omitted, "
        f"{ZIP_NAME_TEMPLATE!r} is filled in with the manifest version.",
    )
    parser.add_argument(
        "--layout",
        choices=LAYOUTS,
        default=None,
        help=f"Archive layout: {LAYOUT_EXTENSION} (default) puts blender_manifest.toml at "
        f"the archive root, which is what Blender 4.2+ wants; {LAYOUT_LEGACY} wraps "
        "everything in a single folder named after the manifest id, which is what the "
        "legacy Install from Disk path wants.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Override the output directory; relative paths resolve under the "
        f"repository root (default: {RELEASE_OUTPUT_DIR.name!r}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List and validate what would be packaged, then exit without writing.",
    )
    parser.add_argument(
        "--no-pause",
        action="store_true",
        help="Do not wait for Enter on exit (PAUSE_PROMPT comes from .env).",
    )
    parser.add_argument(
        "--show-settings",
        action="store_true",
        help="Print the resolved .env settings and exit.",
    )
    args = parser.parse_args(argv)

    logger = setup_logging()

    if args.show_settings:
        logger.info("Settings: %s", env_utils.source_description())
        for name, value in (
            ("ADDON_SOURCE_DIR", SOURCE_DIR),
            ("ADDON_RELEASE_OUTPUT_DIR", RELEASE_OUTPUT_DIR),
            ("ADDON_VERSION", ADDON_VERSION or "(read from the manifest)"),
            ("ADDON_ZIP_NAME_TEMPLATE", ZIP_NAME_TEMPLATE),
            ("ADDON_ZIP_LAYOUT", DEFAULT_ZIP_LAYOUT),
            ("ZIP_COMPRESSION_LEVEL", COMPRESSION_LEVEL),
            ("ADDON_ZIP_EXCLUDED_SUFFIXES", ", ".join(EXCLUDED_SUFFIXES)),
            ("ADDON_GENERATOR_LOG", LOG_FILE),
        ):
            logger.info("  %s = %s", name, value)
        return 0

    by_options = any(
        value is not None
        for value in (args.zip_name, args.layout, args.output_dir)
    ) or args.dry_run
    in_ci = os.environ.get("GITHUB_ACTIONS") == "true"
    try:
        if by_options or in_ci:
            exit_code = main(args, logger)
        else:
            try:
                exit_code = interactive_build(logger)
            except EOFError:
                # IDEs often run scripts with stdin closed; build automatically
                # instead of failing, so the run still completes.
                print(
                    "No interactive input is available here; building automatically.",
                    file=sys.stderr,
                )
                exit_code = main(args, logger)
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        exit_code = 130
    except Exception as error:
        logger.error("Error: %s", error, exc_info=True)
        exit_code = 1

    prompt_utils.pause_if_requested(args.no_pause)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(run())
