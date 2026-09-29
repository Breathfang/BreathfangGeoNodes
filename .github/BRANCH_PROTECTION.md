# Branch protection for `main`

The `Nightly` workflow (`.github/workflows/nightly.yml`) is only useful if a
finding can actually stop a merge. On its own a failing `security-scan` job is
just a red X on a page nobody has to look at. These settings make it a hard
gate.

## What you are protecting

| Job | Runs on | Can it block a merge? |
| --- | --- | --- |
| `Security scan` | every PR to `main`, every push to `main` | **Yes.** This is the required status check. |
| `Build and deploy` | pushes to `main` only | No. It never runs on a PR. |

A confirmed violation exits `1`, the `Security scan` job goes red, and the
required check keeps the PR open. A file the scanner cannot read is reported as
`[WARNING]` and skipped, so a corrupt `.blend` does not block an unrelated PR.

## Setup (repository Settings UI)

1. Go to **Settings → Rules → Rulesets → New ruleset → New branch ruleset**.
   (For an older repository, use **Settings → Branches → Add rule** instead —
   the same options live there under different labels.)
2. **Ruleset name:** `main protection`.
3. **Enforcement status:** `Active`.
4. **Target branches:** `Include` a branch pattern of `main`.
5. Under **Rules**, enable:
   - **Require a pull request before merging**
     - *Required approvals:* `1`
     - *Dismiss stale pull request approvals when new commits are pushed:* on
     - *Require conversation resolution before merging:* on
   - **Require status checks to pass**, then add exactly one check:
     - search for and select **`Security scan`**
   - **Require branches to be up to date before merging** (strict mode).
   - **Require linear history:** optional, on if you prefer squash-only.
6. Leave **Do not allow bypassing the above settings** off, and add a bypass
   entry — see the next section, it is not optional.

## The bypass list is required, not optional

`build-and-deploy` commits the generated zip straight back to `main` using
`GITHUB_TOKEN`. GitHub **rejects that push** once `main` is protected, and the
job fails at the `git push` step. Without a bypass entry, the first nightly
deployment breaks.

Add one of these under **Bypass list** in the ruleset:

| Actor | When to use it |
| --- | --- |
| **`github-actions`** (the app) | Preferred. Lets the workflow push the zip while humans still go through a PR. |
| `github-actions[bot]` (the user) | Equivalent, if your repository offers the user form. |
| A maintainer account | For emergency manual releases. Prefer leaving this out. |

The bypass only covers the push the workflow already made after
`security-scan` passed. It does not let anyone merge a failing PR.

## Verify it worked

1. Open any pull request against `main`.
2. Confirm the **Checks** tab lists `Security scan`.
3. Add a throwaway `.py` file to `DragonGraph's Project/` containing
   `import os` and open or update the PR.
4. `Security scan` must go **red** with `unauthorized import 'os'`, and the
   **Merge** button must stay disabled.
5. Close the PR and delete the file. Do not commit it.

Also confirm the merge box reports *"Expected — waiting for status check"*
rather than *"Expected — checking"*. The second one means the check is not
registered as required yet and the rule is not doing anything.

## Enabling the nightly build

`build-and-deploy` is additionally gated on
`NIGHTLY_BUILDS_ENABLED` in `.github/scripts/.env`. To resume builds, set it to
`true` and commit.

`gate_check.py` fails the run with exit `1` if that toggle cannot be resolved
(missing `.env`, missing key, empty value, non-boolean). That is intentional:
a gate that cannot read its own toggle must not be allowed to guess. An
explicit `false` is not an error — it skips the deploy and leaves the security
scan running.

## Emergency bypasses

There are two, and both are visible in the audit trail:

- **Locally:** `SKIP_SECURITY_HOOK=1 git push`. The pre-push hook prints a
  banner saying nothing was scanned. CI still scans the resulting PR.
- **In the ruleset:** the bypass list above.

Neither one can make a failing `Security scan` merge through a pull request.
