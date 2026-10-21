# Branch policy

Status: active. Owner-approved 2026-10-21. This file is normative.

RPTP uses exactly two long-lived branches:

| Branch | Purpose | Permitted changes |
|---|---|---|
| `main` | Release branch. Every commit on `main` must be releasable. | Receives only reviewed `development -> main` pull requests. No direct commits, force-pushes, or deletion. Release tags and release artifacts come from `main` only. |
| `development` | Integration and work branch. All ongoing work lands here. | Direct commits by the owner or an authorized agent. No force-pushes. `development` may be ahead of `main` and is never a release source. |

No other branches are permitted. Do not create feature, chore, fix, release, or hotfix branches. A temporary branch is a policy violation; urgent work still goes through `development` and a pull request to `main`.

## Required workflow

1. Start work from `development` and keep it current with `origin/development`.
2. Commit and push all work to `development`.
3. Run the documented local checks before requesting a release.
4. Open a pull request from `development` to `main` when the work is release-ready.
5. The pull request must include a summary, test evidence, known limitations, and any gate or clean-room impact.
6. Require green CI, including the branch-policy check, before merging.
7. Merge with a merge commit. Do not squash or rebase unless the owner explicitly approves it for that release.
8. After merging, sync `development` from `main` with a fast-forward merge when possible. Do not reset or rewrite shared history.
9. Delete every branch other than `main` and `development` immediately after its audit or merge.

## Prohibited actions

- Direct commits or force-pushes to `main`.
- Pull requests targeting `main` from any branch other than `development`.
- Pull requests from `development` to any branch other than `main`.
- Force-pushes to `development`.
- Release tags or release artifacts from `development`.
- Merging with red or missing required checks.
- Keeping a feature, chore, fix, release, hotfix, or temporary branch after its purpose is complete.
- Committing ISO images, BIOS files, game executables, extracted game assets, or other proprietary game data.

## Release rules

- `main` is the only release branch and the source of release tags.
- A release is the merge commit created by an approved `development -> main` pull request.
- Do not tag `development`.
- A release must record its CI run, commit, test evidence, known limitations, and compatibility status.
- Formal Gate 0, clean-room, and game-compatibility status are independent of a successful merge; a merge must not be used to claim a gate passed or a game is supported.

## Enforcement

- CI runs on pushes to `main` and `development` and on pull requests.
- The `Branch policy` CI job rejects pull requests that are not `development -> main`.
- GitHub branch protection or repository rulesets must require pull requests, green checks, no force-push, and no deletion for both branches. This file cannot configure repository settings; the settings must match this policy.
- If repository settings conflict with this file, stop and ask the owner before merging or pushing.

## Migration record

The one-time migration to this policy is:

1. Audit `chore/post-gate0-reconcile`, rename it to `development`, and merge it to `main` through a reviewed pull request.
2. Delete the old `chore/post-gate0-reconcile` remote branch after the new `development` branch contains all audited commits.
3. Delete `feat/gate2-iso9660-inspector`; it is contained in the audited history and has no unique commits.
4. After migration, the remote branch list must be exactly `main` and `development`.
