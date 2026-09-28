import argparse
import importlib.metadata
import logging
import platform
import subprocess
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FILE = Path("_PythonLibraryAutoSetup.log")
LOG_MAX_BYTES = 1_000_000
LOG_BACKUP_COUNT = 5
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

MIN_PYTHON = (3, 13)
MIN_PYTHON_VERSION = ".".join(map(str, MIN_PYTHON))

# PyPI distribution names. Note these differ from import names for some packages
# (for example sphinx-autobuild is imported as sphinx_autobuild).
REQUIRED_PACKAGES = (
    "sphinx",
    "sphinx-autobuild",
    "sphinx_rtd_theme",
)

PAUSE_PROMPT = "Press enter to exit..."


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


def pause() -> None:
    if sys.stdin.isatty():
        input(PAUSE_PROMPT)


def describe_environment(logger: logging.Logger) -> None:
    logger.info("Minimum Python version: %s", MIN_PYTHON_VERSION)
    logger.info("Current Python version: %s", platform.python_version())
    logger.info("Interpreter: %s", sys.executable)


def check_python_version() -> None:
    if sys.version_info[:2] < MIN_PYTHON:
        raise RuntimeError(
            f"Python {MIN_PYTHON_VERSION} or higher is required, "
            f"but this interpreter is {platform.python_version()}."
        )


def prompt_yes_no(question: str) -> bool:
    return input(f"{question} (y/n): ").strip().lower() in {"y", "yes"}


def is_installed(distribution: str) -> bool:
    try:
        importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return False
    return True


def install(distribution: str, upgrade: bool, logger: logging.Logger) -> bool:
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


def install_required_packages(logger: logging.Logger) -> list[str]:
    failed = []
    for distribution in REQUIRED_PACKAGES:
        upgrade = is_installed(distribution)
        if upgrade:
            logger.info("%s is already installed, checking for updates...", distribution)
        if not install(distribution, upgrade, logger):
            failed.append(distribution)
    return failed


def main(logger: logging.Logger, assume_yes: bool) -> int:
    logger.info("Checking Python version...")
    describe_environment(logger)
    check_python_version()

    if not assume_yes and not prompt_yes_no("Do you want to install the required documentation packages?"):
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
    parser.add_argument("--no-pause", action="store_true", help="Do not wait for Enter on exit.")
    args = parser.parse_args(argv)

    logger = setup_logging()
    try:
        exit_code = main(logger, args.yes)
    except Exception as error:
        logger.error("Error: %s", error, exc_info=True)
        exit_code = 1

    if not args.no_pause:
        pause()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(run())
