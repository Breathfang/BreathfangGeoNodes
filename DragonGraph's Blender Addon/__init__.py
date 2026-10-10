"""DragonGraph's Toolset Pack Loader.

A UI manager that keeps DragonGraph's Geometry Nodes Toolset Pack registered as
an asset library inside Blender's Asset Browser, without the user ever having
to touch Preferences > File Paths > Asset Libraries by hand.

Packaging
---------
This folder is the add-on package. It is shipped as a ``.zip`` and installed
through Blender's standard installer, exactly like an official or nightly
build:

* With ``blender_manifest.toml`` present, Blender treats it as an **extension**
  and installs it to ``<user_resource>/extensions/<repo>/<id>/``; the module
  namespace becomes ``bl_ext.<repo>.<id>``.
* Without the manifest, Blender treats it as a **legacy add-on** using the
  ``bl_info`` dictionary below and installs it to ``<user_resource>/addons/``.

Every module therefore uses ``__package__`` (never a hard-coded name) and
relative imports, so both paths work with no code changes.

Directory isolation
-------------------
``constants.ADDON_ROOT`` is resolved with
``os.path.dirname(os.path.realpath(__file__))`` and is the *only* project root
this add-on ever touches. The asset library registered with Blender is
``ADDON_ROOT/assets``; every library ``.blend`` and every path passed to
``bpy.data.libraries.load()`` is validated against that root by
``library_manager.ensure_inside_addon()``.

"Manually load" unpacks a pack ``.zip`` into ``assets/extracted/``. Reading
the archive is the user's choice -- they picked it in a file browser, and a pack
downloaded to ``Downloads`` must not have to be copied in first. Writing is not:
the destination is always inside the add-on, and archive members that name an
absolute path, a ``..`` segment or a symlink are refused rather than being
stripped, so an untrusted archive cannot place a file anywhere else on disk.
Members are written directly into ``extracted/`` with their own names, because
the add-on path is already long enough that repeating the archive's name in a
subfolder pushes a pack's library past Windows' 260 character path limit.
Destinations are length-checked before anything is written, so a path that would
still be too long is reported as such instead of failing as a missing file.

A pack's ``blender_assets.cats.txt`` is merged into ``assets/`` rather than left
in ``extracted/``, because Blender reads the catalog file only from the root of an
asset library.

Target: Blender 5.2 and 5.3+ (Python 3.13).
"""

bl_info = {
    "name": "DragonGraph's Toolset Pack Loader",
    "author": "DragonGraph / Breathfang",
    "version": (1, 0, 0),
    "blender": (5, 2, 0),
    "location": "View3D > Sidebar (N) > DragonGraph",
    "description": (
        "UI manager that loads DragonGraph's Geometry Nodes Toolset Pack into "
        "Blender's Asset Browser from inside its own add-on folder"
    ),
    "category": "Geometry Nodes",
    "doc_url": "https://breathfanggeonodes.readthedocs.io/en/latest/",
    "tracker_url": "https://github.com/Breathfang/BreathfangGeoNodes/issues",
    "website": "https://github.com/Breathfang/BreathfangGeoNodes",
    "support": "COMMUNITY",
}

import bpy

from . import constants
from . import library_manager
from . import operators
from . import preferences
from . import ui

__all__ = ("bl_info", "register", "unregister")


# ---------------------------------------------------------------------------
# Add > Node menu entry (Node Editor shortcuts > Add)
# ---------------------------------------------------------------------------


def _menu_func(self, context):
    self.layout.separator()
    self.layout.operator(
        operators.DRAGONGRAPH_OT_reload_from_library.bl_idname,
        text=constants.LABEL_RELOAD_LIBRARY,
        icon=constants.ICON_RELOAD,
    )


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


#: Whether the ``load_post`` handler is allowed to append the pack into the file
#: Blender just opened.  It is ``False`` and must stay ``False``; the flag exists
#: so the decision is a named, testable value rather than the absence of code, and
#: so a future attempt to re-enable it has to flip this deliberately.
AUTO_APPEND_ON_LOAD = False


@bpy.app.handlers.persistent
def _on_load_post(_dummy):
    """Deliberately does nothing.

    This add-on used to append the pack's node groups into every file Blender
    opened.  That was a bad idea twice over:

    * Appending copies every group into the current file, so opening a file, or
      creating a new one, paid for the whole pack.  The pack is already
      available through the registered Asset Library, which needs no copy.
    * The copies carried asset metadata whose catalog the opened file does not
      know about, so Blender re-validated and reported them as
      "asset has invalid metadata" on open.

    The handler is still registered (and still ``@persistent``) so that a file
    saved by an older build, which expects it in ``load_post``, does not fail
    ``remove()`` on unregister, and so the behaviour has one obvious place to
    live if it is ever wanted again.  It must never append to the open file.
    """
    if AUTO_APPEND_ON_LOAD:  # pragma: no cover - guarded off on purpose
        raise AssertionError(
            "AUTO_APPEND_ON_LOAD must stay False: appending the pack into every "
            "opened file is what this handler was changed to stop doing."
        )
    return


def _startup_state():
    """Re-establish the asset library entry after the add-on is enabled.

    ``use_asset_library`` is authoritative: if the user removed the entry by
    hand in Preferences > File Paths > Asset Libraries, this puts it back.
    """
    prefs = preferences.get_prefs()
    if prefs is not None:
        prefs.apply_asset_library_state()


def register():
    # Preferences first: the UI and the operators both read them.
    preferences.register()
    operators.register()
    ui.register()

    bpy.types.NODE_MT_add.append(_menu_func)

    if _on_load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_on_load_post)

    _startup_state()


def unregister():
    if _on_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_on_load_post)

    try:
        bpy.types.NODE_MT_add.remove(_menu_func)
    except (ValueError, AttributeError):
        # Already removed, or the menu type is gone (5.3 reorganised the node
        # add menus). Disabling the add-on must never raise.
        pass

    ui.unregister()
    operators.unregister()
    preferences.unregister()


# ---------------------------------------------------------------------------
# Text-editor escape hatch
#
# Relative imports need a package context, so running this file directly with
# "Run Script" re-imports the folder as a proper package first. Installing the
# zip is the supported route; this only exists so the add-on can be smoke
# tested from the scripting workspace.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import importlib
    import os
    import sys

    _root = os.path.dirname(os.path.realpath(__file__))
    _parent = os.path.dirname(_root)
    _package = os.path.basename(_root)

    if _parent not in sys.path:
        sys.path.insert(0, _parent)

    _module = importlib.import_module(_package)
    _module.register()