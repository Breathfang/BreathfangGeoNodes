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
- Must remain interoperable with **Blender 4.5 LTS and 5.2 LTS**.
- Support for non-LTS Blender versions is not required until the next LTS release.
- Requires **Python 3.13 or higher**. Run
  [`_PythonLibraryAutoSetup.py`](_PythonLibraryAutoSetup.py) to install the required packages
  into your current interpreter.

### Icon contributions

- You will need drawing software. Affinity Designer or Adobe Illustrator are both recommended.
- Art style should be **simple, clean, and consistent** with the existing icons in the project.
- Icons are merged into the main pack `.blend` file as soon as possible, so keep the source
  artwork around &mdash; SVG or AI files are preferred over flattened PNGs.

### Documentation contributions

- Run [`_PythonLibraryAutoSetup.py`](_PythonLibraryAutoSetup.py) to install the required
  packages: `sphinx`, `sphinx-autobuild`, and `sphinx_rtd_theme`.
- Run [`.docsbuild.bat`](.docsbuild.bat) to build the documentation and preview it at
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
| [`_PythonLibraryAutoSetup.py`](_PythonLibraryAutoSetup.py) | Installs the documentation toolchain. |
| [`.docsbuild.bat`](.docsbuild.bat) | Builds and serves the documentation with live reload. |
| [`_NodepackZipGenerator.py`](_NodepackZipGenerator.py) | Packages the current pack into a release `.zip` in `Generated Nodepacks/`. |

## Merge process

1. You submit a pull request or an issue with your file attached.
2. It gets reviewed. If it is not ready yet, you will be notified.
3. Once it is considered ready, it gets polished and merged into the main pack file.
4. You get a notification when it lands in an update.

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
