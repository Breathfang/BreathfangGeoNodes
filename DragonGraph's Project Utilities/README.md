# DragonGraph's Project Utilities

Development toolbox for the Dragongraph's Toolset Pack repository. Everything here is for
**maintainers and contributors working on the repository** &mdash; none of it ships inside the
released or nightly `.zip` files (this folder is explicitly excluded from the pack builds and
from the GitHub Actions trigger).

All Python tools require **Python 3.13 or higher**. The two `.bat` files are Windows only.

| Tool | Purpose |
| ---- | ------- |
| [`python_library_autosetup.py`](python_library_autosetup.py) | Installs the documentation toolchain (`sphinx`, `sphinx-autobuild`, `sphinx_rtd_theme`) into your current interpreter. |
| [`.docsbuild.bat`](.docsbuild.bat) | Builds the documentation and serves it at <http://127.0.0.1:8000> with live reload. Windows only. |
| [`language_server_taskkill_blender_save.bat`](language_server_taskkill_blender_save.bat) | Kills the Blender language server process (`language_server_windows_x64.exe`) so `.blend` save prompts stop hanging. Windows only. |
| [`nodepack_zip_generator.py`](nodepack_zip_generator.py) | Packages `DragonGraph's Project/` into a release `.zip` under `Generated Nodepacks/`, or a nightly snapshot under `DragonGraph's Nighty Build/` (`--nightly`). Runs interactively or via `--` options. |
| [`temporary_file_cleaner.py`](temporary_file_cleaner.py) | Interactive CLI that finds temporary files inside the repository, lists them a page at a time (10 each), shows a preview, then deletes them on explicit confirmation. |

## Install the documentation toolchain

```text
python python_library_autosetup.py
```

Prompts before installing anything; pass `--yes` to install immediately (no prompt, for CI
use) and `--no-pause` to skip the "press enter to exit" wait. Checks your Python version first
(3.13+) and logs to `python_library_autosetup.log` in your working directory.

## Preview the documentation live

```text
.docsbuild.bat              start on port 8000 with a clean build
.docsbuild.bat 8080         start on port 8080
.docsbuild.bat --no-clean   keep the existing docs/_build output
```

It opens <http://127.0.0.1:8000> automatically and reloads when files under `docs/` change.
While it runs, press `R` to rebuild, `B` to open the browser, `L` to show the build log,
`C` for a clean rebuild, `Q` to stop. Build output is logged to `.docsbuild.log` and
`.docsbuild-sphinx.log` at the repository root. Requires `sphinx` + `sphinx-autobuild`
(installed by [`python_library_autosetup.py`](python_library_autosetup.py)).

## Unstick a hanging Blender save prompt

If Blender's autosave/language server keeps the editor from finishing a save, run:

```text
language_server_taskkill_blender_save.bat
```

This force-kills `language_server_windows_x64.exe`. It only touches that one process.

## Build a pack .zip

Run with no options to get the interactive wizard:

```text
python nodepack_zip_generator.py
```

Choose `1` (release), `2` (nightly snapshot), or `3` (quit). For a release you are asked for
the node version (suggested from the first `.blend` filename) and the output directory
(default `Generated Nodepacks\`).

The same build can be driven non-interactively with options (how CI calls it):

```text
python nodepack_zip_generator.py --nightly
python nodepack_zip_generator.py --node-version v1.3.0-beta --output-dir Generated Nodepacks
```

- `--nightly` &mdash; snapshot named `Dragongraph's Toolset Pack NightlyBuilds_<short-sha>_<timestamp>.zip`.
- `--node-version` &mdash; version string for releases; parsed from the first `.blend` if omitted.
- `--output-dir` &mdash; override where the zip goes; relative paths resolve under the repo root.
- `--no-pause` &mdash; don't wait for a keypress on exit.

**What goes inside:** the full contents of `DragonGraph's Project/`, with that folder as the
archive root (original names, original subpaths, every file type). Only these suffixes are
excluded: `.md`, `.log`, `.tmp`, `~`, `.orig`, `.rej`, and Blender autosaves `.blend1`-`.blend9`.

## Clean temporary files

```text
python temporary_file_cleaner.py
```

Interactive flow: it scans the repository, shows every match a page at a time (10 entries per
page), then shows a final preview and asks `delete N file(s) [y/N]`. Only a `y` deletes
anything. Add `--dry-run` to list and preview without deleting:

```text
python temporary_file_cleaner.py --dry-run
```

Cleans the same suffixes excluded from the packs: `.log`, `.tmp`, `~` (editor backups like
`blender_assets.cats.txt~`), `.orig`, `.rej`, and `.blend1`-`.blend9`.

**Safety:** the search is rooted at the repository root (one level up from this folder) and can
never step above it. `.git/` entries and symlinks are skipped, and every file is re-checked to
be inside the repository the moment before it is deleted.

## Repository anchors

Each tool derives the repository root from its own location, so they work no matter where you
invoke them from. Anything outside the repository &mdash; including the `SFW Projects` parent
folder &mdash; is out of reach by design.