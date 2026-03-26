# Feature: Terminal Identity (Title + Badge)

> Label: "Tool: Terminal Identity (Title + Badge)"
> Category: "Install, Update & Scripts"
> Prerequisite: features/agent_launchers_common.md
> Prerequisite: features/project_init.md

[TODO]

## 1. Overview

When multiple agent sessions run in separate terminal tabs, there is no visual indicator of which agent is running where. This feature adds two layers of terminal identity: a terminal title (universal, works in all terminals) that sets the tab/window title to the agent role, and an iTerm2 badge (iTerm2 only) that overlays the role name for at-a-glance identification. Both layers show the agent mode name with the current branch (or worktree label) in parentheses — e.g., `PM (main)`, `Engineer (W1)`. The branch context persists across mode switches so users always know which branch they're on. Engineer mode shows additional state during continuous-mode phase execution. Both layers are cleaned up on normal exit and Ctrl+C.

---

## 2. Requirements

### 2.1 Helper Script (`tools/terminal/identity.sh`)

A sourceable bash library (not directly executable) providing two tiers of functions:

**Terminal Title (universal -- works in all terminals):**
- `set_term_title <text>` sets the tab/window title via the `\033]0;<text>\007` escape sequence.
- `clear_term_title` resets the title to empty, restoring the terminal's default title behavior.

**iTerm2 Badge (iTerm2 only):**
- `set_iterm_badge <text>` sets the badge via the `\e]1337;SetBadgeFormat=<base64>\a` escape sequence, where `<base64>` is the base64-encoded text.
- `clear_iterm_badge` clears the badge text by sending an empty base64 payload.
- Badge functions are a no-op when `$TERM_PROGRAM != "iTerm.app"`.

**Convenience wrappers:**
- `set_agent_identity <text>` calls both `set_term_title` and `set_iterm_badge` with the same text.
- `clear_agent_identity` calls both `clear_term_title` and `clear_iterm_badge`.

**Portability and output rules:**
- Base64 encoding uses `echo -n "$text" | base64 | tr -d '\n'` for macOS and GNU compatibility.
- All escape sequence output goes to `/dev/tty` when available, not stdout (which may be piped or redirected).
- No color management -- text only. Color can be layered on in a future feature.

### 2.2 Identity on Agent Start

- All four root launchers (`pl-run.sh`, `pl-run.sh`, `pl-run.sh`, `pl-run.sh`) and all generated launchers (via `init.sh`) set both title and badge to their display name on startup.
- The helper script is sourced from `$CORE_DIR/tools/terminal/identity.sh`.

### 2.3 Identity Cleanup

- An EXIT trap calls `clear_agent_identity` to handle normal exit and signals.
- Engineer mode's INT trap (`graceful_stop`) clears identity before resetting the trap.
- Engineer mode's fallback EXIT trap defensively clears identity.
- All clear functions are idempotent (multiple calls are safe).
- Cleanup calls are guarded: `type clear_agent_identity >/dev/null 2>&1 && clear_agent_identity` so that cleanup is safe when the helper was not sourced.

### 2.4 Persistent Branch Context in Badge

The badge MUST always include the current branch name (or worktree label) in parentheses. This applies at startup, on mode switches, and during phase transitions — the branch context is never dropped.

- **Non-worktree:** `<mode-text> (<branch>)` — e.g., `PM (main)`, `Engineer (feature-xyz)`.
- **Worktree:** `<mode-text> (<worktree-label>)` — e.g., `Engineer (W1)`. Worktree label takes priority over branch name.
- **Open mode:** `Purlin (<branch>)` or `Purlin (<worktree-label>)`.

The branch is detected via `git rev-parse --abbrev-ref HEAD`. The worktree label is read from `.purlin_worktree_label` if present.

This rule applies everywhere the badge is set: launcher startup, `/pl-resume` Step 6, `/pl-mode` switches, and Engineer phase transitions.

### 2.5 Engineer Phase Transitions (Continuous Mode)

Both title and badge update together via `set_agent_identity` at each phase transition. Branch context is always appended:

| State | Title / Badge Text |
|-------|-----------|
| Startup / non-continuous | `Engineer (<branch>)` |
| Bootstrap phase | `Engineer: Bootstrap (<branch>)` |
| Sequential phase execution | `Engineer: Phase N/M (<branch>)` |
| Parallel group execution | `Engineer: Phases 2,3,5 (<branch>)` |
| Evaluator running | `Engineer: Evaluating (<branch>)` |
| Between phases | `Engineer (<branch>)` |
| Exit / Ctrl+C | (cleared) |

### 2.6 Generated Launcher Integration (`tools/init.sh`)

- The `generate_launcher()` function emits code that sources the helper script, sets identity on start, and includes an augmented EXIT trap with `clear_agent_identity`.
- Consumer projects receive terminal identity support on the next `pl-init.sh` refresh cycle.
- The role display name is computed from the role parameter: `architect` -> `PM`, `qa` -> `QA`, `pm` -> `PM`, `builder` -> `Engineer`.

### 2.7 Graceful Degradation

- Terminal title works in all terminals (iTerm2, Terminal.app, VS Code integrated terminal, etc.).
- iTerm2 badge is a no-op when `$TERM_PROGRAM != "iTerm.app"`.
- All functions are a no-op when the helper script is missing (e.g., an older submodule that does not include the file).
- No error output is produced in degraded mode.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Title escape sequence emitted for any terminal

    Given the helper script is sourced
    And TERM_PROGRAM is set to any value
    When set_term_title is called with "PM"
    Then the output to /dev/tty contains the escape sequence "\033]0;PM\007"

#### Scenario: Badge escape sequence emitted for iTerm2

    Given the helper script is sourced
    And TERM_PROGRAM is set to "iTerm.app"
    When set_iterm_badge is called with "Engineer"
    Then the output to /dev/tty contains the escape sequence "\e]1337;SetBadgeFormat=<base64 of 'Engineer'>\a"

#### Scenario: Badge is no-op when not iTerm2

    Given the helper script is sourced
    And TERM_PROGRAM is set to "Apple_Terminal"
    When set_iterm_badge is called with "QA"
    Then no output is produced

#### Scenario: Badge is no-op when TERM_PROGRAM is unset

    Given the helper script is sourced
    And TERM_PROGRAM is not set
    When set_iterm_badge is called with "PM"
    Then no output is produced

#### Scenario: Base64 encoding round-trips correctly

    Given the helper script is sourced
    When "Engineer: Phase 2/5" is base64-encoded using the helper's method
    Then decoding the result produces the original string

#### Scenario: set_agent_identity calls both title and badge

    Given the helper script is sourced
    And TERM_PROGRAM is set to "iTerm.app"
    When set_agent_identity is called with "PM (main)"
    Then both the title escape sequence and the badge escape sequence are emitted

#### Scenario: clear_agent_identity calls both clear functions

    Given the helper script is sourced
    And TERM_PROGRAM is set to "iTerm.app"
    When clear_agent_identity is called
    Then both the title-clear and badge-clear escape sequences are emitted

#### Scenario: Generated launcher contains set_agent_identity call

    Given a consumer project has been initialized with pl-init.sh
    When the generated launcher for "architect" is inspected
    Then it contains a call to set_agent_identity with "PM"

#### Scenario: Generated launcher EXIT trap contains clear_agent_identity

    Given a consumer project has been initialized with pl-init.sh
    When the generated launcher for "builder" is inspected
    Then its EXIT trap contains a guarded call to clear_agent_identity

#### Scenario: Generated launcher uses correct display name per role

    Given a consumer project has been initialized with pl-init.sh
    When launchers are generated for each role
    Then architect uses "PM", builder uses "Engineer", qa uses "QA", pm uses "PM"

### QA Scenarios

#### @manual Scenario: Title and badge appear on start and clear on exit

    Given iTerm2 is the active terminal
    And the current branch is "main"
    When the user runs ./pl-run.sh and the agent session starts
    Then the terminal tab title shows "Purlin (main)"
    And the iTerm2 badge overlay shows "Purlin (main)"
    When the agent session exits normally
    Then the terminal tab title resets to its default
    And the iTerm2 badge is cleared

#### @manual Scenario: Title and badge clear on Ctrl+C

    Given iTerm2 is the active terminal
    And an agent session is running via ./pl-run.sh
    When the user presses Ctrl+C
    Then the terminal tab title resets to its default
    And the iTerm2 badge is cleared

#### @manual Scenario: Engineer title and badge update during continuous mode phase transitions

    Given iTerm2 is the active terminal
    And the current branch is "main"
    And a delivery plan exists with at least 3 phases
    When the user runs ./pl-run.sh --continuous
    Then the title and badge show "Engineer (main)" at startup
    And the title and badge show "Engineer: Bootstrap (main)" during the bootstrap phase
    And the title and badge update to "Engineer: Phase N/M (main)" during sequential phase execution
    And the title and badge show "Engineer: Evaluating (main)" when the evaluator runs
    And the title and badge are cleared on exit

#### @manual Scenario: Badge preserves branch context across mode switches

    Given iTerm2 is the active terminal
    And the current branch is "feature-xyz"
    And the agent started with badge "Purlin (feature-xyz)"
    When the user switches to Engineer mode via /pl-mode engineer
    Then the badge updates to "Engineer (feature-xyz)"
    When the user switches to PM mode via /pl-mode pm
    Then the badge updates to "PM (feature-xyz)"

## Regression Guidance
- Cleanup on normal exit AND Ctrl+C (both title and badge cleared)
- Non-iTerm2 terminals: badge functions are no-op, title still works
- Escape sequences output to /dev/tty, not stdout (safe when piped)
- Continuous mode: title updates through phase transitions (Bootstrap -> Phase N/M -> Evaluating)
- Branch context in parentheses MUST persist across mode switches — never dropped to bare mode name
- Worktree label takes priority over branch name when both could apply
