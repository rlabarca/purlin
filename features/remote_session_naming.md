# Feature: Remote Session Naming

> Label: "Tool: Remote Session Naming"
> Category: "Install, Update & Scripts"
> Prerequisite: features/agent_launchers_common.md
> Prerequisite: features/pl_session_resume.md
> Prerequisite: features/config_layering.md

## 1. Overview

Claude Code's remote control feature allows naming sessions visible in claude.ai/code and the mobile app. Purlin's `purlin:start` skill names sessions in the format `<ProjectName> | <Badge>` during session initialization, using the `/rename` command or equivalent mechanism. The session name is set once at startup and reflects the starting mode; mid-session mode switches update the iTerm badge and terminal title but cannot update the remote session name (Claude Code does not expose a programmatic rename API).

---

## 2. Requirements

### 2.1 Session Name Format

- Format: `<ProjectName> | <Badge>`
- `Badge` is identical to the iTerm badge value set by `identity.sh`:
  - Mode name alone in the main worktree: `Engineer`, `PM`, `QA`, `Purlin` (open mode).
  - With worktree label appended when running in a worktree: `Engineer (W1)`, `QA (W2)`, etc.
- `ProjectName` is read from the `project_name` config key (used by Purlin tools). Falls back to the project directory basename when the key is absent or empty.
- Examples:
  - `purlin | Engineer`
  - `MyApp | PM (W1)`
  - `purlin | Purlin` (open mode, no mode active)

### 2.2 Config Resolver Extension

- `resolve_config.py` CLI role mode (`_cli_role`) outputs one additional shell variable:
  - `PROJECT_NAME` -- the resolved project name with basename fallback.
- Resolution logic: `config.get("project_name", "") or os.path.basename(project_root)`.
- Default when the key is absent or empty: the basename of the project root directory.

### 2.3 Session Entry Point Integration

- The `purlin:start` skill sets the session name using the `/rename` command or equivalent mechanism during session initialization:
  - `SESSION_NAME` is computed as `"$PROJECT_NAME | $ROLE_DISPLAY"` where `ROLE_DISPLAY` is the badge value (mode name with optional worktree label).
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

    Given purlin:start is initializing a session
    When the session entry point sets the session name
    Then the session name is in the format "<ProjectName> | <Badge>"
    And the name is set via the /rename command or equivalent mechanism

#### Scenario: Session Name Uses project_name From Config

    Given config.local.json contains {"project_name": "My App"}
    When purlin:start invokes resolve_config.py
    Then PROJECT_NAME is set to "My App"
    And the session name is "My App | <Badge>"

#### Scenario: Session Name Falls Back to Directory Basename

    Given config.local.json does not contain a project_name key
    And the project root directory is named "purlin"
    When purlin:start invokes resolve_config.py
    Then PROJECT_NAME is set to "purlin"
    And the session name is "purlin | <Badge>"

#### Scenario: Resolver Outputs PROJECT_NAME Variable

    Given config.local.json exists with {"project_name": "Purlin"}
    When resolve_config.py is invoked in role mode (e.g., resolve_config.py purlin)
    Then stdout contains PROJECT_NAME="Purlin" among the shell variable assignments

#### Scenario: Session Name Includes Worktree Label

    Given purlin:start is invoked with --worktree
    And the assigned worktree label is W1
    When the session entry point sets the session name
    Then the session name is "<ProjectName> | <Mode> (W1)"

### QA Scenarios

None.
