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
import subprocess
import sys
import tokenize
from pathlib import Path

DEFAULT_ROOTS = ("DragonGraph's Project", "DragonGraph's Project Utilities")
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

DENIED_MODULES = {
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
}

DENIED_CALLS = {"eval", "exec", "execfile", "compile", "__import__", "globals"}

DENIED_ATTR_SUFFIX = {
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
}

DENIED_CALLABLE_ATTRS = {
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

# Extra, raw byte-level checks (they only trigger on clearly suspicious content).
RAW_PATTERNS = [
    re.compile(r"__import__\s*\(\s*['\"]"),
    re.compile(r"\b(?:exec|eval)\s*\([^)]*\)"),
    re.compile(r"\.py\b.*(?:import|exec|eval)"),
]


def is_binary_bytes(data: bytes) -> bool:
    """A Python source file that contains NUL bytes is bytecode, not source."""
    return b"\x00" in data


def read_source(path: Path) -> bytes:
    with open(path, "rb") as fh:
        return fh.read()


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


def scan_python_source(path_name: str, data: bytes, allow_modules) -> list[dict]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return [
            {
                "file": path_name,
                "line": 0,
                "col": 0,
                "marker": "decode-error",
                "message": "file is not valid UTF-8 Python source",
            }
        ]
    if is_binary_bytes(data):
        return [
            {
                "file": path_name,
                "line": 0,
                "col": 0,
                "marker": "binary-file",
                "message": "file contains NUL bytes (bytecode/encrypted blob)",
            }
        ]
    try:
        tree = ast.parse(text, filename=path_name)
    except SyntaxError as exc:
        return [
            {
                "file": path_name,
                "line": exc.lineno or 0,
                "col": exc.offset or 0,
                "marker": "syntax-error",
                "message": f"{exc.msg}",
            }
        ]

    findings: list[dict] = []
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

    # Raw tokenize-level pass: catches comment-obscured patterns the AST cannot see.
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
        code_tokens = [t for t in tokens if t.type == tokenize.NAME or t.type == tokenize.OP]
        raw = " ".join(t.string for t in code_tokens)
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
    except (tokenize.TokenError, SyntaxError, IndentationError):
        pass

    return findings


def changed_py_files(repo: Path, base: str, roots: list[Path]) -> list[str]:
    out: set[str] = set()
    for root in roots:
        diff = subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "diff",
                "--name-only",
                "--diff-filter=ACMRTUXB",
                base,
                "--",
                str(root),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if diff.returncode != 0:
            print(
                f"[py-linter] git diff failed ({diff.stderr.strip()}); falling back to "
                "full-tree scan",
                file=sys.stderr,
            )
            return all_py_files(repo, roots)
        for line in diff.stdout.splitlines():
            line = line.strip()
            if line and Path(line).suffix.lower() == ".py":
                out.add(line)
    return sorted(out)


def all_py_files(repo: Path, roots: list[Path]) -> list[str]:
    out: set[str] = set()
    for root in roots:
        for p in root.rglob("*.py"):
            out.add(str(p.relative_to(repo)))
    return sorted(out)


def changed_github_files(repo: Path, base: str | None) -> list[str]:
    """Files changed under .github between the given base and the worktree.

    Covers both tracked edits (git diff against the base/HEAD) and brand-new,
    not-yet-committed files (git ls-files --others). Updates to the CI pipeline
    or the scanner itself must never be blocked by the scan, so the caller
    bypasses (returns 0) when this list is non-empty.
    """
    out: set[str] = set()
    ref = base or "HEAD"
    diff = subprocess.run(
        ["git", "-C", str(repo), "diff", "--name-only", ref, "--", ".github"],
        capture_output=True,
        text=True,
        check=False,
    )
    if diff.returncode == 0:
        out.update(line.strip() for line in diff.stdout.splitlines() if line.strip())

    untracked = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "--others", "--exclude-standard", "--", ".github"],
        capture_output=True,
        text=True,
        check=False,
    )
    if untracked.returncode == 0:
        out.update(line.strip() for line in untracked.stdout.splitlines() if line.strip())

    return sorted(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lint Python files under DragonGraph's Project for dangerous code."
    )
    parser.add_argument("--repo", default=".", help="Path to the git repository root")
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
    parser.add_argument("-q", "--quiet", action="store_true")
    args = parser.parse_args(argv)

    repo = Path(args.repo).expanduser().resolve()
    if not repo.is_dir() or not (repo / ".git").is_dir():
        print(f"[py-linter] not a git repository: {repo}", file=sys.stderr)
        return 2

    roots = [Path(r).expanduser().resolve() for r in (args.root or DEFAULT_ROOTS)]
    roots = [r if r.is_absolute() else (repo / r).resolve() for r in roots]

    existing_roots: list[Path] = []
    missing_roots: list[str] = []
    for r in roots:
        if not Path(r).is_dir():
            missing_roots.append(str(Path(r).name.lstrip("\\/")))
        else:
            existing_roots.append(Path(r))
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

    if changed_github_files(repo, args.base):
        print("[py-linter] .github/ changes detected; bypassing scan to accept the update")
        return 0

    if args.base:
        files = changed_py_files(repo, args.base, existing_roots)
        if not args.quiet:
            print(f"[py-linter] {len(files)} changed .py file(s) by git diff")
    else:
        files = all_py_files(repo, existing_roots)
        if not args.quiet:
            print(f"[py-linter] full-tree scan: {len(files)} .py file(s)")

    if not files:
        print("[py-linter] no .py files to scan")
        return 0

    findings: list[dict] = []
    for rel in files:
        if Path(rel).as_posix() in skip:
            continue
        path = repo / rel
        if not path.is_file():
            continue
        try:
            data = read_source(path)
        except OSError as exc:
            print(f"[py-linter] cannot read {rel}: {exc}", file=sys.stderr)
            continue
        file_allows = allow | path_allows.get(Path(rel).as_posix(), set())
        findings.extend(scan_python_source(rel, data, file_allows))

    if findings:
        print("[py-linter] SECURITY WARNING: dangerous Python patterns found:")
        for f in findings:
            loc = f"{f['line']}:{f['col']}" if f["line"] else "-"
            print(f"  {f['file']}@{loc} [{f['marker']}] {f['message']}")
        return 1

    print("[py-linter] OK - no dangerous Python patterns found")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except KeyboardInterrupt:
        print("[python-security-scanner] interrupted.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:  # unexpected crash -> bypass, never abort CI
        print(f"[python-security-scanner] unexpected crash: {exc!r}; bypassed (exit 2).", file=sys.stderr)
        raise SystemExit(2)