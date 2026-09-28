import argparse
import datetime
import logging
import os
import re
import secrets
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = _SCRIPT_DIR.parent

LOG_FILE = REPO_ROOT / "nodepack_zip_generator.log"
LOG_MAX_BYTES = 1_000_000
LOG_BACKUP_COUNT = 5
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

SOURCE_DIR = REPO_ROOT / "DragonGraph's Project"
PACK_NAME_TEMPLATE = "DragonGraph's Toolset Pack {node_version}"
RELEASE_OUTPUT_DIR = REPO_ROOT / "Generated Nodepacks"
RELEASE_NAME_TEMPLATE = "{pack_name} - Asset Library.zip"

DEFAULT_NODE_VERSION = "v1.1.0-alpha"  # last-resort fallback for non-interactive runs

NIGHTLY_OUTPUT_DIR = REPO_ROOT / "DragonGraph's Nighty Build"
NIGHTLY_NAME_TEMPLATE = "Dragongraph's Toolset Pack NightlyBuilds_{hex}_{timestamp}.zip"

COMPRESSION_LEVEL = 9

# ZIP exclusion policy (hard-coded, applied to both release and nightly packs).
BLEND_AUTOSAVE_SUFFIXES = tuple(f".blend{d}" for d in range(1, 10))  # .blend1..9
EXCLUDED_SUFFIXES = (".md", ".log", ".tmp", "~", ".orig", ".rej") + BLEND_AUTOSAVE_SUFFIXES

PAUSE_PROMPT = "Press enter to exit..."


@dataclass(frozen=True)
class ArchiveEntry:
    source: Path
    arcname: str

    def exists(self) -> bool:
        return self.source.is_file()


def setup_logging() -> logging.Logger:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(LOG_FORMAT)

    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


def prompt_read(prompt_text: str) -> str:
    """Print a prompt, flush it, then read one line from the user."""
    sys.stdout.write(prompt_text)
    sys.stdout.flush()
    return input().strip()


def ask(prompt: str, default: str | None = None) -> str:
    """Read one line from the user, accepting the bracketed default on empty input."""
    if default is None:
        prompt_text = f"{prompt}: "
    else:
        prompt_text = f"{prompt} [{default}]: "
    return prompt_read(prompt_text) or default or ""


def nightly_hex_ident() -> str:
    sha = os.environ.get("GITHUB_SHA")
    if sha:
        return sha[:8]
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short=8", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            short = result.stdout.strip()
            if short:
                return short[:8]
    except OSError:
        pass
    return secrets.token_hex(4)


def nightly_timestamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")


def is_supported_file(path: Path) -> bool:
    """True for a regular file whose name does not end with an excluded suffix."""
    if not (path.is_file() and not path.is_symlink()):
        return False
    return not path.name.lower().endswith(EXCLUDED_SUFFIXES)


def collect_entries() -> list[ArchiveEntry]:
    """Manifest of every packaged file. DragonGraph's Project/ becomes the
    archive root: every supported file keeps its original name and its path
    relative to that folder, so the archive reproduces the source directory
    exactly (minus the excluded suffixes).
    """
    if not SOURCE_DIR.is_dir():
        raise FileNotFoundError(f"Source directory not found: {SOURCE_DIR}")

    entries: list[ArchiveEntry] = []
    for path in sorted(SOURCE_DIR.rglob("*")):
        if not is_supported_file(path):
            continue
        arcname = path.relative_to(SOURCE_DIR).as_posix()  # archive root = source dir
        entries.append(ArchiveEntry(source=path, arcname=arcname))
    return entries


def pack_version_from_entries(entries: list[ArchiveEntry]) -> str | None:
    """Borrow the pack version from the first .blend filename (e.g. v1.3.0-beta)."""
    for entry in entries:
        match = re.search(r"v\d+(?:\.\d+)+(?:-[A-Za-z0-9.]+)?", entry.source.stem)
        if match:
            return match.group(0)
    return None


def ensure_entries_exist(entries: list[ArchiveEntry], logger: logging.Logger) -> None:
    missing = [entry.source for entry in entries if not entry.exists()]
    if not missing:
        return
    for source in missing:
        logger.error("Missing source file: %s", source)
    raise FileNotFoundError(f"{len(missing)} source file(s) are missing.")


def build_archive(entries: list[ArchiveEntry], output_path: Path, logger: logging.Logger) -> None:
    with zipfile.ZipFile(
        output_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=COMPRESSION_LEVEL,
    ) as zipf:
        for entry in entries:
            zipf.write(entry.source, arcname=entry.arcname)
            logger.info("Inserted %s into zip as %s", entry.source, entry.arcname)


def build_pack(
    entries: list[ArchiveEntry],
    *,
    nightly: bool,
    node_version: str | None,
    output_dir: str | None,
    logger: logging.Logger,
) -> int:
    """Perform the actual build for a fully resolved set of options."""
    if nightly:
        hex_ident = nightly_hex_ident()
        timestamp = nightly_timestamp()
        out = Path(output_dir) if output_dir else NIGHTLY_OUTPUT_DIR
        output_path = out / NIGHTLY_NAME_TEMPLATE.format(hex=hex_ident, timestamp=timestamp)
        logger.info("Nightly build: short SHA %s @ %s UTC", hex_ident, timestamp)
    else:
        pack_name = PACK_NAME_TEMPLATE.format(node_version=node_version)
        out = Path(output_dir) if output_dir else RELEASE_OUTPUT_DIR
        output_path = out / RELEASE_NAME_TEMPLATE.format(pack_name=pack_name)

    out.mkdir(exist_ok=True)
    build_archive(entries, output_path, logger)

    logger.info("Wrote %s", output_path)
    logger.info("Done!")
    return 0


def interactive_build(logger: logging.Logger) -> int:
    """Guided CLI UI for users running the script without any --options."""
    entries = collect_entries()
    ensure_entries_exist(entries, logger)

    print("")
    print("Dragongraph's Toolset Pack - ZIP generator")
    print("==========================================")
    print("What do you want to build?")
    print("  1) Release (versioned asset library .zip)")
    print("  2) Nightly snapshot")
    print("  3) Quit")
    sys.stdout.flush()

    while True:
        choice = prompt_read("Choose [1/2/3]: ") or "3"
        if choice in ("1", "2", "3"):
            break
    if choice == "2":
        nightly = True
        node_version = None
        default_out = NIGHTLY_OUTPUT_DIR.as_posix()
        kind = "nightly snapshot"
        version_note = ""
    elif choice == "1":
        nightly = False
        default_version = pack_version_from_entries(entries) or DEFAULT_NODE_VERSION
        node_version = ask("Node version", default_version)
        default_out = RELEASE_OUTPUT_DIR.as_posix()
        kind = "release"
        version_note = f" {node_version!r}"
    else:
        logger.info("Exiting without building.")
        return 0

    out_dir = Path(ask("Output directory", default_out))
    if not out_dir.is_absolute():
        out_dir = REPO_ROOT / out_dir

    print(f"  -> Build {kind}{version_note} into {out_dir}")
    confirm = prompt_read("Continue? [Y/n]: ").lower()
    if confirm in ("n", "no"):
        logger.info("Cancelled by user.")
        return 0

    return build_pack(
        entries,
        nightly=nightly,
        node_version=node_version,
        output_dir=str(out_dir),
        logger=logger,
    )


def main(args, logger) -> int:
    """Non-interactive build driven entirely by --options (used in CI/scripts)."""
    entries = collect_entries()
    ensure_entries_exist(entries, logger)

    logger.info("Collected %d source file(s).", len(entries))

    node_version = None
    if not args.nightly:
        if args.node_version is None:
            node_version = pack_version_from_entries(entries) or DEFAULT_NODE_VERSION
            logger.info("No --node-version given in non-interactive mode; using %r.", node_version)
        else:
            node_version = args.node_version

    return build_pack(
        entries,
        nightly=args.nightly,
        node_version=node_version,
        output_dir=args.output_dir,
        logger=logger,
    )


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Package DragonGraph's Toolset Pack assets into a release or nightly "
        ".zip. Run without options to launch the interactive build wizard (terminal or "
        "IDE); pass --options - or run under GitHub Actions - to build non-interactively."
    )
    parser.add_argument(
        "--nightly",
        action="store_true",
        help=f"Build a nightly snapshot instead of a versioned release; named "
        f"{NIGHTLY_NAME_TEMPLATE!r} inside {NIGHTLY_OUTPUT_DIR}.",
    )
    parser.add_argument(
        "--node-version",
        default=None,
        help="Release version string (e.g. v1.1.0-alpha). When omitted the version "
        "is parsed from the first .blend filename (falling back to a default).",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Override the output directory; relative paths resolve under the "
        "repository root (default: 'Generated Nodepacks' for releases, "
        "'DragonGraph's Nighty Build' for nightlies).",
    )
    parser.add_argument("--no-pause", action="store_true", help="Do not wait for Enter on exit.")
    args = parser.parse_args(argv)

    logger = setup_logging()

    by_options = (
        args.nightly or args.node_version is not None or args.output_dir is not None
    )
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

    if not args.no_pause and sys.stdin.isatty():
        input(PAUSE_PROMPT)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(run())