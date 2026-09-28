# FAQ

Answers to the questions that come up most often about DragonGraph's Toolset Pack.

For installation and update steps, see the
[documentation](https://breathfanggeonodes.readthedocs.io/en/latest/). For contribution
requirements, see [CONTRIBUTING.md](CONTRIBUTING.md).

- [Using the pack](#using-the-pack)
  - [Can I use the pack commercially?](#can-i-use-the-pack-commercially)
  - [Can I contribute non-geometry nodes (shading, compositor, etc.)?](#can-i-contribute-non-geometry-nodes-shading-compositor-etc)
  - [Why isn't my node merged after an update?](#why-isnt-my-node-merged-after-an-update)
- [Contributing](#contributing)
  - [How do I contribute?](#how-do-i-contribute)
  - [How long does merging take?](#how-long-does-merging-take)
  - [Can I embed Python scripts inside a .blend file?](#can-i-embed-python-scripts-inside-a-blend-file)
  - [Can I remake a node from another node pack?](#can-i-remake-a-node-from-another-node-pack)
  - [Can I contribute using a newer Blender than the base version?](#can-i-contribute-using-a-newer-blender-than-the-base-version)
  - [Why was I banned from contributing?](#why-was-i-banned-from-contributing)
- [Repository scripts](#repository-scripts)
  - [How do I preview the documentation before committing?](#how-do-i-preview-the-documentation-before-committing)
  - [How do I generate the release .zip?](#how-do-i-generate-the-release-zip)

## Using the pack

### Can I use the pack commercially?

Yes. The pack is released under the GPL-3 License, so commercial use is allowed.

### Can I contribute non-geometry nodes (shading, compositor, etc.)?

Yes. Create a new category under Blender Assets for non-geometry nodes &mdash; that keeps them
separated from the Geometry Nodes groups.

### Why isn't my node merged after an update?

The usual reasons:

- Your node isn't ready yet.
- Your node doesn't meet the quality bar.
- Your node is buggy or unsafe.
- Your node contains Python scripts.
- Your pull request or issue hasn't been approved yet.

## Contributing

### How do I contribute?

Two options, both welcome:

1. Create a **new** `.blend` file and put it in the `DragonGraph's Project` folder. Do not edit
   the main pack file &mdash; it gets merged manually.
2. **Open an issue** and attach your created or updated `.blend` file.

If you are unsure what to contribute, open an issue and ask.

### How long does merging take?

There is no guaranteed turnaround time. Your `.blend` file gets merged as soon as it is
considered ready and acceptable, and you are notified when it lands.

### Can I embed Python scripts inside a .blend file?

**No.** This is due to security reasons and to how Blender handles embedded scripts. A `.blend`
file containing an embedded Python script will be rejected, and you will be banned from
contributing.

Python scripts **are** allowed inside the add-on directory &mdash; just never inside a `.blend`
file.

### Can I remake a node from another node pack?

Yes, as long as you meaningfully improve it. Remaking another pack's node and contributing it
here with no significant changes is not allowed.

### Can I contribute using a newer Blender than the base version?

Yes. However, your work will not be merged into the main pack file until the next Blender LTS
release, and it will be merged as soon as possible after that release.

When you do, create a new category under Blender Assets for that Blender version, for example
`Collabs > 5.3`.

### Why was I banned from contributing?

Being banned means the [contribution requirements](CONTRIBUTING.md#requirements) were not
followed. Do not circumvent a ban by creating another account &mdash; appeals go through the
social media channels linked in the
[GitHub repository](https://github.com/Breathfang/BreathfangGeoNodes).

## Repository scripts

The developer tools require **Python 3.13 or higher**; the `.bat` helpers are Windows only.
Full usage notes live in the
[Utilities guide](DragonGraph's%20Project%20Utilities/README.md).

### How do I preview the documentation before committing?

Run [`.docsbuild.bat`](DragonGraph's%20Project%20Utilities/.docsbuild.bat). It builds the
documentation and serves it at
<http://127.0.0.1:8000>, opening your browser automatically.

`[sphinx-autobuild](https://sphinx-autobuild.readthedocs.io/en/latest/)` reloads automatically
when you save, delete, or add a file inside `docs/`.

If the packages are not installed yet, run
[`python_library_autosetup.py`](DragonGraph's%20Project%20Utilities/python_library_autosetup.py)
first.

### How do I generate the release .zip?

Run
[`nodepack_zip_generator.py`](DragonGraph's%20Project%20Utilities/nodepack_zip_generator.py)
and enter the version, for example
`v1.1.0-alpha`. Or pass `--node-version v1.1.0-alpha` to skip the prompt
(required when running non-interactively).

The script packages the contents of `DragonGraph's Project/` with that folder as
the archive root (every file type, original names and paths),
excluding documented files, then writes
`Generated Nodepacks/DragonGraph's Toolset Pack <version> - Asset Library.zip`.

### What are the nightly builds?

Nightly snapshots are built automatically by GitHub Actions whenever anything inside
`DragonGraph's Project/` changes (and daily on a schedule), packaged by
`.github/scripts/nightly_builder.py`. They are named
`Dragongraph's Toolset Pack NightlyBuilds_<short-sha>_<timestamp>.zip` and committed under
`DragonGraph's Nighty Build/` while an identical copy is kept as a GitHub Actions artifact
(7-day retention). To build a nightly snapshot manually run:

```text
python .github/scripts/nightly_builder.py
```
