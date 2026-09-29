#!/usr/bin/env python3
"""Resolve the nightly master toggle and fail fast when it cannot be read.

The workflow calls this as the first step of ``security-scan`` and publishes the
result as the ``nightly_enabled`` job output. ``build-and-deploy`` only runs
when that output is ``true``.

Exit codes are deliberately distinct, because "no builds tonight" and "I could
not determine whether to build" must never be confused:

    0  the toggle was read successfully. It is either true or false, and
       ``nightly_enabled`` says which.
    1  the toggle could NOT be resolved: .env is unreadable, the key is absent,
       or the value is not a recognised boolean. This is a hard failure so a
       broken gate can never quietly disable or enable a publishing pipeline.

A false toggle is NOT an error and does not fail anything. Failing the build on
a deliberate pause would block every unrelated pull request, which is the
opposite of what the security gate is for. Only a confirmed scan violation
blocks a merge, and only this script's inability to read the toggle blocks the
pipeline itself.

``NIGHTLY_BUILDS_ENABLED`` in the real process environment overrides the file,
so a maintainer can also force one run with
``NIGHTLY_BUILDS_ENABLED=true python gate_check.py``.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:  # importable from any working directory
    sys.path.insert(0, str(_SCRIPT_DIR))

from functions import env_utils  # noqa: E402

TOGGLE_KEY = "NIGHTLY_BUILDS_ENABLED"
OUTPUT_NAME = "nightly_enabled"


def _set_github_output(name: str, value: str) -> None:
    """Append to $GITHUB_OUTPUT when running as a step. Never fatal."""
    target = os.environ.get("GITHUB_OUTPUT")
    if not target:
        return
    try:
        with open(target, "a", encoding="utf-8") as handle:
            handle.write(f"{name}={value}\n")
    except OSError as exc:
        print(f"[gate] could not write {target}: {exc}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Resolve NIGHTLY_BUILDS_ENABLED, failing if it cannot be read."
    )
    parser.add_argument(
        "--unset-is-enabled",
        action="store_true",
        help="Treat a missing key as enabled instead of an error. Off by default: "
        "an absent toggle should stop the pipeline, not guess.",
    )
    args = parser.parse_args(argv)

    source = "unknown"
    try:
        source = env_utils.source_description()
    except Exception as exc:  # noqa: BLE001 - source_description must never block
        source = f"unreadable ({exc!r})"

    # Deliberately stricter than the rest of the scripts, which all fall back to
    # a default when a key is missing. A publishing toggle is the one setting
    # where "I could not tell" must never be rounded to "carry on".
    try:
        is_set = env_utils.is_set(TOGGLE_KEY)
    except Exception as exc:  # noqa: BLE001
        print(f"[gate] FATAL: could not read {TOGGLE_KEY}: {exc!r}", file=sys.stderr)
        return 1

    if not is_set:
        if not args.unset_is_enabled:
            print(
                f"[gate] FATAL: {TOGGLE_KEY} is not set in {source}.\n"
                f"[gate] Add '{TOGGLE_KEY}=false' to .github/scripts/.env to pause "
                f"the pipeline deliberately, or pass --unset-is-enabled to treat "
                f"it as enabled.",
                file=sys.stderr,
            )
            return 1
        _set_github_output(OUTPUT_NAME, "true")
        print(f"[gate] Settings: {source}")
        print(
            f"[gate] {TOGGLE_KEY} is unset and --unset-is-enabled was passed "
            f"-> nightly_enabled=true"
        )
        return 0

    try:
        raw_value = env_utils.raw(TOGGLE_KEY, "").strip()
    except Exception as exc:  # noqa: BLE001
        print(f"[gate] FATAL: could not read the value of {TOGGLE_KEY}: {exc!r}", file=sys.stderr)
        return 1

    if not raw_value:
        print(
            f"[gate] FATAL: {TOGGLE_KEY} is present but empty in {source}. "
            f"Use true or false.",
            file=sys.stderr,
        )
        return 1

    parsed = env_utils.parse_bool(raw_value)
    if parsed is None:
        print(
            f"[gate] FATAL: {TOGGLE_KEY}={raw_value!r} in {source} is not a boolean. "
            f"Use one of: true, false, 1, 0, yes, no, on, off.",
            file=sys.stderr,
        )
        return 1
    enabled = parsed
    _set_github_output(OUTPUT_NAME, "true" if enabled else "false")
    print(f"[gate] Settings: {source}")
    print(f"[gate] {TOGGLE_KEY} = {str(enabled).lower()} -> {OUTPUT_NAME}={str(enabled).lower()}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except KeyboardInterrupt:
        print("[gate] interrupted.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:  # unexpected crash -> fail closed
        print(f"[gate] unexpected crash: {exc!r}; treating the toggle as unreadable.", file=sys.stderr)
        raise SystemExit(1)
