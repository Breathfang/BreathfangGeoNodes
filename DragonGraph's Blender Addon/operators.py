"""Operators backing every button in the Toolset Pack loader UI.

Implementation status per button, so nothing is a surprise in review:

===========================  ==================================================
Operator                     Behaviour
===========================  ==================================================
check_updates                Placeholder. Reports the installed version and
                             points at the releases page. Online access is
                             probed first, as Blender requires for network use.
    toggle_asset_library         Real. Loading creates (or re-ticks) the
                             ``assets/`` asset library entry; unloading
                             *unticks* it and deletes nothing. Refreshes open
                             Asset Browsers either way. Drives the load/unload
                             label swap.
reload_from_library          Real. Purges previously appended pack node groups
                             and re-appends them.
open_docs / report_bug       Real. ``bpy.ops.wm.url_open``.
    manual_load                  Real. ``.zip``-only file picker. The archive
                              can be picked from anywhere the user chooses; it
                              is unpacked into ``assets/extracted/`` and the
                              node groups it carries are appended. A pack's
                              ``blender_assets.cats.txt`` is merged into the
                              asset library root, where Blender reads it. The
                              library entry is left ticked throughout; it is not
                              unticked for the swap.
redownload                   Placeholder. Probes online access and reports the
                             target directory it would write into.
uninstall                    Real, destructive-by-intent. Confirmation popup.
                             Unticks and *deletes* the asset library entry (the
                             toggle only unticks) and drops unused pack node
                             groups. Never deletes files from disk.
===========================  ==================================================
"""

import os

import bpy

from . import constants
from . import library_manager
from .preferences import get_prefs

__all__ = ("classes", "register", "unregister")


class DRAGONGRAPH_OT_check_updates(bpy.types.Operator):
    """Check GitHub for a newer build of the Toolset Pack."""

    bl_idname = "dragongraph.check_updates"
    bl_label = constants.LABEL_CHECK_UPDATES
    bl_description = "Placeholder: query the releases page for a newer pack build"
    bl_options = {"REGISTER"}

    def execute(self, context):
        self.report(
            {"INFO"},
            "Installed add-on version: {}".format(constants.ADDON_VERSION_STRING),
        )

        if library_manager.online_access_granted():
            self.report(
                {"INFO"},
                "Online access is granted - a release check would query {} "
                "here.".format(constants.RELEASES_URL),
            )
        else:
            self.report(
                {"WARNING"},
                "Online access is disabled, so no release check can be made. "
                "Enable it in Preferences > System > Network, or open {} "
                "manually.".format(constants.RELEASES_URL),
            )

        return {"FINISHED"}


class DRAGONGRAPH_OT_toggle_asset_library(bpy.types.Operator):
    """Tick or untick the pack in Blender's Asset Library list.

    Turning this off unticks the entry; it does not delete it, and it touches
    nothing else.  The pack's node groups stay in the open file, files on disk
    stay where they are, and the entry can be re-ticked to load again.
    """

    bl_idname = "dragongraph.toggle_asset_library"
    bl_label = constants.LABEL_LOAD_LIBRARY
    bl_description = (
        "Load or unload the Toolset Pack as an asset library. Unloading unticks "
        "the entry in Preferences > File Paths > Asset Libraries; it deletes "
        "nothing"
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        prefs = get_prefs(context)
        if prefs is None:
            self.report(
                {"ERROR"},
                "Could not read the add-on preferences. Re-enable the add-on.",
            )
            return {"CANCELLED"}

        target = not prefs.use_asset_library
        message = prefs.set_asset_library_toggle(target)

        if target and not message:
            self.report(
                {"ERROR"},
                "Could not register '{}' in the Asset Library.".format(
                    constants.ASSET_LIBRARY_NAME
                ),
            )
            return {"CANCELLED"}

        if message:
            self.report({"INFO"}, message)

        # Refresh on both directions, not just on load: an untick changes what the
        # Asset Browser should be listing, and without this the pack keeps showing
        # in an open browser until the user restarts Blender.
        if library_manager.refresh_asset_browsers(context) == 0 and target:
            self.report(
                {"INFO"},
                "No Asset Browser was open to refresh; open one to see the pack.",
            )

        return {"FINISHED"}


class DRAGONGRAPH_OT_fix_duplicate_libraries(bpy.types.Operator):
    """Untick any other asset library that also contains this Toolset Pack.

    Blender registers every asset once per library that can see it, so a single
    ``.blend`` reachable from two libraries registers all of its assets twice and
    the console fills with ``N duplicate(s)`` for each one.  The add-on owns one of
    those two entries and cannot remove the other, so this unticks the offending
    library instead of leaving the user to find it in the console.

    Untick, not delete: the entry stays in Preferences and can be re-ticked.  It is
    also the only correct fix, because a library that is not ticked is not scanned
    and cannot register anything.
    """

    bl_idname = "dragongraph.fix_duplicate_libraries"
    bl_label = constants.LABEL_FIX_DUPLICATE_LIBRARIES
    bl_description = (
        "Untick any other asset library that also contains this Toolset Pack, so "
        "Blender stops registering its assets twice"
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        # refresh=True, not the cached value: the button is the user's answer to
        # the warning, so it has to act on what is true now, not on what was true
        # when the add-on was enabled.
        offenders = library_manager.duplicate_asset_libraries(refresh=True)
        if not offenders:
            self.report(
                {"INFO"},
                "No other asset library contains this pack; nothing to fix.",
            )
            return {"FINISHED"}

        for library, _folders in offenders:
            library.enabled = False

        # The cached answer still names the libraries just unticked, so without this
        # the panel keeps offering a button for a clash that no longer exists.
        library_manager.invalidate_duplicate_cache()

        library_manager.refresh_asset_browsers(context)

        # Naming the libraries matters more than the count here: the user has to
        # know which entry to re-tick if they want it back, and the count alone
        # would not tell them.
        self.report(
            {"INFO"},
            "Unticked {} asset librar{} that also contained this pack: {}. Re-tick "
            "any of them in Preferences > File Paths > Asset Libraries if you "
            "want it back.".format(
                len(offenders),
                "y" if len(offenders) == 1 else "ies",
                ", ".join(repr(library.name) for library, _folders in offenders),
            ),
        )
        return {"FINISHED"}


class DRAGONGRAPH_OT_reload_from_library(bpy.types.Operator):
    """Purge and re-append the Geometry Nodes libraries shipped with the pack."""

    bl_idname = "dragongraph.reload_from_library"
    bl_label = constants.LABEL_RELOAD_LIBRARY
    bl_description = "Reload the Toolset Pack node groups from the shipped library"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        blend_files = list(library_manager.iter_pack_blend_files())
        if not blend_files:
            self.report(
                {"ERROR"},
                "No library .blend found under {}. Use Redownload or Manually "
                "load to fetch it.".format(library_manager.addon_root()),
            )
            return {"CANCELLED"}

        removed, kept = library_manager.purge_pack_data(include_used=False)
        loaded, skipped, failed = library_manager.load_node_groups(
            blend_files, force=True
        )
        library_manager.invalidate_duplicate_cache()

        self.report(
            {"INFO"},
            "Reloaded {} of {} librar{}.".format(
                loaded, len(blend_files), "y" if len(blend_files) == 1 else "ies"
            ),
        )
        if removed:
            self.report({"INFO"}, "Removed {} stale node group(s).".format(removed))
        if kept:
            self.report(
                {"WARNING"},
                "{} node group(s) are still used by the open file and were kept; "
                "duplicate names may appear until they are removed "
                "manually.".format(kept),
            )
        if skipped:
            self.report({"INFO"}, "Skipped {} unchanged librar{}.".format(
                skipped, "y" if skipped == 1 else "ies"
            ))
        if failed:
            self.report(
                {"ERROR"},
                "Failed to read {} library file(s).".format(failed),
            )

        return {"FINISHED"}


class DRAGONGRAPH_OT_open_docs(bpy.types.Operator):
    """Open the Geometry Nodes documentation in a web browser."""

    bl_idname = "dragongraph.open_docs"
    bl_label = constants.LABEL_OPEN_DOCS
    bl_description = "Open the DragonGraph Geometry Nodes documentation"
    bl_options = {"REGISTER"}

    url = constants.DOCS_URL

    def execute(self, context):
        if not library_manager.open_url(self.url):
            self.report({"ERROR"}, "Could not open {}".format(self.url))
            return {"CANCELLED"}
        return {"FINISHED"}


class DRAGONGRAPH_OT_report_bug(bpy.types.Operator):
    """Open the GitHub issue tracker for the pack."""

    bl_idname = "dragongraph.report_bug"
    bl_label = constants.LABEL_REPORT_BUG
    bl_description = "Open the GitHub issue tracker for DragonGraph Geometry Nodes"
    bl_options = {"REGISTER"}

    url = constants.ISSUES_URL

    def execute(self, context):
        if not library_manager.open_url(self.url):
            self.report({"ERROR"}, "Could not open {}".format(self.url))
            return {"CANCELLED"}
        return {"FINISHED"}


class DRAGONGRAPH_OT_redownload(bpy.types.Operator):
    """Placeholder: download the latest pack into the add-on folder."""

    bl_idname = "dragongraph.redownload"
    bl_label = constants.LABEL_REDOWNLOAD
    bl_description = "Placeholder: download the latest Toolset Pack build"
    bl_options = {"REGISTER"}

    def execute(self, context):
        target = library_manager.asset_library_dir()
        self.report(
            {"INFO"},
            "Installed version: {}. Downloads would be written to {}.".format(
                constants.ADDON_VERSION_STRING, target
            ),
        )

        if not library_manager.online_access_granted():
            self.report(
                {"WARNING"},
                "Online access is disabled, so nothing can be downloaded. "
                "Enable it in Preferences > System > Network.",
            )
            return {"CANCELLED"}

        self.report(
            {"INFO"},
            "Placeholder: would download {} and unpack it into {}.".format(
                constants.RELEASES_URL, target
            ),
        )
        return {"FINISHED"}


class DRAGONGRAPH_OT_manual_load(bpy.types.Operator):
    """Unpack and load a pack ``.zip`` the user points at.

    Only ``.zip`` is accepted, so the picker (``filter_glob``) and
    :meth:`execute` agree: there is one supported archive format and the user
    cannot accidentally hand the operator a ``.blend`` it does not unpack.

    The archive can be picked from anywhere -- a Downloads folder, a USB
    stick, the add-on's own ``assets/``.  The user selecting a file in a file
    browser is the authority on where it reads from, and "manually load" would
    be useless if the pack had to be copied into the add-on first.

    Where it *expands to* is the add-on's decision, not the archive's: everything
    is written to ``assets/extracted/`` and every member is checked to resolve
    inside that folder, so an untrusted zip cannot place a file anywhere else on
    disk.

    Order of operations: extract, then append, then make sure the asset-library
    entry is present and ticked.  The entry is *not* unticked for the duration of
    the swap; that was implemented and reverted because forcing a rescan on every
    load turned a latent duplicate-asset problem in the user's own library
    configuration into a wall of console errors.
    """

    bl_idname = "dragongraph.manual_load"
    bl_label = constants.LABEL_MANUAL_LOAD
    bl_description = (
        "Unpack a DragonGraph Toolset Pack .zip into assets/extracted/ and "
        "load the node groups it carries"
    )
    bl_options = {"REGISTER", "UNDO"}

    filename: bpy.props.StringProperty(
        name="Pack archive",
        description="Toolset Pack .zip to unpack",
        subtype="FILE_PATH",
        default="",
    )
    directory: bpy.props.StringProperty(
        name="Folder",
        description="Folder the pack .zip was picked from",
        subtype="DIR_PATH",
        default="",
    )
    #: The file browser reads its extension filter from a property literally
    #: named ``filter_glob`` on the operator -- it is not an argument
    #: ``StringProperty`` accepts, so it has to be declared separately and kept
    #: hidden from the UI.
    filter_glob: bpy.props.StringProperty(
        default="*.zip",
        options={"HIDDEN"},
    )

    def invoke(self, context, event):
        self.directory = library_manager.asset_library_dir()
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        prefs = get_prefs(context)

        # Blender may hand back the picked file as a full path in ``filename``
        # with ``directory`` left empty (or vice versa), so both shapes are
        # folded into one absolute path here.
        if os.path.isabs(self.filename):
            zip_path = self.filename
        else:
            base = self.directory or library_manager.asset_library_dir()
            zip_path = os.path.join(base, self.filename)

        # The archive itself may be read from anywhere: the user just chose it
        # in a file browser, and "manually load" exists precisely so a pack
        # downloaded to Downloads or a USB stick works without being copied
        # first.  Requiring the file to already sit inside the add-on made the
        # button fail for its actual use case.
        #
        # Where the archive *expands to* is the part that matters, and that is
        # not the user's choice to make: extract_pack_archive() always writes
        # into assets/extracted/ and rejects any member that resolves outside
        # it, so an untrusted zip cannot place a file anywhere else on disk.
        # Reading a file the user selected cannot write anything.
        if not self.filename.lower().endswith(constants.ALLOWED_PACK_ARCHIVE):
            self.report(
                {"ERROR"},
                "Select a {} archive.".format(constants.ALLOWED_PACK_ARCHIVE),
            )
            return {"CANCELLED"}

        if not os.path.isfile(zip_path):
            self.report({"ERROR"}, "File not found: {}".format(zip_path))
            return {"CANCELLED"}

        try:
            destination = library_manager.extract_pack_archive(zip_path)
        except (library_manager.PackPathsError, library_manager.PackArchiveError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}

        # Load everything the archive unpacked.  ``force=True`` because a
        # re-load of the same pack is the expected way to pick up a new version.
        blend_files = list(library_manager.iter_blend_files_in(destination))
        if not blend_files:
            self.report(
                {"WARNING"},
                "{} unpacked, but it holds no .blend libraries.".format(
                    os.path.basename(zip_path)
                ),
            )
            return {"FINISHED"}

        loaded, _skipped, failed = library_manager.load_node_groups(
            blend_files, force=True
        )
        if not loaded and failed:
            self.report(
                {"ERROR"},
                "Unpacked to {}, but no library could be read.".format(destination),
            )
            return {"CANCELLED"}

        # A pack that has just been unpacked has to be visible, so guarantee the
        # entry is present and ticked.  This reuses the existing row rather than
        # untick/re-creating it: the row already points at assets/, and the unpack
        # only changed the contents of assets/extracted/, so there is nothing to
        # re-point and no chance of ending up with two.
        #
        # NOTE: this deliberately does not untick the entry for the duration of the
        # swap.  Doing so was tried and reverted -- see the note on
        # ensure_asset_library_ticked for why forcing a rescan is not worth it.
        tick_message = library_manager.ensure_asset_library_ticked(
            prefs.import_method if prefs is not None else "PACK"
        )
        if tick_message:
            self.report({"INFO"}, tick_message)

        library_manager.refresh_asset_browsers(context)

        # The pack that was just unpacked is what the duplicate check compares
        # against, so the cached answer is about a file that no longer exists.
        library_manager.invalidate_duplicate_cache()

        message = "Unpacked {} to {} and loaded {} library file(s)".format(
            os.path.basename(zip_path), destination, loaded
        )
        if library_manager.catalog_file_installed():
            message += "; pack catalogs registered"
        if failed:
            message += " ({} file(s) could not be read)".format(failed)
        self.report({"WARNING"} if failed else {"INFO"}, message)
        return {"FINISHED"}


class DRAGONGRAPH_OT_open_extracted(bpy.types.Operator):
    """Open ``assets/extracted/`` in the system file explorer."""

    bl_idname = "dragongraph.open_extracted"
    bl_label = constants.LABEL_OPEN_EXTRACTED
    bl_description = "Reveal the folder that manually loaded packs are unpacked into"
    bl_options = {"REGISTER"}

    def execute(self, context):
        try:
            destination = library_manager.ensure_extracted_dir()
        except (library_manager.PackPathsError, OSError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}

        if not library_manager.open_folder(destination):
            self.report(
                {"ERROR"},
                "Could not open {} in your file explorer.".format(destination),
            )
            return {"CANCELLED"}
        self.report({"INFO"}, "Opened {}".format(destination))
        return {"FINISHED"}


class DRAGONGRAPH_OT_uninstall(bpy.types.Operator):
    """Remove the pack from Blender's Asset Libraries and drop its node groups."""

    bl_idname = "dragongraph.uninstall"
    bl_label = constants.LABEL_UNINSTALL
    bl_description = (
        "Remove DragonGraph's Toolset Pack from the Asset Library list and free "
        "the node groups it loaded. Files on disk are left untouched."
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        # Rendered with Blender's native red confirm button.
        return self.invoke_confirm(context, event)

    def draw(self, context):
        layout = self.layout
        layout.label(
            text="Remove '{}' from the Asset Library?".format(
                constants.ASSET_LIBRARY_NAME
            ),
            icon=constants.ICON_ERROR,
        )
        layout.label(text="Files in the add-on folder are not deleted.")

    def execute(self, context):
        prefs = get_prefs(context)

        if prefs is not None:
            # Unticks first (so the Asset Browser stops showing the pack straight
            # away), then deletes the entry.  Deleting is the point of
            # *uninstall*, as opposed to the Unload toggle, which only unticks.
            prefs.set_asset_library_toggle(False)
            prefs.purge_asset_library_entry()
        else:
            library_manager.set_asset_library_enabled(False)
            library_manager.unregister_asset_library()

        removed, kept = library_manager.purge_pack_data(include_used=False)

        if kept:
            self.report(
                {"WARNING"},
                "{} pack node group(s) are still used by this file and were kept. "
                "Remove them from the Outliner if you want a clean uninstall.".format(
                    kept
                ),
            )

        self.report(
            {"INFO"},
            "Uninstalled. {} node group(s) removed from memory; the add-on's own "
            "files were left in place.".format(removed),
        )
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# Backwards compatibility
# ---------------------------------------------------------------------------


class NODE_OT_reload_gn_toolset_pack(bpy.types.Operator):
    """Deprecated alias for :class:`DRAGONGRAPH_OT_reload_from_library`.

    Kept registered so existing keymaps and scripts written against the
    pre-1.0 ``node.reload_gn_toolset_pack`` idname keep working.
    """

    bl_idname = "node.reload_gn_toolset_pack"
    bl_label = "Reload DragonGraph's Toolset Pack"
    bl_description = "Deprecated: use 'Reload from Asset Library' instead"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        self.report({"INFO"}, "This operator moved; using 'Reload from Asset Library'.")
        return bpy.ops.dragongraph.reload_from_library()


classes = (
    DRAGONGRAPH_OT_check_updates,
    DRAGONGRAPH_OT_toggle_asset_library,
    DRAGONGRAPH_OT_fix_duplicate_libraries,
    DRAGONGRAPH_OT_reload_from_library,
    DRAGONGRAPH_OT_open_docs,
    DRAGONGRAPH_OT_report_bug,
    DRAGONGRAPH_OT_redownload,
    DRAGONGRAPH_OT_manual_load,
    DRAGONGRAPH_OT_open_extracted,
    DRAGONGRAPH_OT_uninstall,
    NODE_OT_reload_gn_toolset_pack,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)