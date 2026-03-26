# Feature: Remote Session Naming

> Label: "Tool: Remote Session Naming"
> Category: "Install, Update & Scripts"
> Prerequisite: features/agent_launchers_common.md
> Prerequisite: features/pl_session_resume.md
> Prerequisite: features/config_layering.md

## 1. Overview

Claude Code's remote control feature allows naming sessions visible in claude.ai/code and the mobile app. Purlin's launcher scripts (`pl-run-*.sh`) currently invoke `claude` without the `--remote-control` flag, so sessions appear unnamed in the session list. This feature adds automatic session naming in the format `<ProjectName> | <Role>` at launch, and a rename suggestion in `/pl-resume` when the agent role changes mid-session.

---

## 2. Requirements

### 2.1 Session Name Format

- Format: `<ProjectName> | <Role>`
- Role display name mapping:
  - `architect` -> `Architect`
  - `builder` -> `Builder`
  - `qa` -> `QA`
  - `pm` -> `PM`
- `ProjectName` is read from the `project_name` config key (used by Purlin tools). Falls back to the project directory basename when the key is absent or empty.

### 2.2 Config Resolver Extension

- `resolve_config.py` CLI role mode (`_cli_role`) outputs one additional shell variable:
  - `PROJECT_NAME` -- the resolved project name with basename fallback.
- Resolution logic: `config.get("project_name", "") or os.path.basename(project_root)`.
- Default when the key is absent or empty: the basename of the project root directory.

### 2.3 Launcher Integration

- All launcher scripts (`pl-run-architect.sh`, `pl-run-builder.sh`, `pl-run-qa.sh`, `pl-run-pm.sh`) always pass `--remote-control "$PROJECT_NAME | $ROLE_DISPLAY"` in the `CLI_ARGS` array.
- Each launcher defines a `ROLE_DISPLAY` variable from the role display name mapping (Section 2.1).
- The `--remote-control` flag is added to `CLI_ARGS` after the resolver `eval` block, using array expansion to handle project names with spaces or special characters.
- Remote control is always enabled by the launcher. Users who do not want remote control manage that through Claude Code's own settings.

### 2.4 Resume Rename Suggestion

- When `/pl-resume` executes with an explicit role argument (tier 1 in Step 1 role detection) that differs from the system prompt's detected role (tier 2), Step 6 recovery summary appends a rename suggestion line:
  ```
  Session name:   run /rename <ProjectName> | <NewRole> to update
  ```
- When the role is unchanged or no system prompt role markers exist (fresh session), no rename suggestion is printed.
- The agent reads `project_name` from config (via the resolver's Python API or direct config read) with basename fallback.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Launcher Always Passes Remote Control Flag

    Given a launcher script (pl-run-architect.sh, pl-run-builder.sh, pl-run-qa.sh, or pl-run-pm.sh)
    When the launcher builds the CLI_ARGS array
    Then CLI_ARGS contains --remote-control with a value in the format "<ProjectName> | <Role>"
    And the value is quoted to handle spaces in the project name

#### Scenario: Session Name Uses project_name From Config

    Given config.local.json contains {"project_name": "My App"}
    When the launcher invokes resolve_config.py for any role
    Then PROJECT_NAME is set to "My App"
    And the session name is "My App | <Role>"

#### Scenario: Session Name Falls Back to Directory Basename

    Given config.local.json does not contain a project_name key
    And the project root directory is named "purlin"
    When the launcher invokes resolve_config.py for any role
    Then PROJECT_NAME is set to "purlin"
    And the session name is "purlin | <Role>"

#### Scenario: Resolver Outputs PROJECT_NAME Variable

    Given config.local.json exists with {"project_name": "Purlin"}
    When resolve_config.py is invoked in role mode (e.g., resolve_config.py builder)
    Then stdout contains PROJECT_NAME="Purlin" among the shell variable assignments

#### Scenario: Resume Suggests Rename When Role Changes

    Given a Builder session is active (system prompt contains Builder role markers)
    When the user invokes /pl-resume architect (explicit role argument)
    Then the recovery summary includes a line:
      Session name:   run /rename <ProjectName> | Architect to update
    And <ProjectName> is resolved from config with basename fallback

#### Scenario: Resume Omits Rename When Role Unchanged

    Given a Builder session is active (system prompt contains Builder role markers)
    When the user invokes /pl-resume builder (same role as system prompt)
    Then the recovery summary does NOT include a "Session name:" line

#### Scenario: Resume Omits Rename When No System Prompt Role Markers

    Given a fresh session with no role identity markers in the system prompt
    When the user invokes /pl-resume builder
    Then the recovery summary does NOT include a "Session name:" line

### QA Scenarios

None.
