"""GitHub Actions awareness shared by the four CI scripts.

The nightly pipeline has a master toggle, and both nightly scripts honour it so
a paused pipeline can neither create nor delete an archive. Keeping the toggle
and the ``GITHUB_ACTIONS`` check together means the two scripts can never drift
apart, and the workflow's import-time gate keeps working against the same
attribute name it has always used.
"""

from __future__ import annotations

import os
import subprocess

from functions import env_utils

# Master toggle for the GitHub Actions nightly pipeline, moved into .env:
#   NIGHTLY_BUILDS_ENABLED=true  -> CI builds, commits and pushes the snapshot.
#   NIGHTLY_BUILDS_ENABLED=false -> the pipeline short-circuits; nothing is
#                                  built or pushed. Local and manual runs are
#                                  NOT affected, only GitHub Actions.
#
# The old name is kept as an alias because .github/workflows reads it directly.
BUILDS_ENABLED = env_utils.get_bool("NIGHTLY_BUILDS_ENABLED", False)

CI_ENV_VAR = "GITHUB_ACTIONS"
CI_ENV_VALUE = "true"


def in_ci() -> bool:
    """True when running inside GitHub Actions."""
    return os.environ.get(CI_ENV_VAR) == CI_ENV_VALUE


def short_sha() -> str | None:
    """First 8 chars of HEAD, or None when git cannot answer."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short=8", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return (result.stdout or "").strip()[:8] or None
