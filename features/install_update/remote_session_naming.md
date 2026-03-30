# Feature: Remote Session Naming

> Label: "Tool: Remote Session Naming"
> Category: "Install, Update & Scripts"
> Prerequisite: agent_launchers_common.md
> Prerequisite: purlin_resume.md
> Prerequisite: config_layering.md

## 1. Overview

Claude Code's remote control feature allows naming sessions visible in claude.ai/code and the mobile app. Purlin's `purlin:resume` skill names sessions using the unified format `<short_mode>(<branch>) | <label>` during session initialization, via the `/rename` command or equivalent mechanism. The format is identical to the terminal title and iTerm badge (see `terminal_identity.md` section 2.4). The session name is set once at startup and reflects the starting mode; mid-session mode switches update the iTerm badge and terminal title but cannot update the remote session name (Claude Code does not expose a programmatic rename API).

---

## 2. Requirements

### 2.1 Session Name Format

- Format: `<short_mode>(<context>) | <label>` — unified with terminal title and iTerm badge.
- `short_mode`: `Engineer` -> `Eng`; `PM`, `QA`, `Purlin` unchanged.
- `context`: branch name or worktree label (worktree label takes priority).
- `label`: project name by default. Read from the `project_name` config key. Falls back to the project directory basename when the key is absent or empty.
- Examples:
  - `Eng(main) | purlin`
  - `PM(W1) | MyApp`
  - `Purlin(main) | purlin` (open mode, no mode active)

### 2.2 Config Resolver Extension

- `resolve_config.py` CLI role mode (`_cli_role`) outputs one additional shell variable:
  - `PROJECT_NAME` -- the resolved project name with basename fallback.
- Resolution logic: `config.get("project_name", "") or os.path.basename(project_root)`.
- Default when the key is absent or empty: the basename of the project root directory.

### 2.3 Session Entry Point Integration

- The `purlin:resume` skill sets the session name using the `/rename` command or equivalent mechanism during session initialization:
  - `SESSION_NAME` is the value of `$_PURLIN_LAST_BADGE` after calling `update_session_identity`, which produces the unified format `<short_mode>(<context>) | <label>`.
- Remote control is always enabled. Users who do not want remote control manage that through Claude Code's own settings.

### 2.4 Limitation: No Mid-Session Rename

- Claude Code does not expose a programmatic API to rename a running session.
- The `customTitle` field in the session JSONL is read at launch and cached by the remote control interface; modifying it on disk does not propagate.
- Mid-session mode switches update the iTerm badge and terminal title (via `identity.sh`) but the remote session name remains as set at launch.
- If a future Claude Code release adds a rename API or CLI command (`claude session rename`), this section should be replaced with a mode-switch rename requirement.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Session Name Set During Initialization

    Given purlin:resume is initializing a session
    When the session entry point sets the session name
    Then the session name is in the unified format "<short_mode>(<context>) | <label>"
    And the name is set via the /rename command or equivalent mechanism

#### Scenario: Session Name Uses project_name From Config

    Given config.local.json contains {"project_name": "My App"}
    And the current branch is "main"
    When purlin:resume initializes in Engineer mode
    Then the session name is "Eng(main) | My App"

#### Scenario: Session Name Falls Back to Directory Basename

    Given config.local.json does not contain a project_name key
    And the project root directory is named "purlin"
    And the current branch is "main"
    When purlin:resume initializes in open mode
    Then the session name is "Purlin(main) | purlin"

#### Scenario: Resolver Outputs PROJECT_NAME Variable

    Given config.local.json exists with {"project_name": "Purlin"}
    When resolve_config.py is invoked in role mode (e.g., resolve_config.py purlin)
    Then stdout contains PROJECT_NAME="Purlin" among the shell variable assignments

#### Scenario: Session Name Includes Worktree Label

    Given purlin:resume is invoked with --worktree
    And the assigned worktree label is W1
    And the mode is QA
    When the session entry point sets the session name
    Then the session name is "QA(W1) | <label>"

### QA Scenarios

None.
