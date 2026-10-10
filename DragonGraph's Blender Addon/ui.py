"""UI for the Toolset Pack loader.

A single :func:`draw_toolset_pack_layout` builds the whole panel, and both the
Add-on Preferences (``AddonPreferences.draw``) and the 3D Viewport N-panel call
it.  One layout function means the two entry points can never drift apart.

The panel is a stack of cards.  Each logical section draws into its own box via
:func:`_card`, and the boxes supply their own padding and borders, so no
separators are drawn between them.  The single exception to "one card per action"
is the Maintenance card, which deliberately groups uninstall with redownload and
manual load; see :func:`_draw_maintenance` for why.

Icon note: Blender ships no ``DOCS`` and no ``GITHUB`` icon identifier, so
``HELP`` stands in for the documentation link and ``URL`` for the repository,
as permitted by the spec.
"""

import traceback

import bpy

from . import constants
from . import library_manager
from .preferences import LINK_WARNING, LINK_WARNING_TITLE, get_prefs
from .operators import (
    DRAGONGRAPH_OT_check_updates,
    DRAGONGRAPH_OT_fix_duplicate_libraries,
    DRAGONGRAPH_OT_manual_load,
    DRAGONGRAPH_OT_open_extracted,
    DRAGONGRAPH_OT_open_docs,
    DRAGONGRAPH_OT_redownload,
    DRAGONGRAPH_OT_reload_from_library,
    DRAGONGRAPH_OT_report_bug,
    DRAGONGRAPH_OT_toggle_asset_library,
    DRAGONGRAPH_OT_uninstall,
)

__all__ = (
    "DRAGONGRAPH_PT_toolset_pack_sidebar",
    "classes",
    "draw_guarded",
    "draw_toolset_pack_layout",
    "register",
    "unregister",
)


def _card(layout, header: str | None = None, icon: str = "NONE", alert: bool = False):
    """Return a new box, optionally headed by a label and drawn in the alert colour.

    Every section of this panel is its own card.  A box supplies its own padding
    and border, so the sections read as separate units without separators stacked
    between them, and one section can be added or moved without disturbing the
    spacing of the others.  ``icon`` is passed straight through to
    ``UILayout.label``; ``"NONE"`` is Blender's own "no icon" identifier.

    ``alert`` is set *before* the header is drawn, so a warning card tints its own
    title as well as its body.  Setting it afterwards would leave the header in
    the normal colour, which reads as a separate section.
    """
    box = layout.box()
    if alert:
        # UILayout.alert is a writable RNA property in Blender 5.x; everything
        # drawn into a layout in the alert state renders in the alert colour.
        box.alert = True
    if header is not None:
        box.label(text=header, icon=icon)
    return box


def _draw_header(layout) -> None:
    """Identity card: what this is, which version, and what it does."""
    box = _card(layout)
    box.label(text=constants.ADDON_TITLE, icon="NODETREE")
    # Version and description each get their own line: side by side in a narrow
    # sidebar column they truncate to nothing.
    box.label(text="Version {}".format(constants.ADDON_VERSION_STRING))
    box.label(text=constants.DESCRIPTION_SHORT)


def _draw_operations(layout, prefs) -> None:
    """Asset-operations card: the actions a user reaches for most."""
    box = _card(layout, constants.HEADER_ASSET_LIBRARY, constants.ICON_INFO)

    box.operator(
        DRAGONGRAPH_OT_check_updates.bl_idname,
        text=constants.LABEL_CHECK_UPDATES,
        icon=constants.ICON_CHECK_UPDATES,
    )

    row = box.row(align=True)
    row.operator(
        DRAGONGRAPH_OT_reload_from_library.bl_idname,
        text=constants.LABEL_RELOAD_LIBRARY,
        icon=constants.ICON_RELOAD,
    )
    if prefs is not None and prefs.use_asset_library:
        toggle_text = constants.LABEL_UNLOAD_LIBRARY
        toggle_icon = constants.ICON_UNLOAD
    else:
        toggle_text = constants.LABEL_LOAD_LIBRARY
        toggle_icon = constants.ICON_LOAD
    row.operator(
        DRAGONGRAPH_OT_toggle_asset_library.bl_idname,
        text=toggle_text,
        icon=toggle_icon,
    )

    box.operator(
        DRAGONGRAPH_OT_open_docs.bl_idname,
        text=constants.LABEL_OPEN_DOCS,
        icon=constants.ICON_DOCS,
    )
    box.operator(
        DRAGONGRAPH_OT_report_bug.bl_idname,
        text=constants.LABEL_REPORT_BUG,
        icon=constants.ICON_BUG,
    )


def _draw_maintenance(layout) -> None:
    """Maintenance card: fetching or pointing at the pack by hand, plus uninstall.

    These three actions share one card because they are the same kind of thing --
    whole-installation changes rather than working with nodes -- and separating
    uninstall into a card of its own gave a one-button panel section.

    Only the uninstall *row* is drawn in the alert colour, not the whole card.
    Tinting the card would mark "Redownload" and "Manually load" as destructive
    too, which they are not.  A full-width alert row is still enough to read as
    destructive, and it keeps the button the single most visually distinct control
    on the panel.
    """
    box = _card(layout, constants.HEADER_MAINTENANCE, constants.ICON_INFO)

    row = box.row(align=True)
    row.operator(
        DRAGONGRAPH_OT_redownload.bl_idname,
        text=constants.LABEL_REDOWNLOAD,
        icon=constants.ICON_REDOWNLOAD,
    )
    row.operator(
        DRAGONGRAPH_OT_manual_load.bl_idname,
        text=constants.LABEL_MANUAL_LOAD,
        icon=constants.ICON_MANUAL_LOAD,
    )

    danger = box.row()
    danger.alert = True
    danger.operator(
        DRAGONGRAPH_OT_uninstall.bl_idname,
        text=constants.LABEL_UNINSTALL,
        icon=constants.ICON_UNINSTALL,
    )

    box.operator(
        DRAGONGRAPH_OT_open_extracted.bl_idname,
        text=constants.LABEL_OPEN_EXTRACTED,
        icon=constants.ICON_OPEN_EXTRACTED,
    )

    _draw_duplicate_library_fix(box)


def _draw_duplicate_library_fix(layout) -> None:
    """Offer the duplicate-asset fix, but only when there is a clash to fix.

    Drawn conditionally on purpose.  A button that is always there would either be
    noise for everyone whose library list is fine, or -- worse -- invite someone to
    press it and untick a library they rely on.  Walking the pack tree to decide
    whether to show it is cheap here: it only runs while the panel is being drawn
    and the pack is a handful of ``.blend`` files.
    """
    if not library_manager.duplicate_asset_libraries():
        return

    row = layout.row(align=True)
    row.alert = True
    row.operator(
        DRAGONGRAPH_OT_fix_duplicate_libraries.bl_idname,
        text=constants.LABEL_FIX_DUPLICATE_LIBRARIES,
        icon=constants.ICON_INFO,
    )


def _draw_link_warning(layout, prefs) -> None:
    """Warning card, shown only while the link-based import method is selected.

    Linking leaves this file pointing at ``.blend`` files inside the add-on
    folder, so the node groups can change or break underneath the user when the
    pack is updated. The text is only worth the space while that is true, so it
    gets its own card rather than a box buried inside the status card.
    """
    if not prefs.is_link_import():
        return

    box = _card(layout, LINK_WARNING_TITLE, constants.ICON_ERROR, alert=True)
    box.label(text=LINK_WARNING)


def _draw_status(layout, prefs) -> None:
    """Status card: what the add-on found, and where it looked."""
    box = _card(layout, constants.HEADER_STATUS, constants.ICON_INFO)
    box.label(text=prefs.status_line())
    box.label(text=library_manager.asset_library_dir())


def _draw_settings(layout, prefs) -> None:
    """Preferences-only extras: the settings card and its Blender links."""
    box = _card(layout, constants.HEADER_SETTINGS, "PREFERENCES")

    column = box.column(align=True)
    column.prop(prefs, "import_method")

    # The dynamic load/unload switch is the same property the button writes, so
    # ticking it in Preferences registers the library just as the button does.
    box.prop(prefs, "use_asset_library")

    # These two are Blender's own operators, verified to exist in 5.2.  The
    # panel already has an implicit context override, so no manual
    # temp_override is needed to reach the Preferences window.
    box.operator(
        "preferences.addon_show",
        text="Open Add-on Preferences",
        icon="PREFERENCES",
    )


def draw_toolset_pack_layout(layout, context, show_settings: bool = False) -> None:
    """Draw the full loader panel as a stack of cards.

    Every section draws into its own box: identity, asset operations,
    maintenance, and -- in Preferences only -- status, the link warning and
    settings.  The cards provide their own padding and borders, which is why
    there are no separators between them: a separator between two bordered boxes
    reads as a stray line.

    ``show_settings`` adds the Preferences-only cards so the N-panel stays
    compact; both entry points still come from this one function, so the two
    cannot drift apart.
    """
    prefs = get_prefs(context)

    _draw_header(layout)
    _draw_operations(layout, prefs)
    _draw_maintenance(layout)

    if not show_settings:
        return

    if prefs is None:
        box = _card(layout, alert=True)
        box.label(text=constants.LABEL_PREFS_UNAVAILABLE, icon=constants.ICON_ERROR)
        return

    _draw_status(layout, prefs)
    _draw_link_warning(layout, prefs)
    _draw_settings(layout, prefs)


def draw_guarded(layout, context, show_settings: bool = False) -> None:
    """Draw the panel, turning any failure into a visible card.

    Blender catches an exception raised inside a panel's ``draw`` and simply
    abandons the panel.  The result is an empty panel with nothing on screen and
    no obvious cause unless the console happens to be open -- which is exactly
    the "the tab is there but it is blank" symptom, and it gives no clue which
    card failed.  So the failure is caught here, reported in the panel itself,
    and printed with its traceback.

    The fallback card is drawn inside its own ``try``: if drawing the error is
    what fails, the original exception still reaches the console rather than
    being replaced by a confusing second one.
    """
    try:
        draw_toolset_pack_layout(layout, context, show_settings=show_settings)
    except Exception as error:
        print("[{}] Panel draw failed:\n{}".format(
            constants.ADDON_TITLE, traceback.format_exc()))
        try:
            box = _card(layout, "Panel could not be drawn", constants.ICON_ERROR,
                        alert=True)
            box.label(text="{}: {}".format(type(error).__name__, error),
                      icon=constants.ICON_ERROR)
            box.label(text="The full traceback is in the system console.")
        except Exception:
            pass


class DRAGONGRAPH_PT_toolset_pack_sidebar(bpy.types.Panel):
    """Toolset Pack loader, 3D Viewport N-panel."""

    bl_label = constants.ADDON_TITLE
    bl_idname = "DRAGONGRAPH_PT_toolset_pack_sidebar"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "DragonGraph"

    def draw(self, context):
        draw_guarded(self.layout, context, show_settings=False)


classes = (
    DRAGONGRAPH_PT_toolset_pack_sidebar,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)