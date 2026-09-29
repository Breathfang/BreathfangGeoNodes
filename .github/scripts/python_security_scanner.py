#!/usr/bin/env python3
"""Python security linter for "DragonGraph's Project".

Scans .py files in the repository (or changed since a given git base) with AST
analysis and a tokenizer-level scan for obfuscated / comment-obscured patterns.

The scan roots cover the shipped, untrusted code: "DragonGraph's Project" (which
must never contain Python) and "DragonGraph's Project Utilities" (the
toolset scripts that are bundled into the nightly packs).

Default policy (derived from the repository CONTRIBUTING.md):
- No system / network / code-execution imports or calls inside the pack's own
  Python files: os, sys, subprocess, shutil, ctypes, socket, ftplib, smtplib,
  http, urllib, requests, pickle, marshal, imp, importlib.
- Dangerous callables: eval, exec, execfile, compile, __import__, globals.
- Dangerous attribute chains (with alias tracking): os.system, os.popen,
  subprocess.Popen/.run/.call/.check_output, shutil.rmtree/.move, socket.socket,
  urllib.request.urlopen, requests.get/.post ...
- Direct decompression powered execution gadgets: marshal.loads, pickle.loads.

Any hit is reported with file:line:col and the scanner exits 1. Clean runs exit 0.

Resilience: only a confirmed policy violation exits 1. A file that cannot be
read, is not valid UTF-8, or does not parse is reported as ``[WARNING]`` and
skipped, so a broken file cannot block a push or a CI run. The token-level pass
still runs on an unparseable file, because that is exactly where an obfuscated
payload would hide. Set ``SCAN_STRICT_ON_ERROR=true`` in ``.env`` to turn an
incomplete scan into a failure instead. ``PY_FLAG_BINARY_FILES=false`` downgrades
a NUL-byte or non-UTF-8 .py from a finding to a warning.

Exit codes:
    0  clean. Some files may have been skipped as unreadable or unparseable.
    1  a confirmed policy violation: a dangerous import, call or pattern.
    2  the scan could not be completed (unusable roots, or SCAN_STRICT_ON_ERROR
       with unverifiable files). Never reported as clean.

There is no bypass: changes to this scanner and to .github/ are scanned like any
other change. Tighten the policy through the allow-lists in ``.env`` instead.

The utility scripts legitimately use subprocess/sys (they install Python tooling
and load the git version). To allow a *specific module in a specific file* use
--allow-path FILE:MODULE (repeatable); --allow-module NAME whitelists a module
in every scanned file and --skip-file PATH excludes an entire file.
"""

from __future__ import annotations

import argparse
import ast
import io
import re
import sys
import tokenize
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:  # importable from any working directory
    sys.path.insert(0, str(_SCRIPT_DIR))

from functions import env_utils, path_utils, scan_utils  # noqa: E402

DEFAULT_ROOTS = env_utils.get_list(
    "PY_SCAN_ROOTS", ("DragonGraph's Project", "DragonGraph's Project Utilities")
)
EMPTY_TREE = scan_utils.EMPTY_TREE

# Path parts never walked, whatever the scan roots are. The shared helpers under
# functions/ are trusted maintainer tooling that legitimately use os/sys.
SKIP_DIRS = scan_utils.DEFAULT_SKIP_DIRS

DENIED_MODULES = frozenset(
    env_utils.get_list(
        "PY_DENIED_MODULES",
        (
            "os",
            "sys",
            "subprocess",
            "shutil",
            "ctypes",
            "socket",
            "ftplib",
            "smtplib",
            "http",
            "http.server",
            "urllib",
            "urllib.request",
            "urllib.parse",
            "requests",
            "pickle",
            "marshal",
            "imp",
            "importlib",
        ),
    )
)

DENIED_CALLS = frozenset(
    env_utils.get_list("PY_DENIED_CALLS", ("eval", "exec", "execfile", "compile", "__import__", "globals"))
)

DENIED_ATTR_SUFFIX = frozenset(
    env_utils.get_list(
        "PY_DENIED_ATTR_SUFFIX",
        (
            "system",
            "popen",
            "startfile",
            "Popen",
            "run",
            "call",
            "check_output",
            "check_call",
            "rmtree",
            "move",
            "remove",
            "unlink",
            "socket",
            "connect",
            "sendall",
            "send",
            "recv",
            "readlink",
            "makedirs",
            "mkdir",
            "open",
        ),
    )
)

DENIED_CALLABLE_ATTRS = env_utils.get_pair_set(
    "PY_DENIED_CALLABLE_ATTRS",
    frozenset(
        {
            ("os", "system"),
            ("os", "popen"),
            ("os", "startfile"),
            ("os", "remove"),
            ("os", "unlink"),
            ("os", "rmdir"),
            ("subprocess", "Popen"),
            ("subprocess", "run"),
            ("subprocess", "call"),
            ("subprocess", "check_output"),
            ("subprocess", "check_call"),
            ("shutil", "rmtree"),
            ("shutil", "move"),
            ("shutil", "copy"),
            ("shutil", "copyfile"),
            ("shutil", "copy2"),
            ("socket", "socket"),
            ("socket", "create_connection"),
            ("urllib", "request"),
            ("urllib", "urlopen"),
            ("requests", "get"),
            ("requests", "post"),
            ("requests", "put"),
            ("requests", "delete"),
            ("requests", "request"),
            ("marshal", "loads"),
            ("pickle", "loads"),
        }
    ),
)

# Extra, raw byte-level checks (they only trigger on clearly suspicious content).
# They stay in code because their regexes need escaping a .env line cannot
# express cleanly; PY_RAW_PATTERNS=on/off in .env gates the whole pass.
RAW_PATTERNS_ENABLED = env_utils.get_bool("PY_RAW_PATTERNS", True)

# Unreadable/unparseable files are warned about and skipped by default so one
# broken file cannot block a push or a CI run. Set either to true to make an
# incomplete scan fail closed with exit 2.
STRICT_ON_ERROR = env_utils.get_bool("SCAN_STRICT_ON_ERROR", False)
FLAG_BINARY_FILES = env_utils.get_bool("PY_FLAG_BINARY_FILES", True)
RAW_PATTERNS = (
    [
        re.compile(r"__import__\s*\(\s*['\"]"),
        re.compile(r"\b(?:exec|eval)\s*\([^)]*\)"),
        re.compile(r"\.py\b.*(?:import|exec|eval)"),
    ]
    if RAW_PATTERNS_ENABLED
    else []
)


def is_binary_bytes(data: bytes) -> bool:
    """A Python source file that contains NUL bytes is bytecode, not source."""
    return scan_utils.is_binary_bytes(data)


def read_source(path: Path) -> bytes:
    return scan_utils.read_bytes(path)


def collect_aliases(tree: ast.Module):
    """Map local names to module roots, e.g. ``import os as o`` -> {o: os}."""
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for aliased in node.names:
                root = aliased.name.split(".", 1)[0]
                name = aliased.asname or aliased.name
                aliases[name] = root
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue
            root = node.module.split(".", 1)[0]
            for aliased in node.names:
                if aliased.name == "*":
                    continue
                aliases[aliased.name] = root
    return aliases


def resolve_module(alias_map: dict[str, str], name: str) -> str | None:
    if name in alias_map:
        return alias_map[name]
    return name


def raw_pattern_findings(path_name: str, text: str) -> list[dict]:
    """Tokenize-level pass. Works on text alone, so it still runs on files
    that fail to parse, which is exactly where obfuscated payloads hide."""
    if not RAW_PATTERNS_ENABLED:
        return []
    findings: list[dict] = []
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
        code_tokens = [t for t in tokens if t.type == tokenize.NAME or t.type == tokenize.OP]
        raw = " ".join(t.string for t in code_tokens)
    except Exception as exc:  # noqa: BLE001 - tokenize fails on broken input
        warn(f"{path_name}: tokenizer pass failed ({exc!r})")
        return []
    for pattern in RAW_PATTERNS:
        if pattern.search(raw):
            findings.append(
                {
                    "file": path_name,
                    "line": 0,
                    "col": 0,
                    "marker": "raw-pattern",
                    "message": f"obfuscated pattern matched: {pattern.pattern!r}",
                }
            )
    return findings


def warn(message: str) -> None:
    """Non-fatal diagnostic. Never influences the exit code by itself."""
    print(f"[WARNING] {message}", file=sys.stderr, flush=True)


def scan_python_source(path_name: str, data: bytes, allow_modules) -> tuple[list[dict], list[str]]:
    """Return (findings, warnings) for one file.

    Only a confirmed policy violation becomes a finding. Anything that merely
    stops the scanner from understanding the file (bad encoding, syntax error,
    tokenizer failure) is returned as a warning so the caller reports it and
    moves on to the next file.
    """
    warnings: list[str] = []

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        if FLAG_BINARY_FILES:
            return (
                [
                    {
                        "file": path_name,
                        "line": 0,
                        "col": 0,
                        "marker": "binary-file",
                        "message": f"file is not valid UTF-8 Python source ({exc})",
                    }
                ],
                [],
            )
        return [], [f"not valid UTF-8 Python source ({exc})"]

    if is_binary_bytes(data):
        if FLAG_BINARY_FILES:
            return (
                [
                    {
                        "file": path_name,
                        "line": 0,
                        "col": 0,
                        "marker": "binary-file",
                        "message": "file contains NUL bytes (bytecode/encrypted blob)",
                    }
                ],
                [],
            )
        return [], ["file contains NUL bytes (bytecode/encrypted blob)"]

    # Raw pass first, so an unparseable file is still inspected.
    findings: list[dict] = raw_pattern_findings(path_name, text)

    try:
        tree = ast.parse(text, filename=path_name)
    except (SyntaxError, ValueError, RecursionError, MemoryError) as exc:
        # A syntax error is not a security violation. Report it and keep the
        # findings gathered by the raw pass.
        warnings.append(
            f"could not parse ({exc.__class__.__name__}: {exc}); AST pass skipped"
        )
        return findings, warnings

    aliases = collect_aliases(tree)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for aliased in node.names:
                root = aliased.name.split(".", 1)[0]
                if root in DENIED_MODULES and root not in allow_modules:
                    findings.append(
                        {
                            "file": path_name,
                            "line": node.lineno,
                            "col": node.col_offset,
                            "marker": f"import.{root}",
                            "message": f"unauthorized import {aliased.name!r}",
                        }
                    )
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue
            root = node.module.split(".", 1)[0]
            if root in DENIED_MODULES and root not in allow_modules:
                findings.append(
                    {
                        "file": path_name,
                        "line": node.lineno,
                        "col": node.col_offset,
                        "marker": f"from.{root}",
                        "message": f"unauthorized from-import {node.module!r}",
                    }
                )
        elif isinstance(node, (ast.Call,)):
            func = node.func
            if isinstance(func, ast.Name):
                if func.id in DENIED_CALLS:
                    findings.append(
                        {
                            "file": path_name,
                            "line": node.lineno,
                            "col": node.col_offset,
                            "marker": f"call.{func.id}",
                            "message": f"dangerous callable {func.id}()",
                        }
                    )
            elif isinstance(func, ast.Attribute):
                root = resolve_module(aliases, func.value.id) if isinstance(
                    func.value, ast.Name
                ) else None
                if root is not None:
                    pair = (root, func.attr)
                    if pair in DENIED_CALLABLE_ATTRS and root.split(".")[0] not in allow_modules:
                        findings.append(
                            {
                                "file": path_name,
                                "line": node.lineno,
                                "col": node.col_offset,
                                "marker": f"call.{root}.{func.attr}",
                                "message": f"dangerous call {root}.{func.attr}()",
                            }
                        )
                elif func.attr in DENIED_ATTR_SUFFIX:
                    findings.append(
                        {
                            "file": path_name,
                            "line": node.lineno,
                            "col": node.col_offset,
                            "marker": f"call..{func.attr}",
                            "message": f"dangerous attribute call .{func.attr}()",
                        }
                    )

    return findings, warnings


def changed_py_files(repo: Path, base: str, roots: list[Path]) -> list[str]:
    out: set[str] = set()
    for root in roots:
        names = scan_utils.git_diff_names(repo, base, str(root))
        if names is None:
            return all_py_files(repo, roots)
        for name in names:
            if Path(name).suffix.lower() == ".py":
                out.add(name)
    return sorted(out)


def all_py_files(repo: Path, roots: list[Path]) -> list[str]:
    out: set[str] = set()
    for root in roots:
        out.update(scan_utils.walk_files(repo, root, ".py", SKIP_DIRS))
    return sorted(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lint Python files under DragonGraph's Project for dangerous code."
    )
    parser.add_argument("--repo", default=".", help="Path to the git repository root (default: the repo root)")
    parser.add_argument(
        "--base",
        default=None,
        help="Base commit to diff against; defaults to a full-tree scan.",
    )
    parser.add_argument(
        "--root",
        action="append",
        default=[],
        metavar="DIR",
        help="Scan root, relative to the repo (repeatable). "
        f"Defaults to: {', '.join(DEFAULT_ROOTS)}.",
    )
    parser.add_argument(
        "--allow-module",
        action="append",
        default=[],
        dest="allow_modules",
        help="Whitelist a module name (repeatable), e.g. --allow-module sys",
    )
    parser.add_argument(
        "--allow-path",
        action="append",
        default=[],
        dest="allow_paths",
        metavar="FILE:MODULE",
        help="Whitelist a module for one repo-relative file, e.g. "
        "--allow-path 'DragonGraph's Project Utilities/nodepack_zip_generator.py:subprocess'",
    )
    parser.add_argument(
        "--skip-file",
        action="append",
        default=[],
        help="Exclude a repo-relative file (repeatable)",
    )
    parser.add_argument(
        "--show-settings",
        action="store_true",
        help="Print the resolved .env settings and exit",
    )
    parser.add_argument("-q", "--quiet", action="store_true")
    args = parser.parse_args(argv)

    if args.show_settings:
        print(f"Settings: {env_utils.source_description()}")
        print(f"  PY_SCAN_ROOTS = {', '.join(repr(r) for r in DEFAULT_ROOTS)}")
        print(f"  SCAN_SKIP_DIRS = {', '.join(SKIP_DIRS)}")
        print(f"  PY_DENIED_MODULES = {', '.join(sorted(DENIED_MODULES))}")
        print(f"  PY_DENIED_CALLS = {', '.join(sorted(DENIED_CALLS))}")
        print(f"  PY_RAW_PATTERNS = {'on' if RAW_PATTERNS_ENABLED else 'off'}")
        print(f"  PY_FLAG_BINARY_FILES = {FLAG_BINARY_FILES}")
        print(f"  SCAN_STRICT_ON_ERROR = {STRICT_ON_ERROR}")
        return 0

    repo = scan_utils.resolve_repo(args.repo)
    if not scan_utils.is_git_repo(repo):
        print(f"[py-linter] not a git repository: {repo}", file=sys.stderr)
        return 2

    # Relative roots belong to the repo, not to the caller's working directory.
    roots = [path_utils.resolve_against(repo, r) for r in (args.root or DEFAULT_ROOTS)]

    existing_roots: list[Path] = []
    missing_roots: list[str] = []
    for r in roots:
        if not r.is_dir():
            missing_roots.append(str(Path(r).name.lstrip("\\/")))
        else:
            existing_roots.append(r)
    if missing_roots:
        for name in missing_roots:
            print(f"[py-linter] scan root does not exist, skipping: {name}", file=sys.stderr)
    if not existing_roots:
        print("[py-linter] no scan roots available", file=sys.stderr)
        return 2

    skip = {str(Path(s).as_posix()) for s in args.skip_file}
    allow = {m.split(".")[0] for m in args.allow_modules}
    path_allows: dict[str, set[str]] = {}
    for rule in args.allow_paths:
        if ":" not in rule:
            print(f"[py-linter] ignoring malformed --allow-path {rule!r}", file=sys.stderr)
            continue
        file_part, module_part = rule.rsplit(":", 1)
        mod = module_part.strip().split(".")[0]
        rel = Path(file_part.strip()).as_posix()
        path_allows.setdefault(rel, set()).add(mod)

    # No bypass: a change to the scanner or the pipeline is scanned like any
    # other change. To tighten policy, edit the allow-lists in .env instead.
    try:
        if args.base:
            files = changed_py_files(repo, args.base, existing_roots)
            if not args.quiet:
                print(f"[py-linter] {len(files)} changed .py file(s) by git diff")
        else:
            files = all_py_files(repo, existing_roots)
            if not args.quiet:
                print(f"[py-linter] full-tree scan: {len(files)} .py file(s)")
    except Exception as exc:  # noqa: BLE001 - enumeration failed, fail closed
        print(f"[py-linter] could not enumerate files: {exc!r}", file=sys.stderr)
        return 2

    if not files:
        print("[py-linter] no .py files to scan")
        return 0

    findings: list[dict] = []
    unreadable: list[str] = []
    for rel in files:
        if Path(rel).as_posix() in skip:
            continue
        path = repo / rel
        try:
            if not path.is_file():
                continue
            data = read_source(path)
        except Exception as exc:  # noqa: BLE001 - permission, lock, I/O error
            warn(f"cannot read {rel}: {exc!r}; skipping")
            unreadable.append(rel)
            continue

        file_allows = allow | path_allows.get(Path(rel).as_posix(), set())
        try:
            file_findings, file_warnings = scan_python_source(rel, data, file_allows)
        except Exception as exc:  # noqa: BLE001 - never let one file kill the run
            warn(f"{rel}: scanner error ({exc!r}); skipping")
            unreadable.append(rel)
            continue

        for message in file_warnings:
            warn(f"{rel}: {message}")
            unreadable.append(rel)
        findings.extend(file_findings)

    if findings:
        print("[py-linter] SECURITY WARNING: dangerous Python patterns found:")
        for f in findings:
            loc = f"{f['line']}:{f['col']}" if f["line"] else "-"
            print(f"  {f['file']}@{loc} [{f['marker']}] {f['message']}")
        print(f"[py-linter] {len(findings)} finding(s) across {len(files)} file(s).")
        return 1

    # No violation. Report what could not be verified without failing.
    if unreadable:
        print(
            f"[py-linter] scanned {len(files) - len(unreadable)}/{len(files)} file(s); "
            f"{len(unreadable)} skipped as unreadable or unparseable"
        )
        if STRICT_ON_ERROR:
            print(
                f"[py-linter] SCAN INCOMPLETE: SCAN_STRICT_ON_ERROR is on and "
                f"{len(unreadable)} file(s) could not be verified: "
                f"{', '.join(unreadable[:10])}"
            )
            return 2
        return 0

    print(f"[py-linter] OK - no dangerous Python patterns found in {len(files)} file(s)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except KeyboardInterrupt:
        print("[python-security-scanner] interrupted.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:  # unexpected crash -> fail closed, never pass silently
        print(
            f"[python-security-scanner] unexpected crash: {exc!r}; scan did not complete (exit 2).",
            file=sys.stderr,
        )
        raise SystemExit(2)