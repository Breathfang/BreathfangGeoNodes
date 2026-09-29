# Issue templates

Templates live in [`.github/ISSUE_TEMPLATE/`](.github/ISSUE_TEMPLATE/) and appear on GitHub's
**New issue** page. There is nothing to copy from here.

| Template | Use it for |
| -------- | ---------- |
| [`bug_report.md`](.github/ISSUE_TEMPLATE/bug_report.md) | A node, the add-on, or an install/update that misbehaves |
| [`docs_fix.md`](.github/ISSUE_TEMPLATE/docs_fix.md) | A typo, broken link or image, or an outdated page |
| [`feature_request.md`](.github/ISSUE_TEMPLATE/feature_request.md) | A new node, an improvement, or new tooling |
| [`node_submission.md`](.github/ISSUE_TEMPLATE/node_submission.md) | Handing over a `.blend` with a new node |

Two notes worth reading once:

- **A broken node has no traceback.** Nodes are data, not code, so Blender shows a warning icon on
  the node header and outputs wrong geometry. A screenshot or short video is the most useful thing
  you can attach. A traceback only applies to the add-on, which is Python.
- **Check your Blender version first.** The base pack needs **5.2 LTS or newer**. On an older LTS,
  `DGraph:` nodes silently vanish when appended, which accounts for a lot of reports. `DGraphExt:`
  nodes from an extension pack are stricter and work only in the version they target, so mention
  which pack a node came from. See
  [Minimum Blender version by pack version](README.md#minimum-blender-version-by-pack-version).

Security problems must not be filed as issues &mdash; a public issue stays public even after it is
closed. Contact a maintainer instead; Breathfang (lead) and TheLycanFenrir are listed in
[Collabs.md](DragonGraph's%20Project/Collabs/Collabs.md). Other questions fit none of the four
templates; just open the issue and write it yourself.

Editing a template: each file is Markdown with a YAML frontmatter block. Put guidance for the
person filling the form inside `<!-- -->` so it stays hidden in the finished issue.
