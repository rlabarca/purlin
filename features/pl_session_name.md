# Feature: Session Name Skill

> Label: "Agent Skills: Common: /pl-session-name Session Name"
> Category: "Install, Update & Scripts"
> Prerequisite: features/terminal_identity.md

[TODO]

## 1. Overview

The `/pl-session-name` skill provides on-demand control over the terminal session display name. It uses the centralized `update_session_identity` function from `identity.sh` to update all detected terminal environments (terminal title, iTerm2 badge, Warp tab name) in a single call. The skill enforces the `(<branch>)` or `(<worktree-label>)` context suffix — callers provide only the label portion and context is appended automatically.

---

## 2. Requirements

### 2.1 Command Interface

```
/pl-session-name [label]
```

- **Scope:** Purlin agent only. Available in all modes (shared).
- **No argument:** Re-derive the session name from the current mode + branch/worktree context.
- **With argument:** Use the provided label as the mode/label portion. The `(context)` suffix is still appended by `update_session_identity`.

### 2.2 No-Argument Behavior

1. Determine the current mode: `Engineer`, `PM`, `QA`, or `Purlin` if no mode is active.
2. Determine the project name from `basename` of the project root (or config `project_name` if available).
3. Call `update_session_identity "<mode>" "<project>"`.
4. Print the updated badge and which terminal environments were updated.

### 2.3 With-Argument Behavior

1. Use the provided argument as the label (replacing the mode name). Examples: `"Engineer: Bootstrap"`, `"Deploy"`, `"Reviewing PR #42"`.
2. Determine the project name.
3. Call `update_session_identity "<label>" "<project>"`.
4. Print the updated badge and which terminal environments were updated.

### 2.4 Environment Reporting

After updating, print a summary showing the computed badge and which environments received the update. Environments that are not detected are silently omitted — no warnings or limitation notes are printed.

Example output:
```
Session: Engineer (main)
Updated: terminal title, iTerm badge
```

### 2.5 Path Resolution

The skill uses `{tools_root}/terminal/identity.sh` resolved per `instructions/references/path_resolution.md`.

---

## 3. Scenarios

### Unit Tests

#### Scenario: No-argument refreshes from current mode

    Given the agent is in Engineer mode on branch "main"
    When /pl-session-name is invoked with no arguments
    Then update_session_identity is called with "Engineer" and the project name
    And the badge is set to "Engineer (main)"

#### Scenario: Custom label preserves branch context

    Given the agent is on branch "feature-xyz"
    When /pl-session-name is invoked with "Deploy"
    Then update_session_identity is called with "Deploy" and the project name
    And the badge is set to "Deploy (feature-xyz)"

#### Scenario: Worktree label used when present

    Given the agent is in a worktree with label "W2"
    When /pl-session-name is invoked with no arguments
    Then the badge includes "(W2)" instead of the branch name

### QA Scenarios

#### Scenario: Session name updates visible in iTerm2

    Given iTerm2 is the active terminal
    And the agent is in PM mode on branch "main"
    When /pl-session-name is invoked
    Then the iTerm2 badge shows "PM (main)"
    And the terminal title shows "purlin - PM (main)"

#### Scenario: Environment reporting lists active environments only

    Given the agent is running in Apple Terminal (not iTerm2, not Warp)
    When /pl-session-name is invoked
    Then the output lists "terminal title" as updated
    And does not mention iTerm badge or Warp tab
