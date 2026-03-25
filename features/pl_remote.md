# Feature: /pl-remote Branch Collaboration

> Label: "Agent Skills: Common: /pl-remote Branch Collaboration"
> Category: "Agent Skills: Common"
> Prerequisite: features/purlin_agent_launcher.md

## 1. Overview

The `/pl-remote` skill consolidates branch collaboration commands (push, pull, add) for multi-user workflows. It replaces the old `/pl-remote-push`, `/pl-remote-pull`, and `/pl-remote-add` skills.

---

## 2. Requirements

### 2.1 Subcommands

- `push` -- Push current branch to remote with safety checks (verify remote exists, warn if dirty, warn before pushing to main).
- `pull` -- Pull remote branch into current branch with merge/ff handling. Show categorized changes after merge.
- `add` -- Configure a git remote (prompt for URL, verify connection).

### 2.2 Consolidation

- Old skill files (`pl-remote-push.md`, `pl-remote-pull.md`, `pl-remote-add.md`) MUST be deleted.
- The consolidated skill MUST handle all three subcommands.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Push with safety check

    Given a configured remote
    When /pl-remote push is invoked on a non-main branch
    Then changes are pushed to the remote

#### Scenario: Pull merges remote changes

    Given a remote branch with new commits
    When /pl-remote pull is invoked
    Then remote changes are merged into the current branch

### Manual Scenarios (Human Verification Required)

None.
