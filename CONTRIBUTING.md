# Contributing to DragonGraph's Toolset Pack

Thank you for contributing. This document covers the requirements for each type of
contribution, and the workflow for getting your work merged.

New here? Check [FAQ.md](FAQ.md) first &mdash; it answers the questions that come up most often.

- [Requirements](#requirements)
  - [Blend file contributions](#blend-file-contributions)
  - [Add-on contributions](#add-on-contributions)
  - [Icon contributions](#icon-contributions)
  - [Documentation contributions](#documentation-contributions)
- [How to contribute](#how-to-contribute)
- [Merge process](#merge-process)
- [Repository layout](#repository-layout)

## Requirements

Develop against **Blender 5.2 LTS** unless a section below says otherwise.

### Blend file contributions

- Authored in **Blender 5.2 LTS**.
- Create a **new** `.blend` file and place it in the `DragonGraph's Project` folder. Do not edit
  the main pack file directly.
- Geometry Nodes and Shading Nodes are both welcome.
- The file must stay under **100 MB**. Git LFS is not enabled for this project, and oversized
  files are rejected. If your work does not fit, split it into several `.blend` files instead.
- **Never embed Python scripts in a `.blend` file.** This is a hard rule &mdash; see
  [Can I embed Python scripts inside a .blend file?](FAQ.md#can-i-embed-python-scripts-inside-a-blend-file).
  Python is fine inside the add-on directory.

### Add-on contributions

- Authored in **Blender 5.2 LTS**.
- Must remain interoperable with **Blender 5.2 LTS** (the minimum supported version).
- Support for non-LTS Blender versions is not required until the next LTS release.
- Requires **Python 3.13 or higher**. Run
  [`python_library_autosetup.py`](DragonGraph's%20Project%20Utilities/python_library_autosetup.py)
  to install the required packages
  into your current interpreter.

### Icon contributions

- You will need drawing software. Affinity Designer or Adobe Illustrator are both recommended.
- Art style should be **simple, clean, and consistent** with the existing icons in the project.
- Icons are merged into the main pack `.blend` file as soon as possible, so keep the source
  artwork around &mdash; SVG or AI files are preferred over flattened PNGs.

### Documentation contributions

- Run
  [`python_library_autosetup.py`](DragonGraph's%20Project%20Utilities/python_library_autosetup.py)
  to install the required
  packages: `sphinx`, `sphinx-autobuild`, and `sphinx_rtd_theme`.
- Run [`.docsbuild.bat`](DragonGraph's%20Project%20Utilities/.docsbuild.bat) to build the documentation and preview it at
  <http://127.0.0.1:8000>. `sphinx-autobuild` reloads automatically when you save, delete, or add
  a file inside `docs/`.
- Documentation **should be ready and complete before v3.0.0-stable**.

## How to contribute

Two options, both welcome:

1. **Open a pull request** with a new `.blend` file or script change. Do not edit the main pack
   file &mdash; it gets merged manually.
2. **Open an issue** and attach your created or updated `.blend` file.

Suggestions, recommendations, and questions are welcome too, even if you are not contributing
code. If you are unsure what to contribute, just
[open an issue](https://github.com/Breathfang/BreathfangGeoNodes/issues/) and ask.

### Repository scripts

| Script | Purpose |
| ------ | ------- |
| [`python_library_autosetup.py`](DragonGraph's%20Project%20Utilities/python_library_autosetup.py) | Installs the documentation toolchain. |
| [`.docsbuild.bat`](DragonGraph's%20Project%20Utilities/.docsbuild.bat) | Builds and serves the documentation with live reload. |
| [`nodepack_zip_generator.py`](DragonGraph's%20Project%20Utilities/nodepack_zip_generator.py) | Packages the current pack into a release `.zip` in `Generated Nodepacks/`, or a nightly snapshot in `DragonGraph's Nighty Build/` with `--nightly`. |

Full usage notes for every tool (including `temporary_file_cleaner.py` and the two `.bat`
helpers) live in the
[Utilities guide](DragonGraph's%20Project%20Utilities/README.md).

## Security checks

Two scanners guard everything under `DragonGraph's Project/`, the only code that can end up inside
a shipped pack:

| Script | Checks for |
| ------ | ---------- |
| [`python_security_scanner.py`](.github/scripts/python_security_scanner.py) | Dangerous Python: `os`/`subprocess`/`socket` imports, `eval`/`exec`, `.system()`-style calls, and obfuscated patterns. AST plus a tokenizer pass. |
| [`blend_scanner.py`](.github/scripts/blend_scanner.py) | Python embedded in a `.blend` file, which would run on anyone who opens the pack. |

Both exit `1` only for a confirmed violation. A file that is corrupt, truncated or unparseable is
reported as `[WARNING]` and skipped, so one broken `.blend` will not block an unrelated pull
request. `zstandard` is a required dependency for the `.blend` scanner &mdash; the files here are
Zstandard frames &mdash; so install it once with:

```bash
python -m pip install -r .github/scripts/requirements.txt
```

### Local pre-push gate

Install the hook once per clone so a violation is caught before you push rather than in a failed
check afterwards:

```bash
python .github/scripts/install_hooks.py
```

It runs both scanners and aborts the push on a confirmed violation. For a genuine emergency,
`SKIP_SECURITY_HOOK=1 git push` skips it &mdash; the hook says so loudly, and CI still scans the
resulting pull request.

### In CI

The `Nightly` workflow runs `Security scan` on every pull request and every push to `main`, and
`Build and deploy` runs only when that scan passes. There is no bypass. `main` is expected to
require the `Security scan` status check before merging; see
[`.github/BRANCH_PROTECTION.md`](.github/BRANCH_PROTECTION.md) for the one-time setup, including
the bot entry the bypass list needs so the nightly job can still push its zip.

## Merge process

1. You submit a pull request or an issue with your file attached.
2. The `Security scan` check runs automatically. It must pass before a merge is possible.
3. It gets reviewed. If it is not ready yet, you will be notified.
4. Once it is considered ready, it gets polished and merged into the main pack file.
5. You get a notification when it lands in an update.

There is no guaranteed turnaround time. Merging happens as soon as a contribution is considered
ready and acceptable. If your work is not merged after an update, the usual reasons are listed
in [Why isn't my node merged yet?](FAQ.md#why-isnt-my-node-merged-after-an-update).

## Repository layout

| Path | Contents |
| ---- | -------- |
| `DragonGraph's Project/` | Source `.blend` files and the readme. This is where new `.blend` contributions go. |
| `blend_addon_src/` | Add-on source. Not tracked by Git. |
| `docs/` | Sphinx documentation sources. |
| `Generated Nodepacks/` | Release `.zip` output. Not tracked by Git. |
| `Icon and Logo Designs/` | Icon and logo source artwork. |
| `.github/scripts/` | CI scripts and the shared `functions/` helpers. |
| `.github/hooks/pre-push` | Tracked source of the local pre-push gate, installed by `.github/scripts/install_hooks.py`. |
| `.github/workflows/nightly.yml` | `Security scan`, then `Build and deploy`. |
