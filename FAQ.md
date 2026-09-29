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
- [Contributing & Security](#contributing-security)
  - [Why can't I push my changes?](#why-cant-i-push-my-changes)
  - [What happens if I bypass the pre-push hook?](#what-happens-if-i-bypass-the-pre-push-hook)
  - [Can I modify the .github directory?](#can-i-modify-the-github-directory)
  - [Why was I banned from contributing?](#why-was-i-banned-from-contributing)
    - [Why that is a GitHub terms violation](#why-that-is-a-github-terms-violation)
    - [What happens during a project ban?](#what-happens-during-a-project-ban)
  - [Can I appeal a ban?](#can-i-appeal-a-ban)
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
file containing an embedded Python script will be rejected, and you will be
[banned from contributing](#why-was-i-banned-from-contributing).

Python scripts **are** allowed inside the add-on directory &mdash; just never inside a `.blend`
file. The repository enforces this automatically: every push and pull request is scanned, and a
found script fails the build.

### Can I remake a node from another node pack?

Yes, as long as you meaningfully improve it. Remaking another pack's node and contributing it
here with no significant changes is not allowed.

### Can I contribute using a newer Blender than the base version?

Yes &mdash; but not to the base library. The base asset library stays on **Blender 5.2 LTS** so it
keeps working for everyone on 5.2, and a node that needs something newer goes into a separate
**extension pack** instead. The two prefixes are:

- **Base asset library** (5.2 LTS) &rarr; `DGraph: Node Name Here`
- **Extension packs** (5.3, 5.4, 5.5, or other) &rarr; `DGraphExt: Node Name Here`

The full table is in [Requirements](README.md#requirements).

So a node built in 5.3, 5.4, 5.5, or any other version ships as `DGraphExt: Node Name Here` in its
own `.blend`, and a node that works in 5.2 LTS ships as `DGraph: Node Name Here` in the base
library. Please do not open an extension-pack node in an older Blender and file it as a bug: it
targets a specific version and is expected to fail elsewhere, which is exactly why it is kept out
of the base library.

In your submission, say which Blender version the node needs so the right pack is chosen. See
[Requirements](README.md#requirements) and
[Blend file contributions](CONTRIBUTING.md#blend-file-contributions).

## Contributing & Security

### Why can't I push my changes?

A push fails when the local pre-push hook detects a security violation in your changes. The hook runs
[`python_security_scanner.py`](.github/scripts/python_security_scanner.py) and
[`blend_scanner.py`](.github/scripts/blend_scanner.py) on every file under `DragonGraph's Project/` before the push
completes, and it aborts if either scanner finds a confirmed violation.

Common violations that block a push:

- **Python embedded in a `.blend` file** — The blend scanner detects this and rejects the push. This is a
  hard security rule because an embedded script would run on anyone who opens the pack.
- **Dangerous Python patterns** — The security scanner detects imports of `os`, `subprocess`, `socket`, use of
  `eval`/`exec`, `.system()`-style calls, and obfuscated patterns.

The hook is a safety net: it catches violations locally so you can fix them before they reach the repository.
See [Local pre-push gate](CONTRIBUTING.md#local-pre-push-gate) for installation instructions.

### What happens if I bypass the pre-push hook?

**Do not bypass the pre-push hook.** The hook exists to protect both you and the project from shipping
malicious or unsafe code.

If you force a push past the hook using `SKIP_SECURITY_HOOK=1 git push` or any other bypass method:

- **Your pull request will be rejected.** The CI security scan runs on every pull request and push to `main`,
  and there is no bypass in the workflow itself. A violation found in CI fails the `Security scan` check,
  and the pull request cannot merge until it passes.
- **You may face disciplinary action.** Bypassing security checks is treated as a deliberate violation of
  project policy. Depending on the severity, this can lead to a warning, temporary suspension, or permanent
  ban from contributing.
- **Repeated bypasses lead to a project ban.** Intentionally circumventing security controls demonstrates
  disregard for the project's security standards and the safety of all users. This is grounds for an immediate
  and permanent ban.

The pre-push hook is not an obstacle to work around — it is a guardrail. If the hook blocks your push,
fix the issue it reports rather than bypassing it. See [Security checks](CONTRIBUTING.md#security-checks) for
what the scanners look for.

### Can I modify the .github directory?

**No.** The `.github/` directory contains GitHub Actions workflows, issue templates, security scripts,
and repository configuration. Only maintainers, lead maintainers, and the project leader have permission
to modify files in this directory.

Contributors do not have write access to `.github/` because these files control critical repository
functions:

- **Workflows** (`.github/workflows/`) — Define CI/CD pipelines, security scans, and automated builds
- **Scripts** (`.github/scripts/`) — Security scanners and automation tools that run on every push
- **Issue templates** (`.github/ISSUE_TEMPLATE/`) — Standardized forms for reporting bugs and submitting nodes
- **Repository settings** — Branch protection, team permissions, and other GitHub configurations

If you encounter an issue with the `.github/` directory (for example, a workflow is failing, a template is
incorrect, or a script has a bug), **report it as a GitHub issue** rather than attempting to fix it yourself.
Describe the problem clearly, and a maintainer will address it.

> [!WARNING]
> **Do not bypass this restriction.** Attempting to modify `.github/` without permission — including
> opening pull requests that change these files — will be rejected. Repeated attempts to circumvent
> this rule may lead to disciplinary action, up to and including a project ban. See
> [What happens if I bypass the pre-push hook?](#what-happens-if-i-bypass-the-pre-push-hook) for the
> project's policy on circumventing security controls.

### Why was I banned from contributing?

A ban is issued when the [contribution requirements](CONTRIBUTING.md#requirements), the quality
standards, or a core security policy are violated. The most common cause by far is
[embedding a Python script inside a `.blend` file](CONTRIBUTING.md#blend-file-contributions),
because the pack ships the `.blend` itself and an embedded script would run on anyone who opens it.

A ban is a decision about a specific account, not about whether your work was wanted. A ban does
not mean your node was rejected on quality grounds &mdash; it means a line was crossed that the
maintainer cannot undo after the fact.

#### What happens during a project ban?

When your account is banned from contributing to this repository, the following restrictions apply:

- **Write access is revoked.** You cannot push to any branch, open pull requests, or merge changes.
- **Issue creation is disabled.** You cannot open new issues, including feature requests, bug reports,
  or questions.
- **Commenting is restricted.** Your ability to comment on existing issues and pull requests may be
  limited or removed entirely.
- **Collaborator status is removed.** If you had collaborator access with additional permissions, those
  permissions are immediately revoked.
- **All contributions are rejected.** Any pending pull requests or issues you have open will be closed
  and will not be processed.

These restrictions are enforced at the repository level by GitHub's access controls. They remain in
place until the ban is lifted through the [appeal process](#can-i-appeal-a-ban) or, if the ban is
permanent, indefinitely.

> [!WARNING]
> **No ban evasion.** Do not attempt to work around a restriction by creating a secondary or
> alternative account, or by having someone else submit work on your behalf. This is not only a
> project rule: it is a separate breach of GitHub's own terms, and it is enforceable by GitHub
> rather than by us. See the table below.

#### Why that is a GitHub terms violation

GitHub does not publish a clause named "ban evasion", so do not expect to find one. The provisions
that cover this behaviour are these:

| Provision | What it says |
| --------- | ------------ |
| [GitHub ToS &sect;B.3 &mdash; Account Requirements](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service#b-account-terms) | "One person or legal entity may maintain **no more than one free Account**." |
| [Acceptable Use Policies &sect;4 &mdash; Spam and Inauthentic Activity](https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies#4-spam-and-inauthentic-activity-on-github) | Prohibits "**inauthentic interactions, such as fake accounts** and automated inauthentic activity". |
| [Acceptable Use Policies &sect;3 &mdash; Authenticity](https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies#3-intellectual-property-authenticity-and-private-information) | Prohibits impersonation, including "**fraudulently misrepresenting your identity**". |
| [Community Guidelines &mdash; enforcement](https://docs.github.com/en/site-policy/github-terms/github-community-guidelines#what-happens-if-someone-violates-githubs-policies) | GitHub may respond by "**suspending a user account or organization**", or [terminating it](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service#m-cancellation-and-termination). |

A second account is therefore a **terms breach in its own right**, whatever it is used for, and the
consequence GitHub documents is suspension or termination. That outcome outlasts any decision made
here: it survives even a project ban you would have appealed successfully, and it applies to every
repository, not just this one. Trading a reversible decision by a project maintainer for a
platform-level one is a bad trade, and
[the appeal route below](#can-i-appeal-a-ban) exists precisely so the trade never needs making.

### Can I appeal a ban?

Yes, if you believe the ban was issued in error. Appeals are handled **exclusively** through the
official social media channels linked in the
[GitHub repository](https://github.com/Breathfang/BreathfangGeoNodes) &mdash; not as a GitHub
issue, pull request, or comment on a closed thread, and not through an alternative account.

Include what you contributed, which account was banned, and why you think the decision was
mistaken. Keep it to one message; repeated appeals across several channels do not help your case.

> [!NOTE]
> A banned account cannot submit the appeal itself. Use a channel that is not the banned account,
> and be transparent that you are doing so. Concealing it is [ban evasion](#why-was-i-banned-from-contributing),
> which turns an appealable mistake into a permanent one.

A **project** ban and a **platform** ban are different things, and they are appealed to different
people. This page covers a project ban, which only affects contributions here. If GitHub itself has
suspended or disabled your account, that is not something we can reverse: appeal it through
[GitHub's Appeal and Reinstatement page](https://docs.github.com/en/site-policy/acceptable-use-policies/github-appeal-and-reinstatement)
using their [reinstatement form](https://support.github.com/contact/reinstatement).

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
