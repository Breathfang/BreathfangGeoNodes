"""Static configuration for the "DragonGraph's Toolset Pack Loader" add-on.

This module owns two things that nothing else in the package is allowed to
recompute:

1. The add-on's own extracted folder root.  Blender (or the
   user, via the standard ``.zip`` installer) unpacks the add-on somewhere on
   disk; every path this add-on reads or writes is resolved relative to that
   root so the package stays self-contained and portable.
2. The user-facing strings (titles, URLs, button labels) so the UI modules stay
   declarative and a rebrand is a single-file change.

Nothing here imports ``bpy``: this module is loaded during Blender's add-on
discovery, before ``bpy`` is guaranteed to be usable from a text-editor run.
"""

import os

# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------

ADDON_TITLE = "DragonGraph's Toolset Pack Loader"
ADDON_AUTHOR = "DragonGraph / Breathfang"
ADDON_VERSION = (1, 0, 0)
ADDON_VERSION_STRING = "1.0.0"
BLENDER_VERSION_MIN = (5, 2, 0)

DESCRIPTION_SHORT = (
    "Loads and manages DragonGraph's Toolset Pack inside Blender's Asset Browser."
)

# ---------------------------------------------------------------------------
# External links
# ---------------------------------------------------------------------------

DOCS_URL = "https://breathfanggeonodes.readthedocs.io/en/latest/"
REPO_URL = "https://github.com/Breathfang/BreathfangGeoNodes"
ISSUES_URL = REPO_URL + "/issues"
RELEASES_URL = REPO_URL + "/releases/latest"

# ---------------------------------------------------------------------------
# Button labels (kept verbatim so the UI is translatable in one place)
# ---------------------------------------------------------------------------

LABEL_CHECK_UPDATES = "Check Updates for DragonGraph's Toolset Pack"
LABEL_RELOAD_LIBRARY = "Reload from Asset Library"
LABEL_LOAD_LIBRARY = "Load it to Asset Library"
LABEL_UNLOAD_LIBRARY = "Unload from Asset Library (untick)"
LABEL_OPEN_DOCS = "See Geometry Nodes Documentation"
LABEL_REPORT_BUG = "Report Geometry Nodes/Addon Bugs to Repository"
LABEL_REDOWNLOAD = "Redownload DragonGraph's Toolset Pack"
LABEL_MANUAL_LOAD = "Manually load DragonGraph's Toolset Pack"
LABEL_OPEN_EXTRACTED = "Open the Extracted Folder"
LABEL_UNINSTALL = "Uninstall DragonGraph's Toolset Pack"
LABEL_FIX_DUPLICATE_LIBRARIES = "Fix Duplicate Asset Libraries"
LABEL_PREFS_UNAVAILABLE = "Preferences unavailable"

# ---------------------------------------------------------------------------
# Card headers (one per box in the panel; see ui._card)
# ---------------------------------------------------------------------------

HEADER_ASSET_LIBRARY = "Asset Library"
HEADER_MAINTENANCE = "Maintenance"
HEADER_STATUS = "Status"
HEADER_SETTINGS = "Settings"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

#: Absolute path of this add-on's own extracted folder.  This module lives
#: directly in the add-on root, so this is exactly the required resolution.
ADDON_ROOT = os.path.dirname(os.path.realpath(__file__))

#: Name of the asset-library entry registered in Blender's Preferences.
ASSET_LIBRARY_NAME = "DragonGraph's Toolset Pack"

#: Sub-folder of the add-on root that is handed to Blender as the asset
#: library.  Every ``.blend`` the Asset Browser is meant to see lives here (or
#: in one of its sub-folders).
PACK_DIR_NAME = "assets"
PACK_DIR = os.path.join(ADDON_ROOT, PACK_DIR_NAME)

#: Sub-folder holding the shipped library ``.blend`` files.  Kept separate from
#: ``assets/`` so that re-downloading the pack cannot clobber the originals.
SHIPPED_DIR_NAME = "library"
SHIPPED_DIR = os.path.join(ADDON_ROOT, SHIPPED_DIR_NAME)

#: Sub-folder of ``assets/`` that a manually loaded pack is unpacked into.
#: Kept separate from the ``assets/`` root so the Asset Browser does not pick up
#: loose archive members, and so re-loading the same pack replaces one folder
#: rather than merging into a folder of unrelated files.
EXTRACTED_DIR_NAME = "extracted"
EXTRACTED_DIR = os.path.join(PACK_DIR, EXTRACTED_DIR_NAME)

#: The only archive type "Manually load" accepts.  Blender add-ons and asset
#: packs are distributed as zips, so anything else is a mistake rather than a
#: format this loader knows how to handle.
ALLOWED_PACK_ARCHIVE = ".zip"

# ---------------------------------------------------------------------------
# Icons
#
# Verified against the Blender 5.2 ``icon_items`` enum.  Blender has no
# ``DOCS`` and no ``GITHUB`` identifier, so the closest real icons are used.
# ---------------------------------------------------------------------------

ICON_CHECK_UPDATES = "FILE_REFRESH"
ICON_RELOAD = "FILE_REFRESH"
ICON_LOAD = "IMPORT"
ICON_UNLOAD = "CANCEL"
ICON_DOCS = "HELP"
ICON_BUG = "URL"
ICON_REDOWNLOAD = "FILE_REFRESH"
ICON_MANUAL_LOAD = "PACKAGE"
ICON_OPEN_EXTRACTED = "FILE_FOLDER"
ICON_UNINSTALL = "TRASH"
ICON_INFO = "INFO"
ICON_ERROR = "ERROR"