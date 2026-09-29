"""Shared helpers for the scripts in .github/scripts.

Only Python modules live here. Configuration comes from the single ``.env``
file one level up, read through :mod:`functions.env_utils`; a missing ``.env``
is not an error, the built-in defaults simply apply, which is what keeps these
scripts working on CI where only the checked-in ``.env.example`` exists.
"""

from __future__ import annotations
