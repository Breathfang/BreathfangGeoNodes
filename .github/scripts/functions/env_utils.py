"""Minimal ``.env`` reader for the .github/scripts tooling.

The one and only ``.env`` file for this folder lives next to the scripts, in
``.github/scripts/.env``. There is deliberately no ``.env`` inside this package
and no per-folder override: nightly_builder, nightly_cleaner, blend_scanner and
python_security_scanner all read the same file, and each setting falls back to
the default baked into the calling script when the key is absent, so the scripts
still run on CI where no ``.env`` is checked out.

Precedence, highest first:

1. a real environment variable (handy for one-off runs and for CI),
2. the ``.env`` file,
3. the default passed by the caller.

The format is the familiar ``KEY=VALUE`` one: ``#`` comments, blank lines and an
optional ``export`` prefix are ignored, and values may be wrapped in matching
single or double quotes. No interpolation, no multi-line values. List values are
comma-separated, and an individual item may be wrapped in double quotes when it
contains a comma of its own.
"""

from __future__ import annotations

import csv
import os
import re
from collections.abc import Iterable
from pathlib import Path

# Folder that holds the scripts, i.e. the parent of this package.
TOOL_ROOT = Path(__file__).resolve().parent.parent

ENV_FILENAME = ".env"

_TRUE_WORDS = frozenset({"1", "true", "yes", "on", "y"})
_FALSE_WORDS = frozenset({"0", "false", "no", "off", "n"})

# ".blend1-9" -> prefix ".blend", first 1, last 9
_SUFFIX_RANGE = re.compile(r"^(?P<prefix>.*?)(?P<start>\d+)-(?P<end>\d+)$")


def env_path() -> Path:
    """Absolute path of the folder-wide ``.env`` file."""
    return TOOL_ROOT / ENV_FILENAME


def _strip_quotes(value: str) -> str:
    """Unwrap a fully quoted value, leaving partially quoted ones alone.

    The inner check matters for list values such as ``"a b","c d"``: those start
    and end with a double quote but are not one quoted string, so they must
    survive for :func:`get_list` to split on the comma.
    """
    if len(value) < 2 or value[0] != value[-1] or value[-1] not in ("'", '"'):
        return value
    inner = value[1:-1]
    quote = value[0]
    escaped = False
    for char in inner:
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == quote:
            return value  # an unescaped inner quote: not a single quoted value
    return inner


def parse_env_text(text: str) -> dict[str, str]:
    """Turn the raw contents of a ``.env`` file into a mapping."""
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        key, separator, value = line.partition("=")
        if not separator:
            continue
        key = key.strip()
        if not key:
            continue
        values[key] = _strip_quotes(value.strip())
    return values


def load_env(path: Path | None = None) -> dict[str, str]:
    """Read the ``.env`` file; an unreadable or missing file yields ``{}``."""
    target = env_path() if path is None else path
    try:
        text = target.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return {}
    return parse_env_text(text)


_FILE_VALUES: dict[str, str] | None = None


def _values() -> dict[str, str]:
    """Parsed ``.env`` contents, read once per interpreter."""
    global _FILE_VALUES
    if _FILE_VALUES is None:
        _FILE_VALUES = load_env()
    return _FILE_VALUES


def reload_env() -> None:
    """Forget the cached ``.env`` contents so the next read hits the disk."""
    global _FILE_VALUES
    _FILE_VALUES = None


def raw(key: str, default: str = "") -> str:
    """Raw string value for ``key``, or ``default`` when it is not set."""
    found = os.environ.get(key)
    if found is not None:
        return found
    return _values().get(key, default)


def is_set(key: str) -> bool:
    """True when ``key`` comes from the environment or the ``.env`` file."""
    return key in os.environ or key in _values()


def get_str(key: str, default: str = "") -> str:
    value = raw(key, "").strip()
    return value or default


def parse_bool(value: str) -> bool | None:
    """Interpret a raw string as a boolean.

    Returns None when the value is empty or unrecognised, so a caller that must
    not guess (a publishing toggle, a security gate) can fail instead of
    silently inheriting a default.
    """
    value = value.strip().lower()
    if value in _TRUE_WORDS:
        return True
    if value in _FALSE_WORDS:
        return False
    return None


def get_bool(key: str, default: bool = False) -> bool:
    value = raw(key, "").strip().lower()
    if not value:
        return default
    if value in _TRUE_WORDS:
        return True
    if value in _FALSE_WORDS:
        return False
    return default


def get_int(key: str, default: int = 0) -> int:
    value = raw(key, "").strip()
    if not value:
        return default
    try:
        return int(value, 0)
    except ValueError:
        return default


def get_float(key: str, default: float = 0.0) -> float:
    value = raw(key, "").strip()
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def split_items(value: str) -> tuple[str, ...]:
    """Split a comma-separated value, honouring double quotes around items.

    ``csv`` does the heavy lifting so a list entry may itself contain a comma,
    as the scan roots do: ``"DragonGraph's Project","DragonGraph's Other"``.
    """
    try:
        fields = next(csv.reader([value], skipinitialspace=True))
    except (csv.Error, StopIteration):
        fields = value.split(",")
    return tuple(field.strip() for field in fields if field.strip())


def get_list(key: str, default: tuple[str, ...] = ()) -> tuple[str, ...]:
    """Comma-separated value as a tuple, with blank entries dropped."""
    value = raw(key, "").strip()
    if not value:
        return default
    return split_items(value) or default


def get_suffixes(key: str, default: tuple[str, ...] = ()) -> tuple[str, ...]:
    """Like :func:`get_list`, but expands ``.blend1-9`` style range tokens.

    Keeping the ranges compact matters because the autosave policy shows up in
    more than one setting and spelling out nine suffixes twice invites typos.
    """
    return expand_suffixes(get_list(key, default))


def expand_suffixes(items: Iterable[str]) -> tuple[str, ...]:
    """Expand every ``<prefix><start>-<end>`` token into individual suffixes."""
    expanded: list[str] = []
    for item in items:
        match = _SUFFIX_RANGE.fullmatch(item)
        if match is None:
            expanded.append(item.lower())
            continue
        prefix, start_text, end_text = match.groups()
        start, end = int(start_text), int(end_text)
        step = 1 if end >= start else -1
        expanded.extend(f"{prefix}{number}" for number in range(start, end + step, step))
    return tuple(expanded)


def get_pair_set(
    key: str, default: frozenset[tuple[str, str]] = frozenset()
) -> frozenset[tuple[str, str]]:
    """Parse ``a.b,c.d`` into a set of ``(root, attribute)`` pairs.

    Used for the security scanner's dangerous-callable table, which is nicer to
    scan and edit as one flat line than as a literal set of tuples.
    """
    value = raw(key, "").strip()
    if not value:
        return default
    pairs: set[tuple[str, str]] = set()
    for item in split_items(value):
        root, separator, attr = item.rpartition(".")
        if separator and root and attr:
            pairs.add((root, attr))
    return frozenset(pairs) or default


def source_description() -> str:
    """One-line summary for ``--help``-style banners and debug output."""
    path = env_path()
    count = len(_values())
    if not path.is_file():
        return f"no {ENV_FILENAME} at {path} (using built-in defaults)"
    return f"{path} ({count} setting(s), environment variables win)"
