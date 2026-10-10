"""Asset-library and node-group plumbing for the Toolset Pack loader.

Responsibilities
----------------
* Own the add-on isolation rule.  Every path this add-on reads, registers or
  deletes is validated to live inside the add-on folder first, so the pack can
  never point Blender at a directory it does not own.
* Register / unregister the internal ``assets/`` folder in
  ``bpy.context.preferences.filepaths.asset_libraries``.
* Unpack a manually loaded pack ``.zip`` into ``assets/extracted/``, applying
  the same isolation rule to every member the archive declares.
* Discover and append the Geometry Nodes library files that ship with the add-on.
* Ask any open Asset Browser to re-read its libraries.

API notes verified against Blender 5.2 / 5.3
---------------------------------------------
* ``PreferencesFilePaths.asset_libraries`` is a read-only collection that is
  mutated through ``AssetLibraryCollection.new()`` / ``.remove()``.  The
  ``new()`` keyword is ``directory=``; the returned ``UserAssetLibrary`` exposes
  ``path`` for later edits.
* ``PreferencesFilePaths.active_asset_library`` no longer indexes directly into
  ``asset_libraries`` as of 5.2 (the first two slots are "All Libraries" and
  "Essentials"), so this module never reads that index -- it looks its own
  library up by name instead.
* ``bpy.ops.asset.library_refresh()`` fails its poll outside an Asset Browser
  context, so ``refresh_asset_browsers()`` locates a real asset-browsing
  ``FILE_BROWSER`` area and overrides into it.
* Blender reads ``blender_assets.cats.txt`` only from the root of an asset
  library, never from a subfolder, so a pack that ships one has it merged into
  ``assets/`` rather than left in ``extracted/``.
"""

import hashlib
import os
import shutil
import stat
import subprocess
import zipfile

import bpy

from . import constants

__all__ = (
    "PACK_TAG",
    "PackArchiveError",
    "PackPathsError",
    "asset_library_dir",
    "asset_library_entry_count",
    "duplicate_asset_libraries",
    "duplicate_asset_library_warnings",
    "ensure_asset_library_ticked",
    "ensure_extracted_dir",
    "ensure_inside_addon",
    "extract_pack_archive",
    "catalog_file_installed",
    "extracted_dir",
    "find_asset_library",
    "is_asset_library_enabled",
    "is_asset_library_registered",
    "is_inside_addon",
    "is_pack_installed",
    "is_pack_node_group",
    "invalidate_duplicate_cache",
    "iter_blend_files_in",
    "iter_pack_blend_files",
    "load_node_groups",
    "online_access_granted",
    "open_folder",
    "pack_asset_count",
    "paths_equal",
    "purge_pack_data",
    "refresh_asset_browsers",
    "register_asset_library",
    "set_asset_library_enabled",
    "unregister_asset_library",
)

#: Hard ceiling on the uncompressed size accepted from one pack archive, and on
#: the number of members.  A zip can declare a tiny compressed size and expand to
#: anything ("zip bomb"), so the declared ``file_size`` is summed and compared
#: *before* anything is written to disk.  The limits are deliberately generous:
#: a Geometry Nodes library is text, not binary media.
MAX_ARCHIVE_BYTES = 2 * 1024 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 20000

#: Windows caps a path at 260 characters.  A pack's own library file name is
#: long enough to cross that once the add-on path is prefixed, so destinations
#: are measured against it before anything is written.
MAX_PATH_LENGTH = 260

#: Blender's asset catalog file. It is only read from the root of an asset
#: library, so a pack that ships one has to have it placed there.
CATALOG_FILE_NAME = "blender_assets.cats.txt"

#: Where the last unpack left a catalog file, for the operator's report. Reset at
#: the start of every unpack so a stale path is never reported for a pack that
#: shipped no catalogs.
_CATALOG_INSTALLED = {}

#: Memoised result of :func:`duplicate_asset_libraries`.
#:
#: This has to be cached, and not as a micro-optimisation: the check walks every
#: asset library the user has and hashes the ``.blend`` files it finds, which is
#: ~150 ms for a project-sized library.  The panel draws the duplicate warning, and
#: Blender redraws a panel on every pointer move, so an uncached call here froze
#: the UI solid -- one redraw at a time, hundreds of times a second.
#:
#: So the walk happens once and the answer is reused.  Anything that can change the
#: answer has to invalidate it explicitly (see :func:`invalidate_duplicate_cache`);
#: add-on enable and the fix operator both do.  A stale warning until the next
#: enable is a far better failure than an unresponsive Blender.
_DUPLICATE_CACHE: dict = {}


class PackPathsError(RuntimeError):
    """Raised when a path escapes the add-on's own folder."""


class PackArchiveError(RuntimeError):
    """Raised when a pack archive is unreadable, unsafe or holds no libraries."""


# ---------------------------------------------------------------------------
# Paths and isolation
# ---------------------------------------------------------------------------


def addon_root() -> str:
    """Absolute path of the add-on's own extracted folder root."""
    return constants.ADDON_ROOT


def asset_library_dir() -> str:
    """Absolute path of the folder registered as an asset library."""
    return constants.PACK_DIR


def extracted_dir() -> str:
    """Absolute path of the folder manual loads are unpacked into."""
    return ensure_inside_addon(constants.EXTRACTED_DIR)


def ensure_extracted_dir() -> str:
    """Return the extracted folder, creating it if it does not exist."""
    destination = extracted_dir()
    os.makedirs(destination, exist_ok=True)
    return destination


def is_inside_addon(path: str) -> bool:
    """True when *path* resolves to a location inside the add-on folder."""
    if not path:
        return False
    root = os.path.realpath(addon_root())
    try:
        target = os.path.realpath(path)
    except (OSError, ValueError):
        return False
    if target == root:
        return True
    try:
        return os.path.commonpath([root, target]) == root
    except ValueError:
        # Raised on Windows when the two paths sit on different drives, which
        # by definition means the target is outside the add-on.
        return False


def ensure_inside_addon(path: str) -> str:
    """Return the normalised *path*, or raise if it is not inside the add-on."""
    if not is_inside_addon(path):
        raise PackPathsError(
            "Refusing to touch {!r}: the Toolset Pack loader only operates inside "
            "its own folder ({}).".format(path, addon_root())
        )
    return os.path.normpath(path)


def paths_equal(first: str, second: str) -> bool:
    """Case-insensitive, separator-tolerant path comparison."""
    if not first or not second:
        return first == second
    return os.path.normcase(os.path.normpath(first)) == os.path.normcase(
        os.path.normpath(second)
    )


# ---------------------------------------------------------------------------
# Asset library registration (Preferences > File Paths > Asset Libraries)
# ---------------------------------------------------------------------------


def _asset_libraries():
    return bpy.context.preferences.filepaths.asset_libraries


def find_asset_library(name: str = constants.ASSET_LIBRARY_NAME):
    """Return the ``UserAssetLibrary`` this add-on owns, or ``None``."""
    for library in _asset_libraries():
        if library.name == name:
            return library
    return None


def is_asset_library_registered() -> bool:
    """True when our asset-library entry exists in Blender's Preferences."""
    return find_asset_library() is not None


def _library_root(library) -> str:
    try:
        return os.path.realpath(library.path)
    except (AttributeError, TypeError):
        return ""


def _blend_files_under(root: str):
    """Real paths of every ``.blend`` at or below *root*.

    Asset libraries are scanned recursively, so a library pointing at a project
    folder picks up pack libraries nested anywhere under it.  That is what makes
    the same ``.blend`` reachable from two libraries at once.
    """
    if not root or not os.path.isdir(root):
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for filename in sorted(filenames):
            if filename.lower().endswith(".blend"):
                yield os.path.realpath(os.path.join(dirpath, filename))


def _blend_fingerprints(root: str, only_sizes=None):
    """Map content fingerprint -> real path for each ``.blend`` under *root*.

    Keyed on *content*, not on path, because the clash is not the same file seen
    twice: the pack in the add-on's ``assets/extracted/`` and the same pack in the
    project folder are two separate copies with the same bytes.  Blender registers
    both, so a path comparison would miss the one case that actually matters.

    *only_sizes* restricts hashing to files of those sizes.  Pass the sizes of our
    own libraries when scanning somebody else's library: a folder that cannot
    contain a byte-identical copy of a pack of a different size is not worth
    hashing, and a project library can hold a lot of ``.blend`` files.
    """
    fingerprints = {}
    for path in _blend_files_under(root):
        try:
            size = os.path.getsize(path)
        except OSError:
            continue
        if only_sizes is not None and size not in only_sizes:
            continue
        digest = _file_digest(path)
        if digest is not None:
            fingerprints.setdefault((size, digest), path)
    return fingerprints


def invalidate_duplicate_cache() -> None:
    """Force the next :func:`duplicate_asset_libraries` call to walk again.

    Must be called by anything that changes the answer: enabling the add-on, and
    the fix operator once it has unticked a library.
    """
    _DUPLICATE_CACHE.clear()


def _file_digest(path: str, chunk_size: int = 1 << 20):
    """SHA-256 of *path*, or ``None`` if it cannot be read.

    Local stdlib only -- the add-on ships no third-party imports.
    """
    digest = hashlib.sha256()
    try:
        with open(path, "rb") as handle:
            for block in iter(lambda: handle.read(chunk_size), b""):
                digest.update(block)
    except OSError:
        return None
    return digest.hexdigest()


def duplicate_asset_libraries(refresh: bool = False):
    """Enabled libraries, other than our own, that also contain this pack.

    Returns ``(library, folders)`` pairs, where *folders* are the directories
    inside *library* that hold the matching copies, so a caller can both act on
    the entry and tell the user where to look.  Ordered by name so the result is
    stable between calls and does not depend on the order Blender happens to list
    the libraries in.

    The answer is cached, because computing it costs a filesystem walk plus
    hashing and this is called while drawing a panel -- see :data:`_DUPLICATE_CACHE`
    for why that was not optional.  Pass ``refresh=True`` to force a recompute, and
    note that *only* the add-on enabling and the fix operator do.
    """
    if not refresh and "offenders" in _DUPLICATE_CACHE:
        return _DUPLICATE_CACHE["offenders"]

    offenders = _find_duplicate_asset_libraries()
    _DUPLICATE_CACHE["offenders"] = offenders
    return offenders


def _find_duplicate_asset_libraries():
    ours = find_asset_library()
    if ours is None or not getattr(ours, "enabled", False):
        return []

    ours_root = _library_root(ours)
    ours_blends = _blend_fingerprints(ours_root)
    if not ours_blends:
        return []

    # Only a byte-identical copy can clash, so a file of a different size in
    # somebody else's library is skipped without being read at all.  Sizes are
    # read from directory entries, which is the cheap part of the walk.
    our_sizes = {size for size, _digest in ours_blends}

    offenders = []
    for library in _asset_libraries():
        if not getattr(library, "enabled", False):
            continue
        if library.name == constants.ASSET_LIBRARY_NAME:
            continue

        other_root = _library_root(library)
        if not other_root or paths_equal(other_root, ours_root):
            continue

        other_blends = _blend_fingerprints(other_root, only_sizes=our_sizes)
        shared = set(ours_blends).intersection(other_blends)
        if not shared:
            continue

        # Name the folder inside the *other* library, not ours. Ours is inside the
        # add-on and is not the one the user can act on; theirs is the entry they
        # have to untick, and the pack sits in a subfolder of it that they can
        # point away from.
        folders = sorted({os.path.dirname(other_blends[key]) for key in shared})
        offenders.append((library, folders))

    return sorted(offenders, key=lambda pair: pair[0].name)


def duplicate_asset_library_warnings():
    """Describe the libraries that :func:`duplicate_asset_libraries` would fix.

    Blender registers every asset it finds, keyed by library, so one ``.blend``
    reachable from two libraries is registered twice and each asset in it logs
    ``N duplicate(s)``.  The add-on owns only one of the two entries, so it cannot
    resolve this on its own -- but it can say which library the user has to untick,
    which is otherwise buried in console spam with no mention of a library name.

    Compared by content, not by path, because the usual case is two identical
    copies of the pack in two folders rather than one file listed twice.

    Returns a list of human-readable messages, empty when there is no clash.
    """
    messages = []
    for library, folders in duplicate_asset_libraries():
        messages.append(
            "The asset library '{}' also contains this Toolset Pack ({}). "
            "Blender registers the same assets twice, which is why the console "
            "reports duplicates. Untick '{}' in Preferences > File Paths > Asset "
            "Libraries, or point it at a folder that does not contain the "
            "pack.".format(library.name, ", ".join(folders), library.name)
        )
    return messages


def register_asset_library(import_method: str = "PACK"):
    """Create or repair our asset-library entry.

    Returns ``(library, created)``.  ``created`` is ``True`` only when a brand
    new entry was appended, which lets callers decide whether the Asset Browser
    needs a refresh at all.
    """
    directory = ensure_inside_addon(asset_library_dir())
    os.makedirs(directory, exist_ok=True)

    existing = find_asset_library()
    if existing is not None:
        if not paths_equal(existing.path, directory):
            # The add-on moved (a different Blender version, a new extensions
            # folder, a re-install). Point the stale entry at the new location.
            existing.path = directory
        existing.use_relative_path = True
        existing.import_method = import_method
        existing.enabled = True
        return existing, False

    # NOTE: the keyword is ``directory=``; ``UserAssetLibrary.path`` is only
    # writable after the entry exists.
    library = _asset_libraries().new(
        name=constants.ASSET_LIBRARY_NAME,
        directory=directory,
    )
    library.use_relative_path = True
    library.import_method = import_method
    library.enabled = True
    return library, True


def asset_library_entry_count() -> int:
    """How many entries named after this add-on are in the Asset Libraries list.

    One is the only correct value.  A second would mean the Asset Browser lists the
    same pack twice, so anything that has to reason about registration (tests, the
    manual-load path) checks this rather than assuming it.
    """
    return sum(
        1
        for library in _asset_libraries()
        if library.name == constants.ASSET_LIBRARY_NAME
    )


def is_asset_library_enabled() -> bool:
    """True when our entry exists *and* is ticked in the Asset Libraries list."""
    library = find_asset_library()
    return library is not None and bool(library.enabled)


def ensure_asset_library_ticked(import_method: str = "PACK") -> str:
    """Guarantee exactly one entry, ticked and pointing at ``assets/``.

    This is what the manual-load path uses after it has unpacked a new pack.  It
    deliberately does *not* untick and re-create the entry: the entry points at
    ``assets/`` and manual load only replaces the contents of
    ``assets/extracted/``, so the row is already correct and re-creating it would
    only risk ending up with two.

    The one thing it does fix is a row that was left unticked, or one whose path
    has gone stale because the add-on moved.  Loading a pack that the Asset Browser
    cannot see is the confusing failure, so unpacking implies ticked.

    Returns a short status message when something actually changed (entry created,
    re-pointed, or re-ticked), or ``""`` when the entry was already correct.
    """
    before = asset_library_entry_count()
    was_enabled = is_asset_library_enabled()

    try:
        library, created = register_asset_library(import_method)
    except (OSError, PackPathsError) as error:
        return "Could not tick '{}' in the Asset Library: {}".format(
            constants.ASSET_LIBRARY_NAME, error
        )

    after = asset_library_entry_count()
    if after > 1:
        return (
            "'{}' is listed {} times in the Asset Library list. Only one is "
            "expected; use Uninstall to remove the extra ones.".format(
                constants.ASSET_LIBRARY_NAME, after
            )
        )

    if created:
        return "Registered '{}' at {}".format(library.path, library.name)
    if not was_enabled:
        return "Ticked '{}' so the new pack shows in the Asset Browser".format(
            constants.ASSET_LIBRARY_NAME
        )
    return ""


def unregister_asset_library() -> bool:
    """Delete our asset-library entry. Returns ``True`` if one was deleted.

    This is the destructive half of unloading and is reserved for
    :func:`preferences.DRAGONGRAPH_AddonPreferences.purge_asset_library_entry`,
    which the user has to ask for by name.  The ordinary "Unload" toggle must
    call :func:`set_asset_library_enabled` instead, so that a mis-click leaves
    the entry in Preferences and it can simply be re-ticked.
    """
    library = find_asset_library()
    if library is None:
        return False
    _asset_libraries().remove(library)
    return True


def set_asset_library_enabled(enabled: bool) -> None:
    """Tick or untick our entry in the Asset Libraries list, keeping it.

    Unloading works by unticking rather than by deleting the entry, which is what
    the user means by "untick" in Preferences > File Paths > Asset Libraries.  The
    entry, its path and its import method all survive, so loading again is a
    single re-tick instead of a re-create, and an accidental unload is trivially
    reversible.
    """
    library = find_asset_library()
    if library is not None:
        library.enabled = bool(enabled)


# ---------------------------------------------------------------------------
# Pack archive extraction
# ---------------------------------------------------------------------------


def _member_destination(destination: str, member_name: str) -> str:
    """Resolve one zip member to a path inside *destination*.

    Zip files carry their own paths, and a crafted archive can name an entry
    ``../../evil.py`` or ``C:\\Windows\\evil.dll``.  The member name is
    therefore never joined blindly: absolute names (a leading ``/`` or a drive
    prefix) and every ``..`` segment are rejected outright, and the resolved
    path is re-checked against both *destination* and the add-on root.

    Returns ``""`` for an entry that names no path at all (a bare ``"./"``
    root entry, which some Windows zip writers emit); the caller skips those.
    """
    cleaned = member_name.replace("\\", "/")

    # An absolute member name is never legitimate inside a pack archive, and
    # silently reinterpreting it as relative ("/x" -> "x", "C:/x" -> "C/x")
    # would let a crafted archive decide where its files land.  Reject instead.
    if cleaned.startswith("/") or _has_drive_prefix(cleaned):
        raise PackArchiveError(
            "Refusing to unpack the absolute path {!r}: pack archives must use "
            "relative paths.".format(member_name)
        )

    parts = []
    for segment in cleaned.split("/"):
        if segment in ("", "."):
            continue
        if segment == "..":
            raise PackArchiveError(
                "Refusing to unpack {!r}: the archive points outside the "
                "extraction folder.".format(member_name)
            )
        parts.append(segment)

    if not parts:
        # An entry naming nothing but separators, "." or "./". Zips written on
        # Windows sometimes carry a bare "./" root entry. There is no path to
        # resolve, so the caller is told to skip it.
        return ""

    target = os.path.normpath(os.path.join(destination, *parts))
    if not is_inside_addon(target) or not _is_within(target, destination):
        raise PackArchiveError(
            "Refusing to unpack {!r}: the archive points outside the "
            "extraction folder.".format(member_name)
        )
    return target


def _has_drive_prefix(name: str) -> bool:
    """True for ``C:``, ``C:/x`` and other Windows drive-relative/absolute forms."""
    return len(name) >= 2 and name[1] == ":" and name[0].isalpha()


def _is_within(path: str, root: str) -> bool:
    """True when *path* is strictly below *root* (root itself does not count)."""
    try:
        path_real = os.path.realpath(path)
        root_real = os.path.realpath(root)
    except (OSError, ValueError):
        return False
    if path_real == root_real:
        return False
    try:
        return os.path.commonpath([root_real, path_real]) == root_real
    except ValueError:
        return False


def _assert_writable_length(path: str, label: str) -> None:
    """Refuse a destination Windows cannot represent, with a usable message.

    Windows caps a path at 260 characters.  Beyond it, ``open`` fails with
    ``FileNotFoundError`` naming a file whose parent folder was just created
    successfully, which is indistinguishable from a genuinely missing file and
    sends the reader looking in the wrong place.  A pack's library name is long
    enough on its own to cross the limit, so this is checked up front and
    reported as the path-length problem it is.
    """
    if len(path) > MAX_PATH_LENGTH:
        raise PackArchiveError(
            "{} needs a path of {} characters, past the {} character limit "
            "Windows allows: {!r}. Shorten the pack's file name, or move the "
            "add-on to a shorter path.".format(
                label, len(path), MAX_PATH_LENGTH, path
            )
        )


def extract_pack_archive(zip_path: str) -> str:
    """Unpack a pack ``.zip`` into ``assets/extracted/``.

    The members land in the folder itself, not in a subfolder named after the
    archive.  A pack ships its library at the top level under its own file
    name, so a subfolder only repeated that name, and the add-on path is
    already long enough that the repetition pushes the library past Windows'
    260 character limit.

    *Reading* the archive is unrestricted: the caller has already resolved a
    file the user explicitly chose, and a pack downloaded to ``Downloads`` must
    not have to be copied into the add-on first.  Nothing here can write
    outside the add-on as a result.

    *Writing* is not.  The destination is always inside the add-on, and every
    member must resolve to a path inside it (see :func:`_member_destination`),
    so the archive's own contents cannot choose their destination.  The
    destination folder is emptied on each run, so re-loading the same pack
    does not leave stale libraries behind and repeated extraction cannot
    accumulate files.

    Returns the absolute path of the folder the archive was unpacked into.
    Raises :class:`PackArchiveError` for unreadable, empty or unsafe archives.
    """
    # An absolute path from the file browser is used as given; a bare file name
    # is resolved against the assets folder the picker was opened in.
    if not os.path.isabs(zip_path):
        zip_path = os.path.join(asset_library_dir(), zip_path)

    if not zip_path.lower().endswith(constants.ALLOWED_PACK_ARCHIVE):
        raise PackArchiveError(
            "Only {} archives can be unpacked (got {!r}).".format(
                constants.ALLOWED_PACK_ARCHIVE,
                os.path.basename(zip_path),
            )
        )

    if not os.path.isfile(zip_path):
        raise PackArchiveError(
            "No such file: {}".format(os.path.basename(zip_path))
        )

    destination = extracted_dir()
    _CATALOG_INSTALLED.clear()

    try:
        archive = zipfile.ZipFile(zip_path)
    except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile) as error:
        raise PackArchiveError(
            "Could not open {}: {}".format(os.path.basename(zip_path), error)
        )

    with archive:
        members = archive.infolist()
        if not members:
            raise PackArchiveError(
                "{} is empty.".format(os.path.basename(zip_path))
            )
        if len(members) > MAX_ARCHIVE_MEMBERS:
            raise PackArchiveError(
                "{} holds more than {} entries.".format(
                    os.path.basename(zip_path), MAX_ARCHIVE_MEMBERS
                )
            )

        declared_total = 0
        for member in members:
            # Symlinks inside an archive would let a pack point Blender at a
            # file anywhere on disk; they are not needed for a node library.
            mode = member.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise PackArchiveError(
                    "Refusing to unpack the symlink {!r}.".format(member.filename)
                )
            declared_total += max(0, int(member.file_size))

        if declared_total > MAX_ARCHIVE_BYTES:
            raise PackArchiveError(
                "{} unpacks to more than {} bytes.".format(
                    os.path.basename(zip_path), MAX_ARCHIVE_BYTES
                )
            )

        # Validate every member, directory entries included, *before* writing
        # anything: a directory entry is written in the same pass as the files,
        # so a bad one discovered half way through would still leave a
        # partially unpacked folder behind.  The length check belongs in the
        # same pass, for the same reason: it must refuse before the first byte
        # is written, not after some of the pack is already on disk.
        for member in members:
            target = _member_destination(destination, member.filename)
            if target:
                _assert_writable_length(
                    target, "Unpacking {}".format(os.path.basename(zip_path))
                )

        if os.path.isdir(destination):
            _remove_tree(destination)
        os.makedirs(destination, exist_ok=True)

        for member in members:
            target = _member_destination(destination, member.filename)
            if not target:
                continue
            if member.is_dir():
                os.makedirs(target, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with archive.open(member) as source, open(target, "wb") as sink:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    sink.write(chunk)

        _install_catalog_file(destination)

    return destination


def _install_catalog_file(destination: str) -> str:
    """Copy a pack's catalog file to the asset library root, where Blender reads it.

    Blender only looks for ``blender_assets.cats.txt`` in the root of an asset
    library, never in a subfolder of it.  A pack ships that file next to its
    library, so unpacking it into ``extracted/`` would produce a file Blender
    never opens and the pack's catalogs would silently be missing.  It is copied
    up one level for that reason.

    An existing catalog file is merged rather than replaced, so a user's own
    catalogs, and the catalogs of a pack loaded earlier, survive.  Only the
    lines a pack actually ships are touched.  Returns the path written, or an
    empty string when the archive carried no catalog file.
    """
    source = os.path.join(destination, CATALOG_FILE_NAME)
    if not os.path.isfile(source):
        return ""

    root = ensure_inside_addon(asset_library_dir())
    target = os.path.join(root, CATALOG_FILE_NAME)
    _assert_writable_length(
        target, "Installing the pack's {}".format(CATALOG_FILE_NAME)
    )

    try:
        with open(source, "r", encoding="utf-8", errors="replace") as handle:
            incoming = handle.read()
    except OSError as error:
        raise PackArchiveError(
            "Could not read the pack's {}: {}".format(CATALOG_FILE_NAME, error)
        )

    existing = ""
    if os.path.isfile(target):
        try:
            with open(target, "r", encoding="utf-8", errors="replace") as handle:
                existing = handle.read()
        except OSError:
            # An unreadable catalog file is not worth refusing the pack over:
            # the file is rewritten from the pack's own text below.
            existing = ""

    merged = _merge_catalog_files(existing, incoming)
    with open(target, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(merged)
    _CATALOG_INSTALLED["path"] = target
    return target


def catalog_file_installed() -> str:
    """The library root ``blender_assets.cats.txt`` written by the last unpack.

    Empty when the last archive carried no catalog file, which is what the
    operator reports to decide whether to mention the catalogs.
    """
    return _CATALOG_INSTALLED.get("path", "")


def _merge_catalog_files(existing: str, incoming: str) -> str:
    """Merge two catalog files by UUID, letting *incoming* win on a clash.

    Blender's format is one ``UUID:catalog/path:simple name`` line per catalog,
    so a catalog is identified by its UUID.  Comments, blank lines and the
    ``VERSION`` line are kept; the pack's definition replaces an existing one
    with the same UUID, which is what re-loading an updated pack should do.
    """
    header = [
        line
        for line in incoming.splitlines()
        if line.startswith("#")
        or line.startswith("VERSION")
        or not line.strip()
    ]
    if not any(line.startswith("VERSION") for line in header):
        header = ["VERSION 1"] + header

    def _entries(text):
        found = []
        for line in text.splitlines():
            if not line.strip() or line.startswith("#") or line.startswith("VERSION"):
                continue
            parts = line.split(":", 2)
            if len(parts) == 3 and parts[0].strip():
                found.append((parts[0].strip(), line))
        return found

    merged = {}
    order = []
    for uuid, line in _entries(existing):
        if uuid not in merged:
            order.append(uuid)
        merged[uuid] = line
    for uuid, line in _entries(incoming):
        if uuid not in merged:
            order.append(uuid)
        merged[uuid] = line

    comments = [line for line in header if line.startswith("#") and line.strip()]
    out = list(comments)
    out.append("VERSION 1")
    out.append("")
    out.extend(merged[uuid] for uuid in order)
    return "\n".join(out).rstrip("\n") + "\n"


def _remove_tree(path: str) -> None:
    """Delete *path* recursively, refusing anything outside the add-on."""
    if not is_inside_addon(path):
        raise PackPathsError(
            "Refusing to delete {!r}: it is outside the add-on folder.".format(path)
        )
    shutil.rmtree(path, ignore_errors=True)


# ---------------------------------------------------------------------------
# Pack contents
# ---------------------------------------------------------------------------


def _iter_blend_files(directory: str):
    if not directory or not os.path.isdir(directory):
        return
    for dirpath, dirnames, filenames in os.walk(directory):
        dirnames.sort()
        for filename in sorted(filenames):
            if not filename.lower().endswith(".blend"):
                continue
            yield os.path.join(dirpath, filename)


def iter_blend_files_in(directory: str):
    """Every ``.blend`` under *directory*, or nothing if it is not a folder.

    Public wrapper around :func:`_iter_blend_files` so callers outside this
    module (the manual-load operator, for a freshly unpacked archive) do not
    have to reach for a private name.  Results are *not* filtered through the
    isolation rule; the caller is responsible for passing a validated folder.
    """
    return _iter_blend_files(directory)


def iter_pack_blend_files():
    """Every ``.blend`` inside the add-on folder that may hold the pack.

    This covers ``assets/`` (what the Asset Browser reads) and ``library/``
    (the shipped originals), and nothing outside the add-on folder.
    """
    seen = set()
    for directory in (constants.PACK_DIR, constants.SHIPPED_DIR):
        for path in _iter_blend_files(directory):
            key = os.path.normcase(os.path.normpath(path))
            if key in seen:
                continue
            seen.add(key)
            yield path


def is_pack_installed() -> bool:
    """True when at least one library ``.blend`` shipped with the add-on."""
    return next(iter_pack_blend_files(), None) is not None


def pack_asset_count() -> int:
    """Number of Geometry Nodes libraries discovered inside the add-on."""
    return sum(1 for _ in iter_pack_blend_files())


def _is_pack_library(path: str) -> bool:
    return bool(path) and is_inside_addon(path)


#: Custom ID-property stamped on every node group this add-on brings in.
#:
#: It exists because ``node_group.library`` is only populated when the data is
#: *linked*.  Appending (which is what "Pack"/"Append" import methods do, and
#: what this add-on always uses for node groups) leaves ``library`` as ``None``,
#: so provenance cannot be recovered from the datablock alone.  The tag is the
#: authoritative record, and ``_source_of`` falls back to the library only for
#: linked data.
PACK_TAG = "_dragongraph_pack"


def _source_of(node_group) -> str:
    """Absolute path this node group came from, or ``""`` if not ours."""
    tag = node_group.get(PACK_TAG)
    if tag:
        return str(tag)
    library = getattr(node_group, "library", None)
    if library is not None and _is_pack_library(library.filepath):
        return library.filepath
    return ""


def is_pack_node_group(node_group) -> bool:
    """True when *node_group* was loaded from inside the add-on folder."""
    return bool(_source_of(node_group))


def is_node_group_loaded(blend_path: str) -> bool:
    """True when node groups from *blend_path* are already in ``bpy.data``."""
    return any(
        paths_equal(_source_of(node_group), blend_path)
        for node_group in bpy.data.node_groups
        if _source_of(node_group)
    )


def load_node_groups(blend_paths, force: bool = False):
    """Append the Geometry Nodes library files found inside the add-on.

    ``force=False`` skips a file whose node groups are already loaded, which is
    what the ``load_post`` handler wants.  ``force=True`` is what the explicit
    "Reload" button wants, and is paired with :func:`purge_pack_data` first.

    Every appended node group is tagged with :data:`PACK_TAG` (its source
    path) and given a fake user, so the pack's nodes stay available in the Add
    menu and can always be identified again for a clean reload.

    Returns ``(loaded, skipped, failed)`` file counts.
    """
    loaded = 0
    skipped = 0
    failed = 0

    for blend_path in blend_paths:
        try:
            blend_path = ensure_inside_addon(blend_path)
        except PackPathsError:
            failed += 1
            continue

        if not os.path.isfile(blend_path):
            failed += 1
            continue

        # Appending the file that is currently open raises
        # "ValueError: Cannot load from the current blend file."  This happens
        # on every ``load_post`` when the user opens one of the pack's own
        # library files, so it has to be skipped rather than treated as an
        # error.  Its node groups are already in ``bpy.data`` by definition.
        if paths_equal(blend_path, bpy.data.filepath):
            skipped += 1
            continue

        if not force and is_node_group_loaded(blend_path):
            skipped += 1
            continue

        before = {ng.name for ng in bpy.data.node_groups}

        try:
            with bpy.data.libraries.load(blend_path, link=False) as (
                data_from,
                data_to,
            ):
                data_to.node_groups = list(data_from.node_groups)
        except (OSError, RuntimeError, ValueError) as error:
            # ValueError covers "Cannot load from the current blend file" and
            # unreadable/corrupt archives; none of them should abort the loop.
            failed += 1
            print("[DragonGraph] Could not read {}: {}".format(blend_path, error))
            continue

        # Blender mangles names on collision ("Foo", "Foo.001"), so tag by
        # diffing the ID collection rather than by the requested name.
        # ``bpy.data.libraries.load`` returns the names it was asked for, not
        # the resulting datablocks, so newly created IDs are found by diffing
        # against what was present before the load.
        for node_group in bpy.data.node_groups:
            if node_group.name in before:
                continue
            node_group[PACK_TAG] = blend_path
            node_group.use_fake_user = True

        loaded += 1

    return loaded, skipped, failed


def _real_users(node_group) -> int:
    """User count ignoring the fake user.

    :func:`load_node_groups` gives every pack node group a fake user so the
    nodes stay in the Add menu, and Blender counts that fake user in
    ``ID.users``.  Reading ``users`` directly would therefore make every pack
    group look "in use" and :func:`purge_pack_data` would never clean up, so
    the fake user is cleared for the duration of the read.
    """
    if not node_group.use_fake_user:
        return node_group.users
    node_group.use_fake_user = False
    try:
        return node_group.users
    finally:
        node_group.use_fake_user = True


def purge_pack_data(include_used: bool = False):
    """Drop data-blocks that came from inside the add-on.

    Only node groups carrying :data:`PACK_TAG` with a source under the add-on
    root are ever considered, so a user's own libraries are untouchable.

    ``include_used=False`` (the default) keeps anything still referenced by a
    scene, because removing those would break the open file.  The fake user
    added on load does not count as a real use (see :func:`_real_users`).
    Returns ``(removed, kept_in_use)`` node-group counts.
    """
    removed = 0
    kept_in_use = 0

    for node_group in list(bpy.data.node_groups):
        source = _source_of(node_group)
        if not source or not _is_pack_library(source):
            continue
        if not include_used and _real_users(node_group) > 0:
            kept_in_use += 1
            continue
        bpy.data.node_groups.remove(node_group)
        removed += 1

    # Drop the now-unused Library IDs so a re-load does not reuse stale links.
    # Only linked data produces Library IDs; appended data does not.
    for library in list(bpy.data.libraries):
        if _is_pack_library(library.filepath) and library.users == 0:
            bpy.data.libraries.remove(library)

    return removed, kept_in_use


# ---------------------------------------------------------------------------
# Asset Browser integration
# ---------------------------------------------------------------------------


def online_access_granted() -> bool:
    """True when the user allowed Blender to use the internet.

    Blender's documented rule is that add-ons must gate network work on the
    read-only ``bpy.app.online_access`` flag rather than writing the
    preference themselves.
    """
    return bool(getattr(bpy.app, "online_access", False))


def refresh_asset_browsers(context) -> int:
    """Re-read the libraries in every open Asset Browser.

    ``bpy.ops.asset.library_refresh()`` fails its poll unless the context is
    actually browsing assets, and ``AssetLibraryReference`` exposes no writable
    RNA so the reference cannot be faked.  The supported route is therefore to
    find a real ``FILE_BROWSER`` area in ``ASSETS`` browse mode and override
    into it.  Returns the number of editors successfully refreshed.
    """
    if context is None:
        return 0

    window_manager = getattr(context, "window_manager", None)
    if window_manager is None:
        return 0

    refreshed = 0

    for window in window_manager.windows:
        screen = getattr(window, "screen", None)
        if screen is None:
            continue
        for area in screen.areas:
            # Blender has no dedicated ASSET_BROWSER space type: the Asset
            # Browser is a File Browser whose browse_mode is 'ASSETS'.
            if area.type != "FILE_BROWSER":
                continue
            space = area.spaces.active
            if getattr(space, "browse_mode", "FILES") != "ASSETS":
                continue
            region = next(
                (r for r in area.regions if r.type == "WINDOW"), None
            )
            try:
                with context.temp_override(window=window, area=area, region=region):
                    if bpy.ops.asset.library_refresh.poll():
                        bpy.ops.asset.library_refresh()
                    else:
                        continue
            except RuntimeError:
                # The editor went away mid-iteration; nothing else to do.
                continue
            refreshed += 1

    return refreshed


def open_url(url: str) -> bool:
    """Open *url* in the user's browser. Returns ``True`` on success."""
    try:
        return "FINISHED" in bpy.ops.wm.url_open(url=url)
    except (AttributeError, RuntimeError, TypeError):
        return False


def open_folder(path: str) -> bool:
    """Open *path* in the host file explorer.

    Returns ``True`` on success.  Any error is caught so the caller can report a
    usable message instead of raising an exception.
    """
    target = path
    try:
        target = os.path.realpath(path)
    except OSError:
        pass
    if not os.path.exists(target):
        try:
            os.makedirs(target, exist_ok=True)
        except OSError:
            pass

    try:
        if os.name == "nt":
            os.startfile(target)  # type: ignore[attr-defined]
            return True
        if os.name == "posix":
            opener = None
            if os.environ.get("XDG_SESSION_TYPE") == "wayland":
                opener = "xdg-open"
            if opener is None:
                opener = "xdg-open"
            try:
                subprocess.Popen([opener, target])
                return True
            except (OSError, ValueError):
                pass
            try:
                subprocess.Popen(["open", target])
                return True
            except (OSError, ValueError):
                pass
        return False
    except Exception:
        return False