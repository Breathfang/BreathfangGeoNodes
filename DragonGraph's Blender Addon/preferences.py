"""Add-on preferences for the Toolset Pack loader.

The single most important property here is
:attr:`DRAGONGRAPH_AddonPreferences.use_asset_library`.  It is the dynamic
boolean that drives the "Load it to Asset Library" / "Unload from Asset
Library" label swap in the UI, and it is also the *authoritative* record of
whether the pack is registered -- changing it performs the registration.

The update callback is re-entrant by nature (the operators write the property
to request an action, and writing it triggers the callback), so every internal
write goes through :meth:`DRAGONGRAPH_AddonPreferences.set_asset_library_toggle`
which holds a module-level lock for the duration.
"""

import bpy

from . import constants
from . import library_manager

__all__ = (
    "LINK_WARNING",
    "LINK_WARNING_TITLE",
    "DRAGONGRAPH_AddonPreferences",
    "classes",
    "get_prefs",
    "register",
    "unregister",
)

# Guards the write performed by ``set_asset_library_toggle`` so that the
# property's update callback does not recurse into a second register/unregister.
_TOGGLE_LOCK = False

# Only the three values Blender 5.2 actually accepts on
# ``UserAssetLibrary.import_method``.  ``APPEND_REUSE`` still appears in the
# RNA enum items but assigning it raises, so it is deliberately not offered.
_IMPORT_METHODS = (
    (
        "LINK",
        "Link (Not Recommended)",
        "Link the assets instead of copying them. The node groups in this file "
        "stay tied to the pack on disk, so they can change or break without "
        "warning when the pack is updated, moved or deleted",
    ),
    ("APPEND", "Append", "Copy the asset data into the current file"),
    ("PACK", "Pack", "Copy the asset and everything it depends on into the file"),
)

#: Shown in the status box while ``import_method`` is ``LINK``.  Linking is a
#: legitimate choice, but the file becomes dependent on a path on disk that the
#: add-on does not control, so it is worth saying out loud.
LINK_WARNING = (
    "Link is not recommended. These node groups stay connected to the files in "
    "the add-on folder, so an update, a move or a delete can change or break "
    "them in this file without warning. Use Append or Pack unless you need to "
    "edit the pack's nodes in place."
)
LINK_WARNING_TITLE = "Linked data depends on the add-on folder"


def get_prefs(context=None):
    """Return this add-on's :class:`AddonPreferences`, or ``None``.

    Keyed on ``__package__``, which resolves to the plain package name for a
    legacy add-on and to ``bl_ext.<repo>.<id>`` for an extension -- the same
    string used for ``bl_idname``, so both install paths work unchanged.

    Note: Blender returns a *fresh* Python wrapper on every
    ``preferences.addons[...]`` access, so callers must compare the result by
    value, never with ``is``.  That is fine here because everything written
    through the wrapper goes straight into the underlying ID properties.
    """
    ctx = context if context is not None else bpy.context
    try:
        addons = ctx.preferences.addons
    except AttributeError:
        return None
    addon = addons.get(__package__)
    if addon is None:
        return None
    return addon.preferences


class DRAGONGRAPH_AddonPreferences(bpy.types.AddonPreferences):
    """Settings and status for the Toolset Pack loader."""

    bl_idname = __package__
    bl_label = constants.ADDON_TITLE

    # -- Dynamic load/unload toggle ----------------------------------------
    use_asset_library: bpy.props.BoolProperty(
        name="Use Asset Library",
        description=(
            "Whether DragonGraph's Toolset Pack is ticked as an asset library in "
            "Blender's Preferences. Ticking this adds the entry, unticking it "
            "only hides the pack from the Asset Browser: the entry, your node "
            "groups and every file are left alone"
        ),
        default=False,
        update=lambda self, context: self._on_toggle_changed(),
    )

    # -- Behaviour ---------------------------------------------------------
    import_method: bpy.props.EnumProperty(
        name="Import Method",
        description="How assets from the Toolset Pack are brought into a file",
        items=_IMPORT_METHODS,
        default="PACK",
        update=lambda self, context: self._on_import_method_changed(),
    )

    # Kept so an existing preferences file from a build that had the checkbox
    # still loads, and so nothing referencing it raises. It no longer controls
    # anything: the pack is reached through the Asset Library, and appending it
    # into every opened file cost the user open-time performance and produced
    # "asset has invalid metadata" reports.
    auto_load_on_open: bpy.props.BoolProperty(
        name="Load on File Open (Removed)",
        description=(
            "No longer used. The Toolset Pack is available from Blender's Asset "
            "Browser without copying its node groups into every file you open"
        ),
        default=False,
    )

    # -- Toggle plumbing ---------------------------------------------------
    def _on_toggle_changed(self) -> None:
        if _TOGGLE_LOCK:
            return
        message = self.apply_asset_library_state()
        if message:
            print("[{}] {}".format(constants.ADDON_TITLE, message))

    def set_asset_library_toggle(self, value) -> str:
        """Request a load/unload without re-entering the update callback.

        Returns a status message for the caller to surface as a report.
        """
        global _TOGGLE_LOCK

        value = bool(value)
        _TOGGLE_LOCK = True
        try:
            self.use_asset_library = value
        finally:
            _TOGGLE_LOCK = False

        return self.apply_asset_library_state()

    def apply_asset_library_state(self) -> str:
        """Make the Asset Browser match :attr:`use_asset_library`.

        Unloading *unticks* the entry; it never deletes it.  That is what the user
        does by hand in Preferences > File Paths > Asset Libraries, and it means
        unloading is reversible: the entry keeps its path and import method, so
        loading again is one click and a mis-click costs nothing.  Deleting the
        entry is a separate, deliberately awkward action
        (:meth:`purge_asset_library_entry`).
        """
        if self.use_asset_library:
            try:
                library, created = library_manager.register_asset_library(
                    self.import_method
                )
            except (OSError, library_manager.PackPathsError) as error:
                return "Could not register the asset library: {}".format(error)
            verb = "Registered" if created else "Re-enabled"
            return "{} '{}' at {}".format(verb, library.path, library.name)

        if not library_manager.is_asset_library_registered():
            return ""

        library_manager.set_asset_library_enabled(False)
        return "Untick of '{}': the entry is kept, untick it again to load".format(
            constants.ASSET_LIBRARY_NAME
        )

    def purge_asset_library_entry(self) -> bool:
        """Delete the Asset Libraries entry outright. Returns ``True`` if deleted.

        Not wired to any button.  It exists so that a user who *does* want the
        entry gone from Preferences has a way to ask for that explicitly, and so
        that "untick to unload" cannot be mistaken for "the add-on cleans up after
        itself".
        """
        return library_manager.unregister_asset_library()

    def _on_import_method_changed(self) -> None:
        # Deliberately not gated on ``use_asset_library``: if the entry exists
        # (even if the toggle is momentarily out of sync after the user deleted
        # it by hand) the new value should still be applied to it.
        library = library_manager.find_asset_library()
        if library is not None:
            library.import_method = self.import_method

    # -- Status helpers used by the UI and by operators --------------------
    def sync_toggle_with_preferences(self) -> None:
        """Adopt the real registration state after an external change.

        For example the user unticked the entry by hand in
        Preferences > File Paths > Asset Libraries, or deleted it outright.

        This reads the *ticked* state, not mere existence, because unticking is
        how the add-on unloads.  A user who unticks the library in Preferences is
        saying "unload", and the toggle has to reflect that or the panel would
        claim the pack is loaded while the Asset Browser is not showing it.
        """
        global _TOGGLE_LOCK

        actual = library_manager.is_asset_library_enabled()
        if actual == self.use_asset_library:
            return
        _TOGGLE_LOCK = True
        try:
            self.use_asset_library = actual
        finally:
            _TOGGLE_LOCK = False

    def is_link_import(self) -> bool:
        """True while the risky link-based import method is selected."""
        return self.import_method == "LINK"

    def status_line(self) -> str:
        """One-line human summary of the current state.

        A kept-but-unticked entry is reported as not loaded, since that is what
        the user experiences: the pack is not in the Asset Browser.
        """
        if library_manager.is_asset_library_enabled():
            count = library_manager.pack_asset_count()
            return "Loaded - {} asset librar{} found".format(
                count, "y" if count == 1 else "ies"
            )
        if library_manager.is_asset_library_registered():
            return "Unloaded - the Asset Library entry is kept but unticked"
        if library_manager.is_pack_installed():
            return "Not loaded - press Load it to Asset Library"
        if library_manager.is_pack_installed():
            return "Not loaded - press Load it to Asset Library"
        return "No library files found in {}".format(
            library_manager.asset_library_dir()
        )

    # -- Add-on Preferences UI --------------------------------------------
    def draw(self, context):
        # Imported here rather than at module scope: ui imports this module.
        from . import ui

        ui.draw_guarded(self.layout, context, show_settings=True)


def _report_duplicate_libraries() -> None:
    """Name any other library that also exposes the pack, on enable.

    Blender registers each asset once per library that can see it, so one
    ``.blend`` reachable from two libraries makes every asset in it log
    ``N duplicate(s)``.  The add-on only controls one of the two entries, so it
    cannot resolve this, but it can say which library to untick instead of leaving
    the user to reverse-engineer console spam.

    Printed rather than reported: there is no operator context to report from at
    registration time, and a user who has hit this has Blender's console open in
    front of them precisely because the errors are appearing there.

    The result is cached by the check itself, so this is the one walk that enable
    pays for.  Caching it here rather than in the panel is the point: Blender
    redraws a panel on every pointer move, and an uncached walk per redraw is what
    made Blender appear to hang.
    """
    from . import library_manager

    library_manager.invalidate_duplicate_cache()
    for message in library_manager.duplicate_asset_library_warnings():
        print("[{}] WARNING: {}".format(constants.ADDON_TITLE, message))


classes = (
    DRAGONGRAPH_AddonPreferences,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    _report_duplicate_libraries()


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)