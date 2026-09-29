# DragonGraph's Project Utilities

Development toolbox for the Dragongraph's Toolset Pack repository. Everything here is for
**maintainers and contributors working on the repository** &mdash; none of it ships inside the
released or nightly `.zip` files (this folder is explicitly excluded from the pack builds and
from the GitHub Actions trigger).

All Python tools require **Python 3.13 or higher**. The two `.bat` files are Windows only.

## Settings (`.env`)

Both tooling folders keep **exactly one** `.env`, sitting next to the scripts that read it:

```text
DragonGraph's Project Utilities/
  .env                 <- read by the three .py tools below
  functions/           <- shared Python modules only, no .env
.github/scripts/
  .env                 <- read by the four CI .py scripts
  functions/           <- shared Python modules only, no .env
```

There is deliberately **no** `.env` inside `functions/` and none per script. The two `.bat` files
(`.docsbuild.bat`, `language_server_taskkill_blender_save.bat`) do not read `.env` at all; they keep
their own settings block at the top of the file.

**Both `.env` files are committed** and are the single source of truth for the settings below. That
is on purpose: `NIGHTLY_BUILDS_ENABLED` has to reach CI through a diff, so a private untracked copy
would let a maintainer believe they had flipped the pipeline when they had not. Edit the file, commit
it, and everyone &mdash; including CI &mdash; gets the change. Keep nothing secret in it; the only
personal value anyone should need is a local `BLENDER_BINARY` path, which a real environment variable
can override without touching the file.

Every setting still falls back to a built-in default when the key is absent, so a missing or
truncated `.env` degrades to the previous hard-coded behaviour instead of crashing. A real
environment variable always beats a value in the file, so you can override one setting for a single
run without editing anything:

```text
set NIGHTLY_BUILDS_ENABLED=true     (Windows)
NIGHTLY_BUILDS_ENABLED=true         (bash)
```

Inspect what a script actually resolved:

```text
python nodepack_zip_generator.py --show-settings
python temporary_file_cleaner.py --list
python .github/scripts/nightly_builder.py --show-settings
```

| Key | Default | Used by |
| ---- | ------- | ------- |
| `REPO_ROOT` | *(auto-detect `.git`)* | all scripts |
| `SOURCE_DIR` | `DragonGraph's Project` | zip generator, nightly builder, scanners |
| `RELEASE_OUTPUT_DIR` | `Generated Nodepacks` | zip generator |
| `NIGHTLY_OUTPUT_DIR` | `DragonGraph's Nighty Build` | zip generator, nightly builder, cleaner |
| `LOG_MAX_BYTES` / `LOG_BACKUP_COUNT` | `1000000` / `5` | zip generator, autosetup |
| `PAUSE_PROMPT` | `Press enter to exit...` | the interactive tools |
| `ZIP_COMPRESSION_LEVEL` | `9` | zip generator, nightly builder |
| `ZIP_EXCLUDED_SUFFIXES` | `.md,.log,.tmp,~,.orig,.rej,.blend1-9` | zip generator, nightly builder |
| `CLEANER_PAGE_SIZE` | `10` | temporary file cleaner |
| `CLEANER_SUFFIXES` | `.log,.tmp,~,.orig,.rej,.blend1-9` | temporary file cleaner |
| `MIN_PYTHON` | `3.13` | library autosetup |
| `DOCS_PACKAGES` | `sphinx,sphinx-autobuild,sphinx_rtd_theme` | library autosetup |

`.github/scripts/.env` additionally holds `NIGHTLY_BUILDS_ENABLED` (the master pipeline toggle) and
the scanner policy &mdash; `PY_SCAN_ROOTS`, `SCAN_SKIP_DIRS`, `PY_DENIED_MODULES`,
`PY_DENIED_CALLS`, `PY_DENIED_ATTR_SUFFIX`, `PY_DENIED_CALLABLE_ATTRS`, plus the `.blend` limits.
See its own header comments.

**Pausing nightly builds:** `NIGHTLY_BUILDS_ENABLED=false` stops CI from building, pushing *and*
deleting archives. Local and manual runs are unaffected. To resume, set it to `true` in
`.github/scripts/.env` and commit; the workflow reads the committed value through
`nightly_builder.BUILDS_ENABLED`.

Note that the workflow's `on.push.paths` filter only matches `DragonGraph's Project/**`, so that
commit *arms* the pipeline without running it. The first push that also touches
`DragonGraph's Project/` is what produces a nightly build.

| Tool | Purpose |
| ---- | ------- |
| [`python_library_autosetup.py`](python_library_autosetup.py) | Installs the documentation toolchain (`sphinx`, `sphinx-autobuild`, `sphinx_rtd_theme`) into your current interpreter. |
| [`.docsbuild.bat`](.docsbuild.bat) | Builds the documentation and serves it at <http://127.0.0.1:8000> with live reload. Windows only. |
| [`language_server_taskkill_blender_save.bat`](language_server_taskkill_blender_save.bat) | Kills the Blender language server process (`language_server_windows_x64.exe`) so `.blend` save prompts stop hanging. Windows only. |
| [`nodepack_zip_generator.py`](nodepack_zip_generator.py) | Packages `DragonGraph's Project/` into a release `.zip` under `Generated Nodepacks/`, or a nightly snapshot under `DragonGraph's Nighty Build/` (`--nightly`). Runs interactively or via `--` options. |
| [`temporary_file_cleaner.py`](temporary_file_cleaner.py) | Interactive CLI that finds temporary files inside the repository, lists them a page at a time (10 each), shows a preview, then deletes them on explicit confirmation. |
| [`functions/`](functions) | Shared Python modules the three tools above import. Code only, no `.env`. |

## Install the documentation toolchain

```text
python python_library_autosetup.py
```

Prompts before installing anything; pass `--yes` to install immediately (no prompt, for CI
use) and `--no-pause` to skip the "press enter to exit" wait. Checks your Python version first
(3.13+) and logs to `python_library_autosetup.log` at the repository root. The version floor and
the package list come from `MIN_PYTHON` and `DOCS_PACKAGES` in `.env`.

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
page, `CLEANER_PAGE_SIZE` in `.env`), then shows a final preview and asks `delete N file(s) [y/N]`.
Only a `y` deletes anything. Add `--dry-run` to list and preview without deleting:

```text
python temporary_file_cleaner.py --dry-run
```

Cleans the same suffixes excluded from the packs: `.log`, `.tmp`, `~` (editor backups like
`blender_assets.cats.txt~`), `.orig`, `.rej`, and `.blend1`-`.blend9`.

**Safety:** the search is rooted at the repository root (discovered from this folder's location) and
can never step above it. `.git/` entries and symlinks are skipped, and every file is re-checked to
be inside the repository the moment before it is deleted.

## Repository anchors

Each tool derives the repository root from its own location, so they work no matter where you
invoke them from &mdash; and relative `--output-dir` / `--root` values are resolved against that
root, not against your working directory. Anything outside the repository &mdash; including the
`SFW Projects` parent folder &mdash; is out of reach by design. Set `REPO_ROOT` in `.env` to pin it.

## Shared modules

`functions/` holds the Python helpers the scripts import &mdash; `env_utils` (the `.env` reader),
`path_utils` (repository anchoring), `log_utils` (rotating logger, size formatting) and
`prompt_utils` (console prompts) here, plus `ci_utils` (pipeline toggle) and `scan_utils` (git and
file walking) in `.github/scripts/functions/`. Code only, no configuration, and no logic specific to
one script. The `.env` beside them is the only configuration file either package reads.