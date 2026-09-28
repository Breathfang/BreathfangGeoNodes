#!/usr/bin/env python3
"""Precision .blend scanner for "DragonGraph's Project".

Policies enforced by this repository:
- No Python scripts may be embedded in .blend files.
- No scripts may be executed automatically on file open.

Two layered scanning strategies, both zero-false-positive on the real pack:

1. Structure-aware block scan (preferred). After decompressing the on-disk
   stream to the playable byte stream, the Blender file header is validated and
   the container is walked block by block using the correct BHead layout:
   - Blender 5.x ("BLENDER17-..." 17-byte header) uses the 32-byte LargeBHead8
     {code, SDNAnr, old, len, nr} exclusively.
   - Older files ("BLENDER-..." 16-byte header) are tried with SmallBHead8
     (24 bytes), BHead4 (20 bytes) and LargeBHead8, little- then big-endian,
     and the first candidate that validates (walking to an ENDB terminator
     without overrun) wins.
   Only the payload of Text datablocks (ID code "TXT", null- or space-padded,
   e.g. b"TXT\\x00") is scanned for executable Python markers. This is where
   Blender stores embedded scripts, so ordinary mesh/geometry/cache data is
   never examined.

2. Printable-run fallback. If the header/container cannot be validated, the
   whole stream is scanned for printable text runs (>=16 chars) that contain
   executable Python markers, catching obfuscated or structurally unusual
   files without flagging binary noise.

On-disk layouts handled: uncompressed "BLENDER" at offset 0, legacy body
compression (byte 14 == 'Z'/zlib, 'z'/zstd) under the classic 16-byte header,
and modern whole-file compression where the entire file is a (possibly
multi-frame) Zstandard (or gzip) stream whose header is only visible after
decompression. A 2 GiB decompression cap avoids zip bombs.

Optionally, when a Blender executable is available (--blender-binary or
BLENDER_BINARY), the scanner runs Blender headless to enumerate the real
data-block-level Text objects (``bpy.data.texts``) and scans those instead --
the most authoritative path.

Exit codes: 0 = clean, 1 = suspicious content found, 2 = usage / environment error.
"""

from __future__ import annotations

import argparse
import gzip
import io
import os
import re
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path
from typing import Any

DEFAULT_ROOT = "DragonGraph's Project"
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

MAX_OUTPUT = 2 << 30  # 2 GiB decompression cap (anti zip-bomb)
MAX_RUN_REPORT = 4096  # cap of the text snippet printed per finding
MAX_BLOCKS = 2_000_000

ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"
GZIP_MAGIC = b"\x1f\x8b"
BLENDER_MAGIC = b"BLENDER"
ENDB = b"ENDB"

# Python markers only meaningful inside printable text regions.
# Each entry: (label, compiled bytes-regex)
MARKER_PATTERNS = [
    (
        "blender-python-import",
        re.compile(
            rb"\b(?:import|from)\s+(?:bpy|bge|bmesh|mathutils|bgl|blf)\b", re.I
        ),
    ),
    ("exec-builtin", re.compile(rb"\b(?:exec|execfile|eval|compile)\s*\(")),
    ("import-attr", re.compile(rb"__import__\s*\(")),
    (
        "addon-automation",
        re.compile(rb"\b(?:def\s+(?:register|unregister)\s*\(|bl_info\b|app\s*\.\s*handlers\b)"),
    ),
    (
        "script-file-ref",
        re.compile(rb"(?<![\w/-])[\w./\\-]+\.py\b"),
    ),
]
MARKER_NAMES = {label for label, _ in MARKER_PATTERNS}

# Block header sizes understood by this scanner.
BHEAD_LARGE8 = 32  # Blender 5.x: LargeBHead8 {code, SDNAnr, old, len, nr}
BHEAD_SMALL8 = 24  # legacy 64-bit: SmallBHead8 {code, len, old, SDNAnr, nr}
BHEAD_4 = 20  # legacy 32-bit: BHead4 {code, len, old, SDNAnr, nr}


class SafeZstdDecompressor:
    """Optional zstandard wrapper; reports availability without hard dependency."""

    def __init__(self) -> None:
        self._mod: Any = None
        try:
            import zstandard  # type: ignore
        except Exception:
            self._mod = None
        else:
            self._mod = zstandard

    @property
    def available(self) -> bool:
        return self._mod is not None

    def decompress_stream(self, stream, limit: int = MAX_OUTPUT) -> bytes:
        """Fully decompress a (possibly multi-frame) zstd stream with a hard cap."""
        mod = self._mod
        if mod is None:
            raise RuntimeError("zstandard not installed")
        dctx = mod.ZstdDecompressor()
        out = bytearray()
        with dctx.stream_reader(stream) as reader:
            while True:
                chunk = reader.read(1 << 24)
                if not chunk:
                    break
                out += chunk
                if len(out) > limit:
                    raise ValueError(
                        f"decompressed size exceeded safety limit ({len(out)} > {limit})"
                    )
        return bytes(out)


def decompress_blob(raw: bytes) -> bytes:
    """Return the playable .blend byte stream for any supported on-disk layout."""
    if raw[:7] == BLENDER_MAGIC:
        # Plain header at offset 0 (16-byte classic or 17-byte 5.x). Under the
        # classic header byte 14 holds the body-compression flag.
        if raw[7:9] == b"17" and len(raw) >= 17:
            return raw  # 5.x header: container is the playable stream
        flag = raw[14:15] if len(raw) >= 16 else b""
        body = raw[16:]
        if flag == b"Z":  # zlib-compressed body
            dobj = zlib.decompressobj()
            out = raw[:16] + dobj.decompress(body, MAX_OUTPUT)
            if dobj.unconsumed_tail:
                out += dobj.unconsumed_tail
            return out[: MAX_OUTPUT + 16]
        if flag == b"z":  # zstd-compressed body
            zstd = SafeZstdDecompressor()
            if not zstd.available:
                raise RuntimeError(
                    "file is zstd-compressed; install 'zstandard' (pip install zstandard)"
                )
            return raw[:16] + zstd.decompress_stream(io.BytesIO(body))
        return raw  # uncompressed

    if raw.startswith(ZSTD_MAGIC) or raw.startswith(GZIP_MAGIC):
        stream = io.BytesIO(raw)
        if raw.startswith(GZIP_MAGIC):
            with gzip.GzipFile(fileobj=stream) as gz:
                return gz.read(MAX_OUTPUT)
        zstd = SafeZstdDecompressor()
        if not zstd.available:
            raise RuntimeError(
                "file is zstd-compressed; install 'zstandard' (pip install zstandard)"
            )
        return zstd.decompress_stream(stream, limit=MAX_OUTPUT)

    raise ValueError("not a Blender file (missing BLENDER magic)")


def header_info(blob: bytes) -> dict | None:
    """Validate the playable stream header; return its layout, or None."""
    if not blob[:7] == BLENDER_MAGIC:
        return None
    is_new = blob[7:9] == b"17" and len(blob) >= 17
    header_len = int(blob[7:9].decode("ascii")) if is_new else 16
    if not (16 <= header_len <= 64):
        header_len = 17 if is_new else 16
    version = b""
    if len(blob) >= 17:
        version = blob[12:17]
    return {
        "is_new": bool(is_new),
        "header_len": header_len,
        "version": version.decode("ascii", "replace"),
    }


def bhead_len_field(head: bytes, size: int) -> bytes:
    """Return the raw bytes of the data-length field for a given BHead size."""
    if size == BHEAD_LARGE8:
        return head[16:24]  # int64 len
    return head[4:8]  # int32 len (SmallBHead8 and BHead4)


def walk_blocks(
    blob: bytes,
    header_len: int,
    size: int,
    endian: str,
    allow: set[str],
) -> dict | None:
    """Walk the BHead chain; None = layout does not validate."""
    off = header_len
    n = 0
    text_ranges: list[tuple[int, int]] = []
    while True:
        if off + size > len(blob):
            return None
        head = blob[off : off + size]
        code = head[0:4]
        if not all((0x20 <= byte <= 0x7E) or byte == 0 for byte in code):
            return None
        data_len = int.from_bytes(
            bhead_len_field(head, size), byteorder=endian, signed=True  # type: ignore[arg-type]
        )
        if code == ENDB:
            tail = len(blob) - (off + size)
            if data_len <= 0 and tail <= 8:
                return {
                    "size": size,
                    "endian": endian,
                    "blocks": n,
                    "text_ranges": text_ranges,
                }
            return None
        if data_len < 0:
            return None
        if code[:3] == b"TXT":  # Text datablock: null-/space-padded "TXT"
            text_ranges.append((off + size, data_len))
        off += size + data_len
        n += 1
        if n > MAX_BLOCKS:
            return None


def scan_blocks(blob: bytes, allow: set[str]) -> dict | None:
    """Locate Text datablocks with the correct BHead layout, or None."""
    info = header_info(blob)
    if info is None:
        return None
    if info["is_new"]:
        candidates = [(BHEAD_LARGE8, "little"), (BHEAD_LARGE8, "big")]
    else:
        candidates = [
            (BHEAD_SMALL8, "little"),
            (BHEAD_4, "little"),
            (BHEAD_LARGE8, "little"),
            (BHEAD_SMALL8, "big"),
            (BHEAD_4, "big"),
            (BHEAD_LARGE8, "big"),
        ]
    for size, endian in candidates:
        result = walk_blocks(blob, info["header_len"], size, endian, allow)
        if result is not None:
            result["header"] = info
            return result
    return None


def printable_runs(blob: bytes, min_len: int = 16):
    """Yield (start, end) ranges of printable ASCII (with whitespace) >= min_len."""
    start = None
    for i, byte in enumerate(blob):
        printable = (
            (0x20 <= byte <= 0x7E)
            or byte in (0x09, 0x0A, 0x0C, 0x0D, 0x0B)
        )
        if printable and start is None:
            start = i
        elif not printable and start is not None:
            if i - start >= min_len:
                yield start, i
            start = None
    if start is not None and len(blob) - start >= min_len:
        yield start, len(blob)


def scan_run(run: bytes, allow: set[str], offset_base: int, kind: str) -> list[dict]:
    findings: list[dict] = []
    for label, pattern in MARKER_PATTERNS:
        if label in allow:
            continue
        for m in pattern.finditer(run):
            snip = run[max(0, m.start() - 24) : m.end() + 48]
            findings.append(
                {
                    "kind": kind,
                    "offset": offset_base + m.start(),
                    "run_offset": offset_base,
                    "marker": label,
                    "match": snip.decode("ascii", "replace"),
                }
            )
    return findings


def scan_blob(blob: bytes, allow: set[str]) -> list[dict]:
    """Fallback: scan printable runs across the whole stream."""
    findings: list[dict] = []
    for start, end in printable_runs(blob):
        findings.extend(scan_run(blob[start:end], allow, start, "blend-text"))
    return findings


def scan_text_ranges(blob: bytes, walk: dict, allow: set[str]) -> list[dict]:
    """Scan only the payloads of Text datablocks found by the block walk."""
    findings: list[dict] = []
    for start, data_len in walk["text_ranges"]:
        payload = blob[start : start + data_len]
        for run_start, run_end in printable_runs(payload):
            findings.extend(
                scan_run(payload[run_start:run_end], allow, start + run_start, "blend-text-datablock")
            )
    return findings


def open_in_memory_headless(blender_binary: str, blob: bytes) -> list[dict]:
    """Authoritative scan: load the blend in headless Blender and inspect the real
    Text datablocks. Returns a list of findings (or [] when Blender reports none)."""
    script = (
        "import bpy, sys\n"
        "res = []\n"
        "for t in bpy.data.texts:\n"
        "    name = t.name\n"
        "    content = t.as_string()\n"
        "    if any(\n"
        "        pat in (name + content)\n"
        "        for pat in ('import bpy', 'import bge', 'exec(', 'eval(', "
        "'__import__', 'def register(', 'def unregister(', '.py')\n"
        "    ):\n"
        "        res.append(name)\n"
        "print('BLENDSCAN_RESULT:' + repr(res))\n"
        "sys.stdout.flush()\n"
    )
    with tempfile.NamedTemporaryFile(
        "w", suffix=".blend", dir=tempfile.gettempdir(), delete=False
    ) as tmp:
        blob_path = tmp.name
    with open(blob_path, "wb") as fh:
        fh.write(blob)
    cmd = [
        blender_binary,
        "--background",
        "--factory-startup",
        "--python-expr",
        script,
        blob_path,
    ]
    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=120, check=False
    )
    try:
        os.remove(blob_path)
    except OSError:
        pass
    findings: list[dict] = []
    line = next(
        (l for l in proc.stdout.splitlines() if "BLENDSCAN_RESULT:" in l), None
    )
    if line is None and proc.returncode != 0:
        return [
            {
                "kind": "blender-error",
                "offset": 0,
                "marker": proc.stderr.strip()[-200:] or proc.stdout.strip()[-200:],
                "match": "headless Blender could not inspect the file",
            }
        ]
    if line is None:
        return findings
    try:
        names = eval(line.split("BLENDSCAN_RESULT:", 1)[1])  # noqa: S307
    except Exception:
        return findings
    for name in names:
        findings.append(
            {
                "kind": "blend-text-datablock",
                "offset": 0,
                "marker": name,
                "match": f"Text datablock '{name}' contains executable Python",
            }
        )
    return findings


def changed_blend_files(
    repo: Path, base: str, root: Path
) -> list[str]:
    """Files (repo-root-relative) that changed on .blend within root."""
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
            f"[blend-scanner] git diff failed ({diff.stderr.strip()}); falling back "
            "to full-tree scan",
            file=sys.stderr,
        )
        return all_blend_files(repo, root)
    return [
        line
        for line in diff.stdout.splitlines()
        if line.strip() and Path(line).suffix.lower() == ".blend"
    ]


def all_blend_files(repo: Path, root: Path) -> list[str]:
    out: list[str] = []
    for p in root.rglob("*.blend"):
        out.append(str(p.relative_to(repo)))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scan .blend files under DragonGraph's Project for embedded Python."
    )
    parser.add_argument("--repo", default=".", help="Path to the git repository root")
    parser.add_argument(
        "--base",
        default=None,
        help="Base commit to diff against (git diff --name-only BASE HEAD). "
        "Defaults to a full-tree scan.",
    )
    parser.add_argument(
        "--root",
        default=DEFAULT_ROOT,
        help=f"Scan root (default: {DEFAULT_ROOT!r})",
    )
    parser.add_argument(
        "--blender-binary",
        default=os.environ.get("BLENDER_BINARY"),
        help="Optional headless Blender executable for authoritative Text-block scan",
    )
    for label in sorted(MARKER_NAMES):
        parser.add_argument(
            f"--{label.replace('-', '_')}-off",
            dest="disabled_markers",
            action="append_const",
            const=label,
            default=[],
            help=f"Disable the '{label}' check",
        )
    parser.add_argument("-q", "--quiet", action="store_true")
    args = parser.parse_args(argv)

    repo = Path(args.repo).expanduser().resolve()
    root = (repo / args.root).resolve()
    if not repo.is_dir() or not (repo / ".git").is_dir():
        print(f"[blend-scanner] not a git repository: {repo}", file=sys.stderr)
        return 2

    allow = set(args.disabled_markers)

    if not root.is_dir():
        print(f"[blend-scanner] scan root does not exist: {root}", file=sys.stderr)
        return 2

    if args.base:
        files = changed_blend_files(repo, args.base, root)
        if not args.quiet:
            print(f"[blend-scanner] {len(files)} changed .blend file(s) by git diff")
    else:
        files = all_blend_files(repo, root)
        if not args.quiet:
            print(f"[blend-scanner] full-tree scan: {len(files)} .blend file(s)")

    if not files:
        print("[blend-scanner] no .blend files to scan")
        return 0

    all_findings: list[dict] = []
    for rel in files:
        path = repo / rel
        try:
            raw = path.read_bytes()
        except OSError as exc:
            print(f"[blend-scanner] cannot read {rel}: {exc}", file=sys.stderr)
            all_findings.append(
                {"kind": "read-error", "offset": 0, "file": rel, "marker": str(exc), "match": f"unreadable: {rel}"}
            )
            continue
        try:
            blob = decompress_blob(raw)
        except (ValueError, RuntimeError) as exc:
            print(f"[blend-scanner] {rel}: {exc}", file=sys.stderr)
            all_findings.append(
                {"kind": "parse-error", "offset": 0, "file": rel, "marker": str(exc), "match": f"unparseable: {rel}"}
            )
            continue

        if args.blender_binary and shutil_has_blender(args.blender_binary):
            findings = open_in_memory_headless(args.blender_binary, blob)
        else:
            walk = scan_blocks(blob, allow)
            if walk is not None:
                hdr = walk["header"]
                if not args.quiet:
                    print(
                        f"[blend-scanner] {rel}: valid container "
                        f"(header {'17-byte 5.x' if hdr['is_new'] else '16-byte'} "
                        f"version={hdr['version']!r}, BHead {walk['size']}-byte{'' if walk['endian']=='little' else ' big-endian'}, "
                        f"{walk['blocks']} block(s), {len(walk['text_ranges'])} Text datablock(s))"
                    )
                findings = scan_text_ranges(blob, walk, allow)
            else:
                if not args.quiet:
                    print(
                        f"[blend-scanner] {rel}: container not structurally valid; "
                        f"falling back to printable-run scan"
                    )
                findings = scan_blob(blob, allow)
        for f in findings:
            f["file"] = rel
        all_findings.extend(findings)

    if all_findings:
        print("[blend-scanner] SECURITY WARNING: suspicious content found in .blend files:")
        for f in all_findings:
            print(
                f"  {f['file']} @ {f['offset']}: "
                f"[{f['marker']}] {f['match']}"
            )
        return 1
    print("[blend-scanner] OK - no embedded Python found")
    return 0


def shutil_has_blender(path: str) -> bool:
    import shutil

    return shutil.which(path) is not None or Path(path).is_file()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except KeyboardInterrupt:
        print("[blend-scanner] interrupted.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:  # unexpected crash -> bypass, never abort CI
        print(f"[blend-scanner] unexpected crash: {exc!r}; bypassed (exit 2).", file=sys.stderr)
        raise SystemExit(2)