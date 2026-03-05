# Feature: Push to Remote Repository

> Label: "Release Step: Push to Remote Repository"
> Category: "Release Process"
> Prerequisite: features/policy_release.md
> Prerequisite: features/release_checklist_core.md

## 1. Overview

This feature defines the `purlin.push_to_remote` release step: the delivery step that pushes release commits and tags to the remote repository. This step is enabled by default but may be disabled for air-gapped projects or projects where a separate CI/CD pipeline handles delivery (see `policy_release.md` Invariant 2.4).

## 2. Requirements

### 2.1 Pre-Push Verification

Before pushing, the Architect:

1. Runs `git remote -v` to discover all configured remotes and their URLs.
2. Runs `git branch` to discover local branches.
3. Identifies the default remote: the upstream tracking remote for the current branch (via `git rev-parse --abbrev-ref @{upstream}`), falling back to `origin` if no upstream is set.
4. Identifies the default branch: the current branch (via `git rev-parse --abbrev-ref HEAD`).
5. Presents the user with a confirmation prompt showing the default remote, its URL, and the branch. If multiple remotes exist, lists all available remotes so the user can pick an alternative. If multiple local branches exist, lists them for alternative selection.
6. The presentation should make it easy to accept defaults (e.g., "Push `main` to `origin` (`git@bitbucket.org:...`)? [Y/n]").
7. Checks that the selected remote is not ahead of the local branch. If the remote has commits not present locally, the Architect reports the divergence and halts until the user resolves it.

### 2.2 Force-Push Prohibition

The Architect MUST NOT force-push without explicit user confirmation. If the push would require `--force` or `--force-with-lease`, the Architect warns the user and awaits explicit approval before proceeding.

### 2.3 Push Execution

On confirmation, the Architect executes: `git push <remote> <branch> && git push <remote> --tags`

The `<remote>` and `<branch>` are the values confirmed by the user in Section 2.1 (either the defaults or user-selected alternatives). Both commits and tags are pushed. If either command fails, the Architect reports the error and does not mark the step complete.

### 2.4 Enable/Disable Behavior

This step may be set to `enabled: false` in `.purlin/release/config.json`. When disabled, the step is skipped entirely and the release is considered complete at the prior step.

### 2.5 Step Metadata

| Field | Value |
|-------|-------|
| ID | `purlin.push_to_remote` |
| Friendly Name | `Push to Remote Repository` |
| Code | `null` (interactive step; not automatable as a one-liner) |
| Agent Instructions | "1. Run `git remote -v` and `git branch` to discover remotes and branches. 2. Identify the default remote (upstream tracking remote for the current branch, or `origin`) and default branch (current branch). 3. Present the default: 'Push `<branch>` to `<remote>` (`<url>`)?' If multiple remotes exist, list alternatives. 4. If the user accepts, execute `git push <remote> <branch> && git push <remote> --tags`. 5. If the user picks a different remote/branch, use their selection. 6. Warn if force-push is required; halt if the remote is ahead. Do not proceed without explicit user confirmation for force-push scenarios." |

## 3. Scenarios

### Automated Scenarios
None. All verification is manual (Architect-executed release step).

### Manual Scenarios (Architect Execution)

#### Scenario: Clean push to remote
Given the local branch is ahead of the remote by one or more commits,
And no force-push is required,
When the Architect executes the `purlin.push_to_remote` step,
Then the Architect presents the default remote and branch for confirmation,
And on acceptance runs `git push <remote> <branch> && git push <remote> --tags`,
And reports the push result including branches and tags updated.

#### Scenario: Remote is ahead of local
Given the remote branch has commits not present locally,
When the Architect executes the `purlin.push_to_remote` step,
Then the Architect reports the divergence and halts,
And instructs the user to pull and reconcile before re-running the step.

#### Scenario: Force-push would be required
Given the push cannot proceed without `--force`,
When the Architect executes the `purlin.push_to_remote` step,
Then the Architect warns the user that force-push is required,
And awaits explicit user confirmation before proceeding,
And does not force-push without that confirmation.

#### Scenario: Step is disabled
Given `.purlin/release/config.json` has `purlin.push_to_remote` set to `enabled: false`,
When the Architect executes the release checklist,
Then the `purlin.push_to_remote` step is skipped entirely,
And the release is considered complete at the prior step.

#### Scenario: Multiple remotes, user accepts default
Given the project has remotes "origin" and "github",
And the current branch is "main" tracking "origin/main",
When the Architect executes the `purlin.push_to_remote` step,
Then the Architect presents "Push `main` to `origin` (`<url>`)?" as the default,
And lists "github" as an alternative remote,
And the user can accept the default or choose a different remote.

#### Scenario: Single remote, streamlined confirmation
Given the project has only one remote "origin",
And the current branch is "main",
When the Architect executes the `purlin.push_to_remote` step,
Then the Architect presents "Push `main` to `origin` (`<url>`)?" for confirmation,
And does not prompt for remote selection.