# FAQ

Answers to the questions that come up most often about DragonGraph's Toolset Pack.

For installation and update steps, see the
[documentation](https://breathfanggeonodes.readthedocs.io/en/latest/). For contribution
requirements, see [CONTRIBUTING.md](CONTRIBUTING.md).

- [Using the pack](#using-the-pack)
  - [Can I use the pack commercially?](#can-i-use-the-pack-commercially)
  - [Can I create Shader Nodes and Compositing Nodes?](#can-i-create-shader-nodes-and-compositing-nodes)
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
  - [What are the nightly builds?](#what-are-the-nightly-builds)

## Using the pack

### Can I use the pack commercially?

Yes. The pack is released under the GPL-3 License, so commercial use is allowed.

### Can I create Shader Nodes and Compositing Nodes?

**Yes.** The pack is not limited to Geometry Nodes. Shading Nodes, Compositing Nodes, Simulation
Nodes and Geometry Nodes modifiers are all welcome, and the full per-type rules are in
[What you can contribute](CONTRIBUTING.md#what-you-can-contribute).

The one thing to get right is **where they go**. The existing `🐲 DragonGraph's Node Pack` catalog
is a **Geometry Nodes** asset library, and Blender cannot append a Shader or Compositor group out of
a Geometry Nodes asset library into the correct editor. So:

- **Geometry Nodes, Simulation Nodes and modifier groups** go in
  `🐲 DragonGraph's Node Pack` with the `DGraph:` prefix.
- **Shading and Compositing Nodes** go in a **new asset catalog of your own**, with a name that
  makes the node type obvious, and you say so in your pull request or issue. The maintainer merges
  them and assigns the final catalog name and prefix.

Keep each node type in its own `.blend` file so a large Shading library never has to share a file
with the Geometry Nodes pack, and keep every file under **100 MB**.

> [!NOTE]
> The prefix for Shading and Compositing contributions has not been settled yet. Pick something
> sensible for your own library and describe it in your submission rather than guessing at one.

### Why isn't my node merged after an update?

The usual reasons:

- Your node isn't ready yet.
- Your node doesn't meet the quality bar.
- Your node is buggy or unsafe.
- Your node contains Python scripts.
- Your pull request or issue hasn't been approved yet.

## Contributing

### How do I contribute?

Either open a pull request with a new `.blend` file, or open an issue and attach it. Do not edit the
main pack file &mdash; it gets merged manually. The full steps and requirements are in
[CONTRIBUTING.md](CONTRIBUTING.md#how-to-contribute).

### How long does merging take?

There is no guaranteed turnaround time. Your `.blend` file gets merged as soon as it is
considered ready and acceptable, and you are notified when it lands. The steps are listed in
[CONTRIBUTING.md](CONTRIBUTING.md#merge-process).

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

Run [`.docsbuild.bat`](DragonGraph's%20Project%20Utilities/.docsbuild.bat), which builds the
documentation, serves it at <http://127.0.0.1:8000> and reloads when files under `docs/` change.
Install the toolchain first with
[`python_library_autosetup.py`](DragonGraph's%20Project%20Utilities/python_library_autosetup.py).
See [Preview the documentation live](DragonGraph's%20Project%20Utilities/README.md#preview-the-documentation-live).

### How do I generate the release .zip?

Run
[`nodepack_zip_generator.py`](DragonGraph's%20Project%20Utilities/nodepack_zip_generator.py)
and enter the version, for example `v1.1.0-alpha`. The interactive wizard, the non-interactive
options, and the exact list of excluded file types are documented in
[Build a pack .zip](DragonGraph's%20Project%20Utilities/README.md#build-a-pack-zip).

### What are the nightly builds?

Nightly snapshots are built automatically by GitHub Actions on every push to `main`, packaged by
`.github/scripts/nightly_builder.py`. They are named
`DragonGraph's Toolset Pack NightlyBuilds_<short-sha>_<timestamp>.zip` and committed under
`DragonGraph's Nighty Build/` while an identical copy is kept as a GitHub Actions artifact
(7-day retention). To build one locally run:

```text
python .github/scripts/nightly_builder.py
```

Pausing or resuming them is controlled by one committed setting &mdash; see
[Pausing nightly builds](DragonGraph's%20Project%20Utilities/README.md#pausing-nightly-builds).
