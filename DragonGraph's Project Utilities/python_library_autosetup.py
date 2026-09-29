#!/usr/bin/env python3
"""Install the Sphinx documentation toolchain used by the docs build.

The Python floor, the list of PyPI distributions to install and the log
location come from the single ``.env`` in this folder, read through
``functions/``; each falls back to a built-in default.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import platform
import subprocess
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:  # importable from any working directory
    sys.path.insert(0, str(_SCRIPT_DIR))

from functions import env_utils, log_utils, path_utils, prompt_utils  # noqa: E402

LOG_FILE = path_utils.resolve_under_root(
    env_utils.get_str("LIBRARY_AUTOSETUP_LOG", "python_library_autosetup.log")
)

MIN_PYTHON = tuple(
    int(part) for part in env_utils.get_str("MIN_PYTHON", "3.13").split(".") if part.strip()
)
MIN_PYTHON_VERSION = ".".join(map(str, MIN_PYTHON))

# PyPI distribution names. Note these differ from import names for some packages
# (for example sphinx-autobuild is imported as sphinx_autobuild).
REQUIRED_PACKAGES = env_utils.get_list(
    "DOCS_PACKAGES", ("sphinx", "sphinx-autobuild", "sphinx_rtd_theme")
)


def setup_logging():
    return log_utils.setup_logging("python_library_autosetup", LOG_FILE)


def describe_environment(logger) -> None:
    logger.info("Minimum Python version: %s", MIN_PYTHON_VERSION)
    logger.info("Current Python version: %s", platform.python_version())
    logger.info("Interpreter: %s", sys.executable)
    logger.info("Settings: %s", env_utils.source_description())


def check_python_version() -> None:
    if sys.version_info[:2] < MIN_PYTHON:
        raise RuntimeError(
            f"Python {MIN_PYTHON_VERSION} or higher is required, "
            f"but this interpreter is {platform.python_version()}."
        )


def is_installed(distribution: str) -> bool:
    try:
        importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return False
    return True


def install(distribution: str, upgrade: bool, logger) -> bool:
    command = [sys.executable, "-m", "pip", "install"]
    if upgrade:
        command.append("--upgrade")
    command.append(distribution)

    action = "Updating" if upgrade else "Installing"
    logger.info("%s %s...", action, distribution)

    result = subprocess.run(command)
    if result.returncode != 0:
        logger.error("pip exited with code %d while handling %s", result.returncode, distribution)
        return False
    return True


def install_required_packages(logger) -> list[str]:
    failed = []
    for distribution in REQUIRED_PACKAGES:
        upgrade = is_installed(distribution)
        if upgrade:
            logger.info("%s is already installed, checking for updates...", distribution)
        if not install(distribution, upgrade, logger):
            failed.append(distribution)
    return failed


def main(logger, assume_yes: bool) -> int:
    logger.info("Checking Python version...")
    describe_environment(logger)
    check_python_version()

    if not assume_yes and not prompt_utils.ask_yes_no(
        "Do you want to install the required documentation packages?"
    ):
        logger.info("Process stopped by user.")
        return 0

    failed = install_required_packages(logger)
    if failed:
        logger.error("Failed to set up: %s", ", ".join(failed))
        return 1

    logger.info("All required packages are installed.")
    return 0


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Install the Sphinx documentation toolchain used by the docs build."
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the confirmation prompt and install directly (for CI).",
    )
    parser.add_argument(
        "--no-pause",
        action="store_true",
        help="Do not wait for Enter on exit (PAUSE_PROMPT comes from .env).",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print the resolved .env settings and exit.",
    )
    args = parser.parse_args(argv)

    logger = setup_logging()
    if args.list:
        logger.info("Settings: %s", env_utils.source_description())
        logger.info("  MIN_PYTHON = %s", MIN_PYTHON_VERSION)
        logger.info("  DOCS_PACKAGES = %s", ", ".join(REQUIRED_PACKAGES))
        logger.info("  LIBRARY_AUTOSETUP_LOG = %s", LOG_FILE)
        return 0

    try:
        exit_code = main(logger, args.yes)
    except Exception as error:
        logger.error("Error: %s", error, exc_info=True)
        exit_code = 1

    prompt_utils.pause_if_requested(args.no_pause)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(run())
