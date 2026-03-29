# Feature: Session Name Skill

> Label: "Agent Skills: Common: purlin:session-name Session Name"
> Category: "Install, Update & Scripts"
> Prerequisite: terminal_identity.md

[TODO]

## 1. Overview

The `purlin:session-name` skill provides on-demand control over the terminal session display name. It uses the centralized `update_session_identity` function from `identity.sh` to update all detected terminal environments (terminal title, iTerm2 badge, Warp tab name) in a single call. The unified format is `<short_mode>(<context>) | <label>` — see `terminal_identity.md` section 2.4.

---

## 2. Requirements

### 2.1 Command Interface

```
purlin:session-name [label]
```

- **Scope:** Purlin agent only. Available in all modes (shared).
- **No argument:** Re-derive the session name from the current mode + branch/worktree context.
- **With argument:** Use the provided argument as the label (after `|`). Mode and context are still derived automatically.

### 2.2 No-Argument Behavior

1. Determine the current mode: `Engineer`, `PM`, `QA`, or `Purlin` if no mode is active.
2. Determine the project name from `basename` of the project root (or config `project_name` if available).
3. Call `update_session_identity "<mode>" "<project>"`.
4. Print the updated badge and which terminal environments were updated.

### 2.3 With-Argument Behavior

1. Use the provided argument as the label (replaces the project name in the `| <label>` portion). Examples: `"fix auth flow"`, `"Deploy"`, `"PR #42 review"`.
2. Determine the current mode.
3. Call `update_session_identity "<mode>" "<label>"`.
4. Print the updated badge and which terminal environments were updated.

### 2.4 Environment Reporting

After updating, print a summary showing the computed badge and which environments received the update. Environments that are not detected are silently omitted — no warnings or limitation notes are printed.

Example output:
```
Session: Eng(main) | purlin
Updated: terminal title, iTerm badge
```

### 2.5 Path Resolution

The skill uses `${CLAUDE_PLUGIN_ROOT}/scripts/terminal/identity.sh` per `references/path_resolution.md`.

---

## 3. Scenarios

### Unit Tests

#### Scenario: No-argument refreshes from current mode

    Given the agent is in Engineer mode on branch "main"
    And the project name is "purlin"
    When purlin:session-name is invoked with no arguments
    Then update_session_identity is called with "Engineer" and "purlin"
    And the badge is set to "Eng(main) | purlin"

#### Scenario: Custom label replaces project in display

    Given the agent is in QA mode on branch "feature-xyz"
    When purlin:session-name is invoked with "verify auth"
    Then update_session_identity is called with "QA" and "verify auth"
    And the badge is set to "QA(feature-xyz) | verify auth"

#### Scenario: Worktree label used when present

    Given the agent is in Engineer mode in a worktree with label "W2"
    And the project name is "purlin"
    When purlin:session-name is invoked with no arguments
    Then the badge is "Eng(W2) | purlin"

### QA Scenarios

#### Scenario: Session name updates visible in iTerm2

    Given iTerm2 is the active terminal
    And the agent is in PM mode on branch "main"
    And the project name is "purlin"
    When purlin:session-name is invoked
    Then the iTerm2 badge shows "PM(main) | purlin"
    And the terminal title shows "PM(main) | purlin"

#### Scenario: Environment reporting lists active environments only

    Given the agent is running in Apple Terminal (not iTerm2, not Warp)
    When purlin:session-name is invoked
    Then the output lists "terminal title" as updated
    And does not mention iTerm badge or Warp tab
