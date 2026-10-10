# Library folder

The original `.blend` files that ship with the Toolset Pack belong here.

This folder is kept separate from `../assets` on purpose. `../assets` is what
the Asset Browser reads and what "Redownload" would overwrite; this folder is
treated as read-only source material, so a failed or partial download cannot
destroy the originals.

The loader scans both this folder and `../assets` for `.blend` files, so a
node pack placed in either location is picked up. Files found here are
appended to your open file on load, which is what makes the pack's nodes show
up in the Add > Node menu.

Nothing here is required. If this folder is empty, that is a valid
installation: use "Redownload DragonGraph's Toolset Pack" to fetch the pack, or
"Manually load DragonGraph's Toolset Pack" to unpack a `.zip` you can pick from
anywhere on disk (it is unpacked into `../assets/extracted/`, never here).
