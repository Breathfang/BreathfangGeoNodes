# Contents

## Documentation (wiki)

The node reference is hosted, not kept in this repository:

**https://breathfanggeonodes.readthedocs.io/en/latest/**

Everything about individual node groups &mdash; inputs, outputs, examples and images &mdash; lives on
that site. This file deliberately does not reproduce any of it, and the Sphinx sources under
[`docs/`](docs/) are not indexed here. Use the hosted wiki as the single reference.

## `DragonGraph's Project/`

The folder that gets built into a release. This is the part of the repository worth indexing
file by file.

| File | Purpose |
| ---- | ------- |
| [`DragonGraph's Toolset Pack v1.3.0-beta.blend`](DragonGraph's%20Project/DragonGraph's%20Toolset%20Pack%20v1.3.0-beta.blend) | The pack itself. Ships as-is in the release `.zip`. |
| [`blender_assets.cats.txt`](DragonGraph's%20Project/blender_assets.cats.txt) | Asset catalog definition Blender reads on install. Defines `🐲 DragonGraph's Node Pack` and its subcatalogs, including `⚠️ Beta Nodes` and `ℹ️ Internal Nodes`. |
| [`Read Before Use Nodes.txt`](DragonGraph's%20Project/Read%20Before%20Use%20Nodes.txt) | Install, update, reinstall and uninstall steps that ship inside the pack. |

> [!NOTE]
> `🐲 DragonGraph's Node Pack` is a **Geometry Nodes** asset library, which is why Shading and
> Compositing contributions are asked to bring their own catalog rather than join this one. See
> [Can I create Shader Nodes and Compositing Nodes?](FAQ.md#can-i-create-shader-nodes-and-compositing-nodes).

### `DragonGraph's Project/Collabs/`

| File | Purpose |
| ---- | ------- |
| [`Collabs.md`](DragonGraph's%20Project/Collabs/Collabs.md) | Maintainer list, how to be added, and related links. |
| [`testing.txt`](DragonGraph's%20Project/Collabs/testing.txt) | Scratch file, currently empty. |

### Not indexed

Written automatically by Blender or your editor rather than maintained by hand:

| Pattern | What it is |
| ------- | ---------- |
| `*.blend[0-9]` | Blender auto-backups |
| `*.txt~` | Editor backup of a text file |
| `*.blend.old` | Previous pack, kept after a manual update |
