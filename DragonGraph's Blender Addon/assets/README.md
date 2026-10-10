# Assets folder

This is the folder registered with Blender as the asset library
**DragonGraph's Toolset Pack**. Every `.blend` file placed here (or in a
sub-folder) is what the Asset Browser will show.

## Putting your own nodes here

Save a `.blend` file with your Geometry Nodes groups in it:

- Mark the groups you want to browse as **Assets** (right-click the node group
  in the Node Editor, or use the Asset Browser's "Mark as Asset").
- **File > External Data > Pack Resources** if the group depends on images or
  other external files, otherwise the Asset Browser cannot find them.
- Save that `.blend` into this folder.

Do not put a node pack in here that you also use as a working file. The loader
appends node groups from these files, and "Reload from Asset Library" will
purge and re-append them, so a file that is also your open working document
will lose its node groups on reload.

## How the loader treats this folder

- Only this folder (and the sibling `library/` folder) is ever read. Every
  path is checked against the add-on's own directory before Blender is asked
  to open it, so the add-on cannot be pointed at anything outside itself.
- **Manually load DragonGraph's Toolset Pack** unpacks a `.zip` into
  `extracted/` here, then loads the `.blend` libraries it contains. The pack's
  own file names are used as-is, so its library sits directly in `extracted/`
  rather than in a folder named after the archive. You can pick that `.zip` from
  anywhere - your Downloads folder, a USB stick, or this folder - there is no
  need to move it in first. Re-loading empties `extracted/` before unpacking, so
  an upgrade does not leave stale files behind. Where it unpacks to is always
  `assets/extracted/` regardless of where the archive came from, and entries
  that try to point outside that folder are rejected.
- If the pack ships a `blender_assets.cats.txt`, it is merged into this
  folder's copy rather than left in `extracted/`, because Blender only reads
  the catalog file from the root of an asset library. Your own catalogs are
  kept, and a pack's catalogs replace only their own entries, so re-loading an
  updated pack updates its catalogs in place.
- **Unload from Asset Library (untick)** only unticks this folder's entry in
  Preferences &gt; File Paths &gt; Asset Libraries. It deletes nothing: the entry
  keeps its path and import method and is just hidden from the Asset Browser, so
  loading again is a single re-tick and a mis-click costs you nothing. Your node
  groups in the open file are left alone too.
- Groups brought in from here are tagged with a custom property naming their
  source file, and given a fake user so they stay available in the Add menu.
  Your own node groups are never touched by "Unload", "Uninstall" or "Reload".
- **"Uninstall DragonGraph's Toolset Pack"** is the separate, deliberate step:
  it deletes the asset library entry outright and frees the pack's node groups
  from memory. It asks for confirmation first. It does **not** delete any file in
  this folder, and it is the only action that removes the entry.

## "N duplicate(s)" in the console

Blender registers every asset once per asset library that can see it, keyed by
library. So if the same `.blend` is reachable from two different asset libraries,
every asset in it is registered twice and the console fills with one
`Error registering node tool ... N duplicate(s)` line per asset.

The usual cause is a second library that *contains* this pack. Asset libraries
are scanned recursively, so a library pointing at a project folder picks up a
pack `.blend` nested anywhere under it - and if that folder also holds a copy of
the pack, you get the same assets registered twice. The two files do not even
have to be at the same path; identical contents are enough.

The loader checks for this when the add-on is enabled and names the library
responsible, plus a **Fix Duplicate Asset Libraries** button in the Maintenance
card. The fix unticks the offending library - it does not delete it, so it can be
re-ticked in Preferences &gt; File Paths &gt; Asset Libraries afterwards. An
unticked library is not scanned, so it cannot register anything.

The other half of the fix is on your side: only one library should be able to
reach a given pack. If you want a library that browses your project work, point
it at a folder that does not also contain the shipped pack.
