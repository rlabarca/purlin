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

1. Confirms the current branch and remote configuration (e.g., `git remote -v`, `git status`).
2. Checks that the remote is not ahead of the local branch. If the remote has commits not present locally, the Architect reports the divergence and halts until the user resolves it.

### 2.2 Force-Push Prohibition

The Architect MUST NOT force-push without explicit user confirmation. If the push would require `--force` or `--force-with-lease`, the Architect warns the user and awaits explicit approval before proceeding.

### 2.3 Push Execution

On confirmation, the Architect executes: `git push && git push --tags`

Both commits and tags are pushed. If either command fails, the Architect reports the error and does not mark the step complete.

### 2.4 Enable/Disable Behavior

This step may be set to `enabled: false` in `.agentic_devops/release/config.json`. When disabled, the step is skipped entirely and the release is considered complete at the prior step.

### 2.5 Step Metadata

| Field | Value |
|-------|-------|
| ID | `purlin.push_to_remote` |
| Friendly Name | `Push to Remote Repository` |
| Code | `git push && git push --tags` |
| Agent Instructions | "Confirm the current branch and remote configuration, then push commits and tags to the remote repository. Warn the user if they are about to force-push or if the remote is ahead. Do not proceed without explicit user confirmation for force-push scenarios." |

## 3. Scenarios

### Manual Scenarios (Architect Execution)

#### Scenario: Clean push to remote
Given the local branch is ahead of the remote by one or more commits,
And no force-push is required,
When the Architect executes the `purlin.push_to_remote` step,
Then the Architect runs `git push && git push --tags`,
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
Given `.agentic_devops/release/config.json` has `purlin.push_to_remote` set to `enabled: false`,
When the Architect executes the release checklist,
Then the `purlin.push_to_remote` step is skipped entirely,
And the release is considered complete at the prior step.

## Implementation Notes

This is the only global release step with a non-null `code` field. The shell command `git push && git push --tags` is the canonical execution path. However, the Architect always verifies pre-push conditions (Sections 2.1–2.2) before invoking it.

In Purlin's own `.agentic_devops/release/config.json`, this step is currently set to `enabled: false` pending remote repository setup.
