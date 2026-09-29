"""Console prompt helpers shared by the interactive maintainer tools.

Kept in one place so the wizard scripts flush the same way and honour the same
``PAUSE_PROMPT`` setting, and so an IDE run with stdin closed is handled the
same way everywhere.
"""

from __future__ import annotations

import sys

from functions import env_utils

PAUSE_PROMPT = env_utils.get_str("PAUSE_PROMPT", "Press enter to exit...")


def prompt_read(prompt_text: str) -> str:
    """Print a prompt, flush it, then read one line from the user."""
    sys.stdout.write(prompt_text)
    sys.stdout.flush()
    return input().strip()


def ask(prompt: str, default: str | None = None) -> str:
    """Read one line of user input, accepting the bracketed default on empty."""
    prompt_text = f"{prompt}: " if default is None else f"{prompt} [{default}]: "
    return prompt_read(prompt_text) or default or ""


def ask_yes_no(question: str, default: bool = False) -> bool:
    """Yes/no question; empty input returns ``default``."""
    suffix = "[Y/n]" if default else "[y/N]"
    answer = prompt_read(f"{question} {suffix}: ").lower()
    if not answer:
        return default
    return answer in {"y", "yes"}


def pause() -> None:
    """Wait for Enter, but only on an interactive terminal."""
    if sys.stdin.isatty():
        input(PAUSE_PROMPT)


def pause_if_requested(no_pause: bool) -> None:
    """``--no-pause`` aware variant used by the script ``run()`` wrappers."""
    if not no_pause:
        pause()
