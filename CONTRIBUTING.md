# Contributing to DragonGraph's Toolset Pack

Thank you for contributing. This document covers the requirements for each type of
contribution, and the workflow for getting your work merged.

New here? Check [FAQ.md](FAQ.md) first &mdash; it answers the questions that come up most often.

- [Requirements](#requirements)
  - [What you can contribute](#what-you-can-contribute)
  - [Blend file contributions](#blend-file-contributions)
  - [Add-on contributions](#add-on-contributions)
  - [Icon contributions](#icon-contributions)
  - [Documentation contributions](#documentation-contributions)
- [How to contribute](#how-to-contribute)
  - [Repository scripts](#repository-scripts)
- [Security checks](#security-checks)
  - [Local pre-push gate](#local-pre-push-gate)
  - [In CI](#in-ci)
- [Merge process](#merge-process)
- [Repository layout](#repository-layout)

## Requirements

Develop against **Blender 5.2 LTS** unless a section below says otherwise.

### What you can contribute

The pack is not limited to Geometry Nodes. Every node type below is welcome, and none of them need
to be a single `.blend` file &mdash; keep each type in its own file so a large Shading or
Compositing library never has to share a file with a Geometry Nodes pack.

| Node type | Blender node system | Where it must live |
| --------- | ------------------- | ------------------- |
| **Geometry Nodes** | Geometry Nodes | Asset catalog `🐲 DragonGraph's Node Pack`, prefix `DGraph:` |
| **Shading Nodes** | Shader Editor | Its own asset catalog &mdash; see below |
| **Compositing Nodes** | Compositor Editor | Its own asset catalog &mdash; see below |
| **Simulation Nodes** | Geometry Nodes (simulation sub-discipline) | Asset catalog `🐲 DragonGraph's Node Pack`, prefix `DGraph:` |
| **Modifier groups** | Geometry Nodes modifiers | Asset catalog `🐲 DragonGraph's Node Pack`, prefix `DGraph:` |

`🐲 DragonGraph's Node Pack` is a **Geometry Nodes** asset library, so Shading and Compositing
groups must not be dropped into it &mdash; Blender cannot append a Shader or Compositor group from a
Geometry Nodes asset library into the right editor. Put them in a **new asset catalog of your own**,
named so the type is obvious, and say so in your pull request or issue. The maintainer merges them
and assigns the final catalog and prefix.

> [!NOTE]
> The prefix for Shading and Compositing contributions is not settled yet. Do not assume one; ship
> with a sensible prefix for your own library and describe it in your submission.

Simulation Nodes are Geometry Nodes under the hood, so they follow the Geometry Nodes rules above.

### Blend file contributions

- Authored in **Blender 5.2 LTS**.
- Create a **new** `.blend` file and place it in the `DragonGraph's Project` folder. Do not edit
  the main pack file directly.
- Follow the node-type rules in [What you can contribute](#what-you-can-contribute) &mdash; in
  particular, keep Geometry Nodes, Shading Nodes and Compositing Nodes in separate files.
- The file must stay under **100 MB**. Git LFS is not enabled for this project, and oversized
  files are rejected. If your work does not fit, split it into several `.blend` files instead.
- Mark a node group under `⚠️ Beta Nodes` in your catalog while it is still being tested, so it can
  be merged early and iterated on.
- **Never embed Python scripts in a `.blend` file.** This is a hard rule and it applies to every
  node type, not only Geometry Nodes &mdash; see
  [Can I embed Python scripts inside a .blend file?](FAQ.md#can-i-embed-python-scripts-inside-a-blend-file).
  Python is fine inside the add-on directory.

### Add-on contributions

- Authored in **Blender 5.2 LTS**.
- Must remain interoperable with **Blender 5.2 LTS** (the minimum supported version).
- Support for non-LTS Blender versions is not required until the next LTS release.
- Requires **Python 3.13 or higher**.

### Icon contributions

- You will need drawing software. Affinity Designer or Adobe Illustrator are both recommended.
- Art style should be **simple, clean, and consistent** with the existing icons in the project.
- Icons are merged into the main pack `.blend` file as soon as possible, so keep the source
  artwork around &mdash; SVG or AI files are preferred over flattened PNGs.

### Documentation contributions

- Install the documentation toolchain with
  [`python_library_autosetup.py`](DragonGraph's%20Project%20Utilities/python_library_autosetup.py),
  then preview with
  [`.docsbuild.bat`](DragonGraph's%20Project%20Utilities/.docsbuild.bat), which serves
  <http://127.0.0.1:8000> and reloads on save. Both are documented in the
  [Utilities guide](DragonGraph's%20Project%20Utilities/README.md#preview-the-documentation-live).
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

Maintainer tooling lives in [`DragonGraph's Project Utilities/`](DragonGraph's%20Project%20Utilities/).
The [Utilities guide](DragonGraph's%20Project%20Utilities/README.md) is the single reference for
every tool, the `.env` settings they share, and how to build a pack or preview the documentation.

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
`Build and deploy` only when that scan passes. There is no bypass in the workflow itself.
[`.github/BRANCH_PROTECTION.md`](.github/BRANCH_PROTECTION.md) has the one-time repository setup
that makes this a hard gate, including the bot bypass entry the nightly job needs to push its zip.

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
