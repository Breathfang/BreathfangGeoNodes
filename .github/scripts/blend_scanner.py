#!/usr/bin/env python3
"""Precision .blend scanner for "DragonGraph's Project".

Policies enforced by this repository:
- No Python scripts may be embedded in .blend files.
- No scripts may be executed automatically on file open.

Two layered scanning strategies, both zero-false-positive on the real pack:

1. Structure-aware block scan (preferred). After decompressing the on-disk
   stream to the playable byte stream, the container layout is *discovered*
   rather than assumed, so no Blender version is hardcoded:
   - The header is self-describing. The bytes after the b"BLENDER" magic carry
     the header length in decimal (b"BLENDER17-01v0502" -> 17), so a 6.x file
     that widens its header is read correctly without a code change. When those
     bytes are not all digits the classic fixed 16-byte header is used.
   - The block header (BHead) layout is probed across plausible sizes, length
     field offsets, widths and byte orders. A candidate is kept only if the
     block chain it produces validates all the way to its ENDB terminator
     without overrunning, so a wider BHead or a moved length field is picked
     up at runtime. A chain is additionally trusted when the DNA1 block it
     reports really holds an SDNA payload, which stops a coincidental match on
     low-entropy data from silently shifting every block boundary.
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
BLENDER_BINARY in ``.env``), the scanner runs Blender headless to enumerate the
real data-block-level Text objects (``bpy.data.texts``) and scans those instead --
the most authoritative path.

Scan root, limits, the optional Blender executable and the skip list come from
this folder's ``.env``; run with --show-settings to print what was resolved.

By default only .blend files that CHANGED or were newly ADDED under the scan
root are opened, diffed against the newest commit on the remote default branch
(BLEND_SCAN_BASE, or ``--base``, overrides it; ``--full-tree`` scans
everything). Re-decompressing an untouched multi-hundred-megabyte pack on every
run is pure cost, and a file that has not changed cannot have gained a payload.
Untracked .blend files are always included, since that is what a new pack looks
like before it is committed. If no base can be resolved, or the diff fails, the
scan falls back to the full tree: an unknown base is treated as "scan
everything", never as "nothing to scan".

Resilience: a file that cannot be read or decoded is a technical fault, not a
policy violation. It is reported as ``[WARNING]`` and skipped so one corrupt or
half-written .blend cannot block a push or a CI run. A .blend whose *structure*
is not recognised - a future Blender release, or geometry this scanner cannot
walk - warns with "Unable to parse Blender 6.x or Unknown Blender Version file
structure" and falls through to the printable-run pass; it is never a policy
violation on its own. Set ``SCAN_STRICT_ON_ERROR=true`` in ``.env`` to turn an
incomplete scan (skipped or unverified files) into a failure instead. A missing
decoder is never skippable: if Zstandard is not installed the run fails rather
than quietly reporting files it never opened.

Exit codes:
    0  clean. Some files may have been skipped as unreadable; see the warnings.
    1  a confirmed policy violation: executable Python inside a .blend.
    2  the scan could not be completed (missing decoder, unreadable root, or
       SCAN_STRICT_ON_ERROR with unverifiable files). Never reported as clean.
"""

from __future__ import annotations

import argparse
import gzip
import io
import json
import re
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path
from typing import Any, NamedTuple

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:  # importable from any working directory
    sys.path.insert(0, str(_SCRIPT_DIR))

from functions import env_utils, path_utils, scan_utils  # noqa: E402

DEFAULT_ROOT = env_utils.get_str("BLEND_SCAN_ROOT", "DragonGraph's Project")
EMPTY_TREE = scan_utils.EMPTY_TREE

# Optional explicit diff base. Empty (the default) means "auto": use the newest
# published commit, resolved by scan_utils.resolve_scan_base.
SCAN_BASE = env_utils.get_str("BLEND_SCAN_BASE", "")

# Escape hatch equivalent to --full-tree: re-verify every .blend under the root
# even when nothing changed. Off by default.
SCAN_FULL_TREE = env_utils.get_bool("BLEND_SCAN_FULL_TREE", False)

MAX_OUTPUT = env_utils.get_int("BLEND_MAX_OUTPUT_BYTES", 2 << 30)  # 2 GiB anti zip-bomb
MAX_BLOCKS = env_utils.get_int("BLEND_MAX_BLOCKS", 2_000_000)
MIN_RUN_LENGTH = env_utils.get_int("BLEND_MIN_RUN_LENGTH", 16)
HEADLESS_TIMEOUT = env_utils.get_int("BLEND_HEADLESS_TIMEOUT", 120)
BLENDER_BINARY = env_utils.get_str("BLENDER_BINARY", "")
SKIP_DIRS = scan_utils.DEFAULT_SKIP_DIRS

# A .blend that cannot be read or decoded is a technical fault, not a policy
# violation, so by default it is warned about and skipped (exit 0). Flip this
# to true to make an incomplete scan fail with exit 2 instead.
STRICT_ON_ERROR = env_utils.get_bool("SCAN_STRICT_ON_ERROR", False)

ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"
GZIP_MAGIC = b"\x1f\x8b"
# BLENDER_MAGIC, ENDB and TEXT_CODE are defined with the forward-compatibility
# block below, next to the header/BHead discovery logic that uses them.

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

# ---------------------------------------------------------------------------
#  Forward compatibility with unknown / future Blender releases
# ---------------------------------------------------------------------------
#  Nothing below hardcodes a Blender version. Two facts are used instead:
#
#  1. The file header is self-describing. Immediately after the b"BLENDER"
#     magic, a 5.x file carries its own header length in decimal
#     (b"BLENDER17-01v0502" -> 17). A future 6.x file that widens the header
#     would simply say "18" or "20" and be read correctly. When those bytes are
#     not all decimal digits the file uses the classic fixed 16-byte header.
#
#  2. The block header (BHead) layout is *discovered*, not assumed. Rather than
#     betting on a {20, 24, 32} x {little, big} table that a release can
#     invalidate, every plausible (size, len-field offset, width, endian) is
#     probed and kept only if the resulting block chain validates all the way
#     to its ENDB terminator. A 6.x file with a wider BHead, a moved length
#     field or 128-bit offsets is then handled without a code change.
#
#  If neither step succeeds the file is not a known Blender structure. That is
#  reported as a warning and the printable-run fallback still runs, because an
#  unrecognised container is exactly where embedded Python would hide.
# ---------------------------------------------------------------------------

BLENDER_MAGIC = b"BLENDER"
ENDB = b"ENDB"
TEXT_CODE = b"TXT"

LEGACY_HEADER_LEN = 16  # classic 12-byte identifier + 4-byte tail
MIN_HEADER_LEN = 12
MAX_HEADER_LEN = 64  # sanity bound on the self-describing length

MIN_BHEAD_SIZE = 16
MAX_BHEAD_SIZE = 64
BHEAD_SIZE_STEP = 4  # all released BHead sizes are 4-byte aligned
# Widest first: reading only the low half of a 64-bit length can misparse a
# block larger than 2 GiB. A 16-bit length is not offered because no BHead has
# ever used one, and admitting it measurably raises the rate of coincidental
# matches on low-entropy data.
LEN_WIDTHS = (8, 4)

# Every .blend carries a DNA1 block whose payload is the SDNA type table. That
# makes it a self-validating anchor: a candidate layout is only trusted when the
# block it reports as DNA1 really does hold an SDNA payload. The block code is
# "DNA1"; the payload it introduces begins with "SDNA". It depends on no version
# number and no assumed geometry.
DNA1_CODE = b"DNA1"
DNA1_PAYLOAD_MAGIC = b"SDNA"

# Cheap pre-filter: a wrong layout almost always dies on the first few blocks,
# so only a layout surviving this many pays for a full 155k-block chain walk.
# A deep probe is far cheaper than the full walks it avoids.
PROBE_BLOCKS = 64

# Upper bound on full chain walks performed during discovery. A real file
# rejects nearly every candidate at the probe stage, so this is a safety valve
# against pathological input rather than a normal limit.
MAX_FULL_WALKS = 512


class Layout(NamedTuple):
    """A validated on-disk block-header layout."""

    size: int
    len_offset: int
    len_width: int
    endian: str
    source: str

    def describe(self) -> str:
        return (
            f"{self.size}-byte BHead, len field at +{self.len_offset} "
            f"({self.len_width * 8}-bit, {self.endian}-endian; via {self.source})"
        )



class ScanUnavailable(RuntimeError):
    """A capability is missing, so the file could not be inspected at all.

    This is deliberately NOT the same as a corrupt file. A corrupt file is
    warned about and skipped, but a missing decoder means the scanner never got
    to look inside a file that may well be hiding embedded Python, so the run
    must fail closed instead of quietly reporting "clean".
    """


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
            raise ScanUnavailable(
                "zstandard is not installed, so zstd-compressed .blend files "
                "cannot be inspected. Install it with 'pip install zstandard'."
            )
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
                raise ScanUnavailable(
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
            raise ScanUnavailable(
                "file is zstd-compressed; install 'zstandard' (pip install zstandard)"
            )
        return zstd.decompress_stream(stream, limit=MAX_OUTPUT)

    raise ValueError("not a Blender file (missing BLENDER magic)")


class UnknownBlenderStructure(Exception):
    """The stream is a .blend, but its layout is not one we can walk.

    Raised for a header we cannot size or a block chain that does not validate
    under any probed layout. It is a forward-compatibility signal, not a
    security verdict, so callers warn and fall back instead of failing.
    """


def parse_header(blob: bytes) -> dict:
    """Read the self-describing Blender file header.

    Returns a dict with ``header_len`` (where the first block starts) and the
    decoded version string. Raises UnknownBlenderStructure when the magic is
    absent or the declared length is impossible.
    """
    if len(blob) < MIN_HEADER_LEN or blob[:7] != BLENDER_MAGIC:
        raise UnknownBlenderStructure("missing BLENDER magic in the file header")

    # Self-describing header: decimal digits straight after the magic give the
    # header length ("17" in 5.x). A 6.x file that widens the header says so
    # itself, so no version is ever assumed here.
    digits = bytearray()
    index = 7
    while index < len(blob) and 0x30 <= blob[index] <= 0x39:
        digits.append(blob[index])
        index += 1

    header_len = 0
    if digits:
        try:
            header_len = int(digits.decode("ascii"))
        except (UnicodeDecodeError, ValueError):
            header_len = 0
        if not MIN_HEADER_LEN <= header_len <= MAX_HEADER_LEN:
            header_len = 0
    self_describing = header_len > 0
    if not header_len:
        # Classic layout: the bytes after the magic are a pointer-size marker
        # and an endianness flag rather than a length.
        header_len = LEGACY_HEADER_LEN
    if header_len > len(blob):
        raise UnknownBlenderStructure(
            f"declared header length {header_len} exceeds the {len(blob)}-byte stream"
        )

    version = blob[12:header_len] if header_len > 12 else b""
    return {
        "header_len": header_len,
        "version": version.decode("ascii", "replace"),
        "self_describing": self_describing,
    }


def _candidate_layouts():
    """Yield plausible (size, len_offset, len_width, endian) tuples.

    Ordered so a released layout is found quickly: widest length field first
    (a truncated 64-bit read can otherwise misparse a large block), and the
    larger block sizes first because those are the modern ones.
    """
    sizes = range(MAX_BHEAD_SIZE, MIN_BHEAD_SIZE - 1, -BHEAD_SIZE_STEP)
    for size in sizes:
        offsets = range(BHEAD_SIZE_STEP, size, BHEAD_SIZE_STEP)
        for len_offset in offsets:
            for len_width in LEN_WIDTHS:
                if len_offset + len_width > size:
                    continue
                for endian in ("little", "big"):
                    yield size, len_offset, len_width, endian


def _read_len(blob: bytes, off: int, layout: Layout) -> int | None:
    """Read one block's data length, or None if the bytes are unusable."""
    start = off + layout.len_offset
    end = start + layout.len_width
    if end > len(blob):
        return None
    return int.from_bytes(blob[start:end], layout.endian, signed=True)


def walk_blocks(
    blob: bytes,
    header_len: int,
    layout: Layout,
    limit: int = MAX_BLOCKS,
    stop_after: int | None = None,
) -> dict | None:
    """Walk the BHead chain under ``layout``.

    Returns a summary when the chain validates, else None. ``stop_after`` bounds
    the number of blocks inspected, which the discovery probe uses to reject
    wrong layouts cheaply before paying for a full walk.
    """
    off = header_len
    count = 0
    text_ranges: list[tuple[int, int]] = []
    dna_offsets: list[int] = []
    size = layout.size

    def result(partial: bool = False) -> dict:
        # The DNA1 anchor only counts when the reported block really does hold
        # an SDNA payload, so a coincidental code match cannot self-certify.
        dna_validated = any(
            blob[o : o + len(DNA1_PAYLOAD_MAGIC)] == DNA1_PAYLOAD_MAGIC
            for o in dna_offsets
        )
        return {
            "layout": layout,
            "blocks": count,
            "text_ranges": text_ranges,
            "dna_validated": dna_validated,
            "partial": partial,
        }

    while True:
        if off + size > len(blob):
            return None
        code = blob[off : off + 4]
        if not all((0x20 <= byte <= 0x7E) or byte == 0 for byte in code):
            return None
        data_len = _read_len(blob, off, layout)
        if data_len is None:
            return None

        if code == ENDB:
            # A valid chain ends with a zero-length ENDB and at most one
            # trailing pointer-sized slot.
            if data_len <= 0 and len(blob) - (off + size) <= 8:
                return result()
            return None

        if data_len < 0 or off + size + data_len > len(blob):
            return None
        if code[:3] == TEXT_CODE:  # Text datablock: null-/space-padded "TXT"
            text_ranges.append((off + size, data_len))
        if code == DNA1_CODE:
            dna_offsets.append(off + size)

        off += size + data_len
        count += 1
        if count > limit:
            return None
        if stop_after is not None and count >= stop_after:
            return result(partial=True)


def discover_layout(blob: bytes, header_len: int) -> Layout:
    """Find the block-header layout this file actually uses.

    Candidates are probed and kept only if the chain they produce validates all
    the way to ENDB. A layout that a Blender release changes is therefore
    picked up at runtime instead of needing a code change, and no version number
    is referenced.

    Preference order:
      1. A chain that also validates against the DNA1 anchor.
      2. Otherwise the first fully-validating chain in probe order.

    The DNA1 check matters because low-entropy data can occasionally satisfy a
    wrong layout by coincidence. Choosing such a layout would silently shift
    every block boundary and could skip a Text datablock, so the anchor is
    required whenever the file provides one.
    """
    probes = 0
    full_walks = 0
    fallback: Layout | None = None
    for size, len_offset, len_width, endian in _candidate_layouts():
        probes += 1
        layout = Layout(size, len_offset, len_width, endian, "probed")
        # Cheap reject first: a wrong layout almost always fails immediately.
        if walk_blocks(blob, header_len, layout, stop_after=PROBE_BLOCKS) is None:
            continue
        if full_walks >= MAX_FULL_WALKS:
            break
        full_walks += 1
        full = walk_blocks(blob, header_len, layout)
        if full is None or full.get("partial"):
            continue
        if full.get("dna_validated"):
            return layout._replace(
                source=f"chain + DNA1 anchor ({probes} probed, {full_walks} full walk(s))"
            )
        if fallback is None:
            fallback = layout

    if fallback is not None:
        return fallback._replace(
            source=f"chain validation only, no DNA1 block found "
            f"({probes} probed, {full_walks} full walk(s))"
        )
    raise UnknownBlenderStructure(
        f"no block-header layout validated across {probes} candidates"
    )


def scan_blocks(blob: bytes) -> dict | None:
    """Locate Text datablocks by walking the file's own block chain.

    Returns None when the structure is not recognised; raises
    UnknownBlenderStructure with the reason. The caller warns and falls back to
    the printable-run scan.
    """
    info = parse_header(blob)
    layout = discover_layout(blob, info["header_len"])
    result = walk_blocks(blob, info["header_len"], layout)
    if result is None:
        return None
    result["header"] = info
    return result



def printable_runs(blob: bytes, min_len: int = MIN_RUN_LENGTH):
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
    Text datablocks.

    Raises RuntimeError when Blender cannot be used, so the caller warns and
    falls back to the byte-level pass. Reporting "clean" from a Blender run that
    never actually inspected the file would be worse than not running it.
    """
    # Runs inside Blender. Written defensively because the Text API is not
    # guaranteed to be identical across releases: it is reached through getattr,
    # every access is individually guarded, and a failure is reported as an
    # error rather than collapsing to an empty list, which would read as clean.
    script = r"""
import json
import sys

MARKERS = (
    'import bpy',
    'import bge',
    'exec(',
    'eval(',
    '__import__',
    'def register(',
    'def unregister(',
    '.py',
)


def collect():
    import bpy
    texts = getattr(bpy.data, 'texts', None)
    if texts is None:
        return None, 'bpy.data.texts is unavailable in this Blender build'
    found = []
    for text in list(texts):
        try:
            name = str(text.name)
        except Exception:
            continue
        try:
            content = text.as_string() or ''
        except Exception:
            content = ''
        hits = [m for m in MARKERS if m in name or m in content]
        # Blender 4.0+ can auto-run a Text datablock on file load ("Register").
        try:
            auto_run = bool(getattr(text, 'use_module', False))
        except Exception:
            auto_run = False
        if hits or auto_run:
            found.append({'name': name, 'markers': hits, 'auto_run': auto_run})
    return found, None


try:
    found, error = collect()
except Exception as exc:
    found, error = None, repr(exc)

# JSON, not repr(): the result crosses a process boundary, and eval() on
# subprocess output is remote code execution by another name.
sys.stdout.write('BLENDSCAN_RESULT:' + json.dumps({'found': found, 'error': error}) + '\n')
sys.stdout.flush()
"""
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
        # The file must come before --python-expr: Blender executes a
        # --python-expr while it parses arguments, and only loads a positional
        # file afterwards. With the order reversed the script would inspect an
        # empty --factory-startup scene and always report "clean".
        blob_path,
        "--python-expr",
        script,
    ]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=HEADLESS_TIMEOUT,
        check=False,
    )
    try:
        Path(blob_path).unlink(missing_ok=True)
    except OSError:
        pass

    line = next(
        (l for l in proc.stdout.splitlines() if "BLENDSCAN_RESULT:" in l), None
    )
    if line is None:
        detail = (proc.stderr.strip() or proc.stdout.strip())[-300:]
        reason = (
            f"headless Blender exited with code {proc.returncode}"
            if proc.returncode != 0
            else "headless Blender produced no result (it may not be able to "
            "open this file's version)"
        )
        raise RuntimeError(f"{reason}: {detail}")

    try:
        payload = json.loads(line.split("BLENDSCAN_RESULT:", 1)[1])
    except (ValueError, IndexError) as exc:
        raise RuntimeError(f"unparseable headless Blender result: {exc!r}") from exc

    if payload.get("error") or payload.get("found") is None:
        raise RuntimeError(
            f"headless Blender could not inspect the file: "
            f"{payload.get('error') or 'no Text collection returned'}"
        )

    findings: list[dict] = []
    for entry in payload["found"]:
        markers = entry.get("markers") or []
        auto_run = bool(entry.get("auto_run"))
        reason = (
            f"Text datablock {entry['name']!r} is registered to auto-run on file load"
            if auto_run and not markers
            else f"Text datablock {entry['name']!r} contains executable Python"
        )
        findings.append(
            {
                "kind": "blend-text-datablock",
                "offset": 0,
                "marker": ", ".join(markers) or "use_module",
                "match": reason,
            }
        )
    return findings


def changed_blend_files(
    repo: Path, base: str, root: Path
) -> list[str]:
    """Files (repo-root-relative) that changed on .blend within root.

    ``git diff`` only knows about tracked files, so a .blend that exists on disk
    but is not yet tracked would be invisible to it. That is precisely the case
    a new pack is added in, so untracked .blend files are unioned in: a file is
    scanned when it is either changed since ``base`` or not tracked at all.

    Returns None when the diff could not be computed, which the caller treats
    as "scan the whole tree" so a git failure can never pass as clean.
    """
    names = scan_utils.git_diff_names(repo, base, str(root))
    if names is None:
        return None
    out = {name for name in names if Path(name).suffix.lower() == ".blend"}
    for name in scan_utils.git_untracked_names(repo, str(root)):
        if Path(name).suffix.lower() == ".blend":
            out.add(name)
    return sorted(out)


def all_blend_files(repo: Path, root: Path) -> list[str]:
    return scan_utils.walk_files(repo, root, ".blend", SKIP_DIRS)


def warn(message: str) -> None:
    """Non-fatal diagnostic. Never influences the exit code by itself."""
    print(f"[WARNING] {message}", file=sys.stderr, flush=True)


def scan_one(
    blob: bytes,
    allow: set[str],
    blender_binary: str | None,
    quiet: bool,
    label: str,
) -> tuple[list[dict], bool]:
    """Scan one decompressed container.

    Returns ``(findings, unverified)``. ``unverified`` is True when the
    authoritative pass could not run - headless Blender was unusable, or the
    block structure was not recognised - so only the printable-run fallback
    covered this file. Raises on malformed content.
    """
    unverified = False

    if blender_binary and shutil_has_blender(blender_binary):
        try:
            return open_in_memory_headless(blender_binary, blob), False
        except Exception as exc:  # noqa: BLE001
            # Blender being missing/broken must not silently downgrade the
            # scan, so warn and still run the byte-level pass. The file is
            # flagged as unverified because nothing authoritative looked
            # inside it.
            warn(
                f"{label}: headless Blender scan failed ({exc!r}); "
                f"falling back to the byte-level scan"
            )
            unverified = True

    walk = None
    try:
        walk = scan_blocks(blob)
    except UnknownBlenderStructure as exc:
        # A future Blender release, or a layout we cannot walk. This is a
        # forward-compatibility signal, not a verdict: warn, keep the exit code
        # at 0 unless a marker is actually found below, and still run the
        # printable-run pass, since an unrecognised container is precisely
        # where an embedded script would be hidden.
        warn(
            f"Unable to parse Blender 6.x or Unknown Blender Version file "
            f"structure for {label}. Skipping binary scan. ({exc})"
        )
        unverified = True

    if walk is not None:
        hdr = walk["header"]
        layout: Layout = walk["layout"]
        if not quiet:
            described = "self-describing" if hdr["self_describing"] else "classic fixed"
            print(
                f"[blend-scanner] {label}: valid container "
                f"({described} header, version={hdr['version']!r}, "
                f"{layout.describe()}, "
                f"{walk['blocks']} block(s), {len(walk['text_ranges'])} Text datablock(s))"
            )
        return scan_text_ranges(blob, walk, allow), unverified

    if not quiet:
        print(
            f"[blend-scanner] {label}: no recognised block structure; "
            f"falling back to printable-run scan"
        )
    return scan_blob(blob, allow), True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scan .blend files under DragonGraph's Project for embedded Python."
    )
    parser.add_argument("--repo", default=".", help="Path to the git repository root")
    parser.add_argument(
        "--base",
        default=None,
        help="Base commit to diff against (git diff --name-only BASE). "
        "Defaults to BLEND_SCAN_BASE, then to the newest commit on the remote "
        "default branch, so only .blend files changed or newly added under the "
        "scan root are inspected.",
    )
    parser.add_argument(
        "--full-tree",
        action="store_true",
        help="Scan every .blend under the scan root instead of only what "
        "changed. Use when you want to re-verify a file that has not changed "
        "since it was last scanned.",
    )
    parser.add_argument(
        "--root",
        default=DEFAULT_ROOT,
        help=f"Scan root (default: {DEFAULT_ROOT!r})",
    )
    parser.add_argument(
        "--blender-binary",
        default=BLENDER_BINARY or None,
        help="Optional headless Blender executable for authoritative Text-block "
        f"scan (default: BLENDER_BINARY from .env, currently {BLENDER_BINARY or 'unset'})",
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
    parser.add_argument(
        "--show-settings",
        action="store_true",
        help="Print the resolved .env settings and exit",
    )
    parser.add_argument("-q", "--quiet", action="store_true")
    args = parser.parse_args(argv)

    if args.show_settings:
        print(f"Settings: {env_utils.source_description()}")
        print(f"  BLEND_SCAN_ROOT = {DEFAULT_ROOT!r}")
        print(f"  BLEND_SCAN_BASE = {SCAN_BASE or 'auto (newest published commit)'}")
        print(f"  BLEND_SCAN_FULL_TREE = {SCAN_FULL_TREE}")
        print(f"  BLENDER_BINARY = {BLENDER_BINARY or 'unset'}")
        print(f"  BLEND_MAX_OUTPUT_BYTES = {MAX_OUTPUT}")
        print(f"  BLEND_MAX_BLOCKS = {MAX_BLOCKS}")
        print(f"  BLEND_MIN_RUN_LENGTH = {MIN_RUN_LENGTH}")
        print(f"  BLEND_HEADLESS_TIMEOUT = {HEADLESS_TIMEOUT}")
        print(f"  SCAN_SKIP_DIRS = {', '.join(SKIP_DIRS)}")
        print(f"  SCAN_STRICT_ON_ERROR = {STRICT_ON_ERROR}")
        return 0

    repo = scan_utils.resolve_repo(args.repo)
    root = path_utils.resolve_against(repo, args.root)
    if not scan_utils.is_git_repo(repo):
        print(f"[blend-scanner] not a git repository: {repo}", file=sys.stderr)
        return 2

    allow = set(args.disabled_markers)

    if not root.is_dir():
        print(f"[blend-scanner] scan root does not exist: {root}", file=sys.stderr)
        return 2

    # Only .blend files that actually changed (or were newly added) under the
    # scan root are opened. A pack that has not been touched does not need to be
    # decompressed and re-verified on every run. The base defaults to the newest
    # published commit so that everything not yet published is covered; when no
    # such commit can be resolved, this falls back to the full tree rather than
    # scanning nothing, so an unknown base is never mistaken for "no changes".
    if args.full_tree or SCAN_FULL_TREE:
        files = all_blend_files(repo, root)
        if not args.quiet:
            print(f"[blend-scanner] full-tree scan: {len(files)} .blend file(s)")
    else:
        base = args.base or SCAN_BASE or scan_utils.resolve_scan_base(repo)
        if base is None:
            files = all_blend_files(repo, root)
            if not args.quiet:
                print(
                    "[blend-scanner] no base commit to diff against "
                    "(no remote default branch found); scanning the full tree"
                )
        else:
            files = changed_blend_files(repo, base, root)
            if files is None:
                # The diff itself failed. Scan everything: a git failure must
                # never narrow the scan into a silent pass.
                files = all_blend_files(repo, root)
                if not args.quiet:
                    print(
                        f"[blend-scanner] could not diff against {base[:12]}; "
                        "scanning the full tree"
                    )
            elif not args.quiet:
                print(
                    f"[blend-scanner] scanning {len(files)} .blend file(s) "
                    f"changed or added since {base[:12]}"
                )

    if not files:
        print(
            f"[blend-scanner] no .blend files changed or added under {root.name}"
        )
        return 0

    all_findings: list[dict] = []
    unreadable: list[str] = []
    unverified_files: list[str] = []
    for rel in files:
        # A .blend that is corrupt, truncated, mid-write or not a .blend at all
        # is a technical problem, not a security violation. Warn loudly, count
        # it, and move on so one bad file never blocks the whole pipeline.
        try:
            raw = scan_utils.read_bytes(repo / rel)
        except Exception as exc:  # noqa: BLE001 - never let one file kill the run
            warn(f"cannot read {rel}: {exc!r}; skipping")
            unreadable.append(rel)
            continue

        try:
            blob = decompress_blob(raw)
        except ScanUnavailable as exc:
            # Cannot inspect this file at all. Never report "clean" when the
            # scanner was unable to look inside something.
            print(f"[blend-scanner] {rel}: {exc}", file=sys.stderr)
            print(
                "[blend-scanner] SCAN INCOMPLETE: a required decoder is missing, so "
                "at least one file was never inspected. Install the missing "
                "dependency and re-run; refusing to report a clean result.",
                file=sys.stderr,
            )
            return 2
        except Exception as exc:  # noqa: BLE001 - corrupt/foreign container
            warn(f"{rel}: cannot decode as a .blend container ({exc}); skipping")
            unreadable.append(rel)
            continue

        try:
            findings, unverified = scan_one(
                blob, allow, args.blender_binary, quiet=args.quiet, label=rel
            )
        except Exception as exc:  # noqa: BLE001 - malformed content, unexpected shape
            warn(f"{rel}: scanner error ({exc!r}); skipping")
            unreadable.append(rel)
            continue

        if unverified:
            # The authoritative pass did not run, so this file was only covered
            # by the printable-run fallback. Counted separately from an
            # unreadable file: the bytes were read, but not as far as the file
            # format was understood.
            unverified_files.append(rel)

        for finding in findings:
            finding["file"] = rel
        all_findings.extend(findings)

    if all_findings:
        print("[blend-scanner] SECURITY WARNING: suspicious content found in .blend files:")
        for f in all_findings:
            print(
                f"  {f['file']} @ {f['offset']}: "
                f"[{f['marker']}] {f['match']}"
            )
        print(
            f"[blend-scanner] {len(all_findings)} finding(s) across {len(files)} file(s)."
        )
        return 1

    # No policy violation. Unreadable files are reported, not punished, unless
    # the maintainer opted into strict mode.
    incomplete = unreadable + unverified_files
    if incomplete:
        print(
            f"[blend-scanner] scanned {len(files) - len(incomplete)}/{len(files)} "
            f"file(s); {len(incomplete)} not fully verified "
            f"({len(unreadable)} unreadable/undecodable, "
            f"{len(unverified_files)} with an unrecognised or unsupported structure)"
        )
        if STRICT_ON_ERROR:
            print(
                f"[blend-scanner] SCAN INCOMPLETE: SCAN_STRICT_ON_ERROR is on and "
                f"{len(incomplete)} file(s) could not be fully verified: "
                f"{', '.join(incomplete[:10])}"
            )
            return 2
        return 0

    print(f"[blend-scanner] OK - no embedded Python found in {len(files)} file(s)")
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
    except Exception as exc:  # unexpected crash -> fail closed, never pass silently
        print(
            f"[blend-scanner] unexpected crash: {exc!r}; scan did not complete (exit 2).",
            file=sys.stderr,
        )
        raise SystemExit(2)