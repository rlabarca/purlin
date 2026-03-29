# Feature: Terminal Identity (Title + Badge)

> Label: "Tool: Terminal Identity (Title + Badge)"
> Category: "Install, Update & Scripts"
> Prerequisite: agent_launchers_common.md
> Prerequisite: project_init.md

[TODO]

## 1. Overview

When multiple agent sessions run in separate terminal tabs, there is no visual indicator of which agent is running where. This feature provides multi-environment terminal identity: a terminal title (universal), an iTerm2 badge (iTerm2 only), and a Warp tab name (Warp only, best-effort). All layers use a unified format: `<short_mode>(<branch>) | <label>` — e.g., `Eng(main) | purlin`, `QA(W1) | verify auth`. Mode names are shortened (`Engineer` -> `Eng`; `PM`, `QA`, `Purlin` unchanged). The branch context persists across mode switches so users always know which branch they're on. The label is typically the project name, but long-running skills (build, spec, verify) replace it with a short task description (3-4 words). Engineer mode shows additional state during continuous-mode phase execution via the label. All layers are cleaned up on normal exit and Ctrl+C. A centralized `update_session_identity` function handles context detection and dispatch to all environments, replacing scattered inline logic.

---

## 2. Requirements

### 2.1 Helper Script (`scripts/terminal/identity.sh`)

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

- The `purlin:resume` skill and `purlin:mode` skill set both title and badge to the mode display name on startup and mode switch, using `identity.sh`.
- The helper script is sourced from `$CORE_DIR/scripts/terminal/identity.sh`.

### 2.3 Identity Cleanup

- An EXIT trap calls `clear_agent_identity` to handle normal exit and signals.
- Engineer mode's INT trap (`graceful_stop`) clears identity before resetting the trap.
- Engineer mode's fallback EXIT trap defensively clears identity.
- All clear functions are idempotent (multiple calls are safe).
- Cleanup calls are guarded: `type clear_agent_identity >/dev/null 2>&1 && clear_agent_identity` so that cleanup is safe when the helper was not sourced.

### 2.4 Unified Naming Format

All terminal environments (title, badge, Warp tab) and the remote session name use a single unified format:

```
<short_mode>(<context>) | <label>
```

**Mode shortening:** `Engineer` -> `Eng`. `PM`, `QA`, and `Purlin` are unchanged.

**Context** is the current branch name or worktree label. Worktree label takes priority over branch name. The branch is detected via `git rev-parse --abbrev-ref HEAD`. The worktree label is read from `.purlin_worktree_label` if present. Context MUST always be present — it is never dropped.

**Label** is the project name by default. Long-running skills (`purlin:build`, `purlin:spec`, `purlin:verify`) replace it with a short task description (3-4 words max). The label is optional — when omitted, the format is just `<short_mode>(<context>)`.

Examples:
- **Non-worktree:** `Eng(main) | purlin`, `PM(feature-xyz) | purlin`
- **Worktree:** `Eng(W1) | purlin`, `QA(W2) | verify auth`
- **Open mode:** `Purlin(main) | purlin`
- **Task label:** `Eng(dev/0.8.6) | add auth flow`, `QA(main) | verify login`

This format applies everywhere: `purlin:resume` initialization and Step 11, `purlin:mode` switches, `purlin:build`/`purlin:spec`/`purlin:verify` task start, and Engineer phase transitions.

### 2.5 Engineer Phase Transitions (Continuous Mode)

Both title and badge update together via `update_session_identity` at each phase transition. Phase info is placed in the label (after the `|`):

| State | Display |
|-------|---------|
| Startup / non-continuous | `Eng(<branch>) \| <project>` |
| Bootstrap phase | `Eng(<branch>) \| Bootstrap: <task>` |
| Sequential phase execution | `Eng(<branch>) \| Phase N/M: <task>` |
| Parallel group execution | `Eng(<branch>) \| Phases 2,3,5: <task>` |
| Evaluator running | `Eng(<branch>) \| Evaluating: <task>` |
| Between phases | `Eng(<branch>) \| <project>` |
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

### 2.8 Environment Detection

The helper script detects the terminal environment once at source-time (terminal type cannot change mid-session) and caches the result in shell variables:

- `_PURLIN_ENV_ITERM` — `true` when `$TERM_PROGRAM` is `iTerm.app`.
- `_PURLIN_ENV_WARP` — `true` when `$TERM_PROGRAM` is `WarpTerminal`.
- `_PURLIN_ENV_TITLE` — always `true` (OSC 0 title works in virtually all terminals).

Detection uses a `case` statement on `$TERM_PROGRAM`, extensible by adding new branches for future terminals (Ghostty, Kitty, etc.).

A query function `purlin_detect_env` returns the detection state as a space-separated key:value string for callers that need to inspect which environments are active: `"title:true iterm:false warp:true"`.

### 2.9 Warp Terminal Support

Warp terminal tab naming via two functions:

- `set_warp_tab_name <text>` — sets the Warp tab name via OSC 0 (`\033]0;<text>\007`). No-op when `_PURLIN_ENV_WARP` is not `true`.
- `clear_warp_tab_name` — clears the Warp tab name. No-op when not Warp.

Warp is detected via `TERM_PROGRAM=WarpTerminal`.

**Known limitation:** Warp's OSC 0 support for tab naming is unreliable in some versions (ref: warp-dev/Warp#8330). This implementation is best-effort. The Warp-specific function is separated from `set_term_title` so that a proprietary Warp escape sequence can replace OSC 0 without touching the universal title function.

The convenience wrappers `set_agent_identity` and `clear_agent_identity` dispatch to Warp functions in addition to title and iTerm badge.

### 2.10 Centralized Session Identity

A single function `update_session_identity <mode_display> [label]` encapsulates the full identity update flow:

1. Shorten the mode name via `_purlin_short_mode` (`Engineer` -> `Eng`; `PM`, `QA`, `Purlin` unchanged).
2. Detect branch or worktree context via `_purlin_detect_context` (reads `.purlin_worktree_label` first, falls back to `git rev-parse --abbrev-ref HEAD`).
3. Format the unified string: `<short_mode>(<context>) | <label>` — or `<short_mode>(<context>)` if no label is given.
4. Dispatch to all detected environments: `set_term_title`, `set_iterm_badge`, `set_warp_tab_name` — all receive the same string.
5. Store the computed value in both `$_PURLIN_LAST_BADGE` and `$_PURLIN_LAST_TITLE` (identical). These variables persist in the calling shell's environment.

This function replaces the scattered inline badge-computation + dispatch logic in `purlin:resume`, `PURLIN_BASE.md` section 4.1.1, `purlin:mode`, and `purlin:merge` step 7.

**Backward compatibility:** `set_agent_identity` retains its existing signature for callers that pass pre-formatted text. `update_session_identity` is the preferred API for all new code that needs context detection.

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

#### Scenario: Environment detection identifies iTerm2

    Given TERM_PROGRAM is set to "iTerm.app"
    When the helper script is sourced
    Then _PURLIN_ENV_ITERM is "true"
    And _PURLIN_ENV_WARP is "false"

#### Scenario: Environment detection identifies Warp

    Given TERM_PROGRAM is set to "WarpTerminal"
    When the helper script is sourced
    Then _PURLIN_ENV_WARP is "true"
    And _PURLIN_ENV_ITERM is "false"

#### Scenario: Environment detection for unknown terminal

    Given TERM_PROGRAM is set to "xterm"
    When the helper script is sourced
    Then _PURLIN_ENV_ITERM is "false"
    And _PURLIN_ENV_WARP is "false"
    And _PURLIN_ENV_TITLE is "true"

#### Scenario: Warp tab name emits OSC 0

    Given TERM_PROGRAM is set to "WarpTerminal"
    And the helper script is sourced
    When set_warp_tab_name is called with "PM (main)"
    Then the output contains the escape sequence "\033]0;PM (main)\007"

#### Scenario: Warp tab name is no-op when not Warp

    Given TERM_PROGRAM is set to "iTerm.app"
    And the helper script is sourced
    When set_warp_tab_name is called with "QA"
    Then no output is produced

#### Scenario: update_session_identity computes unified format with branch

    Given a git repository with branch "main"
    And no .purlin_worktree_label file exists
    When update_session_identity is called with "Engineer" and "purlin"
    Then _PURLIN_LAST_BADGE is "Eng(main) | purlin"
    And _PURLIN_LAST_TITLE is "Eng(main) | purlin"

#### Scenario: update_session_identity shortens Engineer to Eng

    Given a git repository with branch "main"
    When update_session_identity is called with "Engineer" and "myproject"
    Then _PURLIN_LAST_BADGE starts with "Eng("

#### Scenario: update_session_identity preserves PM and QA

    Given a git repository with branch "main"
    When update_session_identity is called with "PM" and "myproject"
    Then _PURLIN_LAST_BADGE starts with "PM("
    When update_session_identity is called with "QA" and "myproject"
    Then _PURLIN_LAST_BADGE starts with "QA("

#### Scenario: update_session_identity uses worktree label over branch

    Given a .purlin_worktree_label file contains "W2"
    When update_session_identity is called with "QA" and "myproject"
    Then _PURLIN_LAST_BADGE is "QA(W2) | myproject"
    And _PURLIN_LAST_TITLE is "QA(W2) | myproject"

#### Scenario: update_session_identity without label omits pipe

    Given a git repository with branch "main"
    When update_session_identity is called with "Purlin" and no label
    Then _PURLIN_LAST_BADGE is "Purlin(main)"
    And _PURLIN_LAST_TITLE is "Purlin(main)"

#### Scenario: update_session_identity dispatches to all environments

    Given TERM_PROGRAM is set to "iTerm.app"
    And the helper script is sourced
    When update_session_identity is called with "PM" and "purlin"
    Then set_term_title, set_iterm_badge, and set_warp_tab_name are all invoked

#### Scenario: set_agent_identity includes Warp dispatch

    Given TERM_PROGRAM is set to "WarpTerminal"
    And the helper script is sourced
    When set_agent_identity is called with "Engineer (main)"
    Then set_warp_tab_name is invoked with the title text

#### Scenario: clear_agent_identity includes Warp cleanup

    Given TERM_PROGRAM is set to "WarpTerminal"
    And the helper script is sourced
    When clear_agent_identity is called
    Then clear_warp_tab_name is invoked

#### Scenario: purlin_detect_env returns expected format

    Given TERM_PROGRAM is set to "iTerm.app"
    When purlin_detect_env is called
    Then the output is "title:true iterm:true warp:false"

### QA Scenarios

#### @manual Scenario: Title and badge appear on start and clear on exit

    Given iTerm2 is the active terminal
    And the current branch is "main"
    When the user starts a Purlin session via purlin:resume
    Then the terminal tab title shows "Purlin(main) | purlin"
    And the iTerm2 badge overlay shows "Purlin(main) | purlin"
    When the agent session exits normally
    Then the terminal tab title resets to its default
    And the iTerm2 badge is cleared

#### @manual Scenario: Title and badge clear on Ctrl+C

    Given iTerm2 is the active terminal
    And an agent session is running via purlin:resume
    When the user presses Ctrl+C
    Then the terminal tab title resets to its default
    And the iTerm2 badge is cleared

#### @manual Scenario: Engineer title and badge update during continuous mode phase transitions

    Given iTerm2 is the active terminal
    And the current branch is "main"
    And a delivery plan exists with at least 3 phases
    When the user runs purlin:resume --build with continuous mode enabled
    Then the title and badge show "Eng(main) | purlin" at startup
    And the title and badge show "Eng(main) | Bootstrap: <task>" during the bootstrap phase
    And the title and badge update to "Eng(main) | Phase N/M: <task>" during sequential phase execution
    And the title and badge show "Eng(main) | Evaluating: <task>" when the evaluator runs
    And the title and badge are cleared on exit

#### @manual Scenario: Badge preserves branch context across mode switches

    Given iTerm2 is the active terminal
    And the current branch is "feature-xyz"
    And the agent started with badge "Purlin(feature-xyz) | purlin"
    When the user switches to Engineer mode via purlin:mode engineer
    Then the badge updates to "Eng(feature-xyz) | purlin"
    When the user switches to PM mode via purlin:mode pm
    Then the badge updates to "PM(feature-xyz) | purlin"

#### @manual Scenario: Warp tab name updates on mode switch

    Given Warp terminal is the active terminal
    And the current branch is "main"
    When the user starts a Purlin session
    And switches to Engineer mode via purlin:mode engineer
    Then the Warp tab title shows "Eng(main) | purlin"

#### @manual Scenario: update_session_identity used by purlin:session-name skill

    Given any terminal is active
    And the agent is in PM mode on branch "develop"
    When the user runs purlin:session-name
    Then the terminal title updates to "PM(develop) | purlin"
    And the output shows which environments were updated

#### @manual Scenario: Task label replaces project during long-running skill

    Given iTerm2 is the active terminal
    And the current branch is "main"
    When the user runs purlin:build for feature "auth_flow"
    Then the badge updates to "Eng(main) | auth flow"
    When the build completes or the user switches mode
    Then the badge reverts to "Eng(main) | purlin"

## Regression Guidance
- Unified format everywhere: `<short_mode>(<context>) | <label>` — badge, title, Warp tab, remote session name
- `Engineer` shortened to `Eng`; `PM`, `QA`, `Purlin` unchanged
- Cleanup on normal exit AND Ctrl+C (both title and badge cleared)
- Non-iTerm2 terminals: badge functions are no-op, title still works
- Escape sequences output to /dev/tty, not stdout (safe when piped)
- Continuous mode: phase info goes in the label side (e.g., `Eng(main) | Phase 2/5: auth flow`)
- Branch context in parentheses MUST persist across mode switches — never dropped
- Worktree label takes priority over branch name when both could apply
- Long-running skills (build, spec, verify) replace project name with short task description in the label
- Environment detection cached at source-time, consistent across all calls in session
- Warp tab name best-effort (OSC 0 unreliable in some Warp versions)
- `_PURLIN_LAST_BADGE` and `_PURLIN_LAST_TITLE` are always identical
- `set_agent_identity` backward compatible — still works with pre-formatted text, dispatches to Warp
