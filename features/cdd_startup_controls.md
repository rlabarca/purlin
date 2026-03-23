# Feature: CDD Startup Controls

> Label: "Tool: CDD Startup Controls"
> Category: "Install, Update & Scripts"
> Prerequisite: features/models_configuration.md
> Prerequisite: features/agent_launchers_common.md
> Prerequisite: features/cdd_agent_configuration.md
> Web Test: http://localhost:9086
> Web Start: /pl-cdd

[Complete]

## 1. Overview

Two per-agent boolean flags (`find_work` and `auto_start`) control how much orientation an agent performs at session start. A startup print sequence (agent name + command vocabulary table) runs unconditionally at the beginning of every session, regardless of these flags.

`find_work` controls whether the agent runs its full orientation and suggests a work plan. `auto_start` controls whether the agent begins executing immediately without waiting for user approval. The flags allow expert users to bypass orientation and hand-holding while keeping new-project defaults fully guided.


## 2. Requirements

### 2.1 Config Schema

*   **Fields:** Each agent entry in `config.json` (`agents.architect`, `agents.builder`, `agents.qa`, `agents.pm`) has two boolean fields:
    *   `find_work` (boolean, default `true`): When `true`, the agent runs its full orientation at session start (status check, Critic report, dependency graph, triage) and presents a prioritized work plan. When `false`, the agent skips orientation and awaits a direct instruction.
    *   `auto_start` (boolean, default `false`): When `true` (requires `find_work: true`), after presenting the work plan the agent begins executing immediately without waiting for user approval. When `false`, the agent waits for the user to approve or adjust the plan before proceeding.
*   **Invalid combination:** `find_work: false` with `auto_start: true` is not meaningful. This combination MUST be rejected (see Section 2.3).
*   **Valid combinations:**

    | `find_work` | `auto_start` | Behavior |
    |-------------|--------------|----------|
    | `true` | `false` | Guided session: orient, suggest work plan, wait for approval (default for new projects) |
    | `true` | `true` | Auto mode: orient, suggest work plan, begin executing immediately |
    | `false` | `false` | Expert mode: print command table, await instruction |
    | `false` | `true` | **Invalid** |

*   **Canonical schema extension** (both `config.json` and `purlin-config-sample/config.json` MUST be updated to include the new fields):

```json
"agents": {
    "pm":        { "model": "...", "effort": "...", "bypass_permissions": true, "find_work": true, "auto_start": false },
    "architect": { "model": "...", "effort": "...", "bypass_permissions": true, "find_work": true, "auto_start": false },
    "builder":   { "model": "...", "effort": "...", "bypass_permissions": true, "find_work": true, "auto_start": false },
    "qa":        { "model": "...", "effort": "...", "bypass_permissions": true, "find_work": true, "auto_start": false }
}
```

*   **Fallback:** If either field is absent from `config.json`, the launcher MUST default `find_work` to `true` and `auto_start` to `false`.

### 2.2 Startup Print Sequence (Always-On)

*   **Unconditional:** Every agent session begins by printing a command vocabulary table as its very first output, regardless of `find_work` or `auto_start` values. This behavior is not configurable.
*   **Format:** Agent name and status line, a Unicode horizontal rule, command rows (command left-aligned, description separated by consistent whitespace), a closing horizontal rule. Example for the Builder:

```
Purlin Builder — Ready
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  /pl-status                 Check CDD status and action items
  /pl-find <topic>           Discover where a topic belongs in the spec system
  /pl-build [name]           Implement pending work or a specific feature
  /pl-delivery-plan          Create or review phased delivery plan
  /pl-infeasible <name>      Escalate a feature as unimplementable
  /pl-propose <topic>        Surface a spec change suggestion to the Architect
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

*   **Commands shown per role:** Shared commands (`/pl-status`, `/pl-find`) appear in every agent's table, followed by the role-specific commands. The full command vocabulary for each role is defined in `README.md ## The Agents`.
*   **Implementation:** This behavior is encoded in each role's instruction files (Architect-owned). The instruction files for `instructions/ARCHITECT_BASE.md`, `instructions/BUILDER_BASE.md`, `instructions/QA_BASE.md`, and `instructions/PM_BASE.md` are updated by the Architect as a companion action to this feature's delivery. The Builder does not modify instruction files.

### 2.3 Launcher Validation

*   Each launcher (`pl-run-architect.sh`, `pl-run-builder.sh`, `pl-run-qa.sh`, `pl-run-pm.sh`) MUST read `find_work` and `auto_start` for its role from `config.json` at startup, before invoking Claude.
*   **Invalid combination check:** When `find_work` is `false` and `auto_start` is `true`, the launcher MUST print an error message to stderr describing the invalid combination and exit with status 1 without invoking Claude.
*   **No behavioral injection:** The launchers do not conditionally modify the prompt or session message based on these flags. Actual conditional startup behavior is driven by the agent's instruction files (which read the flags from `config.json` directly).

### 2.4 Conditional Startup Behavior (Instruction-Driven)

*   **How agents read their flags:** Each agent reads `find_work` and `auto_start` from the resolved config (`config.local.json` if it exists, otherwise `config.json`) at session start using its standard Bash tool access, before executing any other startup step.
*   **When `find_work: false`:** Skip orientation entirely. After printing the command table, output a single line: `"find_work disabled -- awaiting instruction."` Then await user input.
*   **When `find_work: true` and `auto_start: false`:** Execute the full startup orientation sequence, present the prioritized work plan, and explicitly ask for confirmation or adjustment before proceeding.
*   **When `find_work: true` and `auto_start: true`:** Execute the full startup orientation sequence, present the prioritized work plan, and begin executing the first item immediately without waiting for user approval.

### 2.5 Dashboard Toggle Controls

*   **Location:** Within the existing Agents section (from `features/cdd_agent_configuration.md`), each agent row gains two checkbox controls appended to the right of the existing YOLO checkbox.
*   **Controls per row:** Two checkboxes with no inline labels; each is identified by its column header in the section header row (see `cdd_agent_configuration.md` Section 2.1):
    *   `find_work` -> column header **"Find"** / **"Work"** (two lines)
    *   `auto_start` -> column header **"Auto"** / **"Start"** (two lines)
*   **Constraint enforcement:** When the user unchecks the Find Work control, the Auto Start checkbox for that agent MUST be simultaneously disabled and unchecked. Re-checking Find Work re-enables Auto Start to its previous state.
*   **Persistence:** Changes are written via `POST /config/agents` immediately, using the same debounce and pending-write-lock pattern as existing model/effort/YOLO controls (see `cdd_agent_configuration.md` Section 2.1).
*   **Styling:** Native checkboxes using `accent-color: var(--purlin-accent)`. No inline label text is rendered beside the checkboxes in agent rows; column headers provide all identification.
*   **Grid layout:** The agent row grid extends by two columns: `(agent name | model | effort | YOLO | Find/Work | Auto/Start)`. Column alignment is consistent across all four agent rows per the grid rules in `cdd_agent_configuration.md` Section 2.1. Disabled controls use `opacity: 0.4` to signal unavailability; their column space is preserved.

### 2.6 API Extension

*   **`POST /config/agents`:** The endpoint MUST accept `find_work` and `auto_start` fields within each agent object. Validation rules:
    *   Both MUST be boolean if present.
    *   The combination `find_work: false` + `auto_start: true` for any agent MUST be rejected with HTTP 400.
*   **`GET /status` (config portion):** The status endpoint response MUST include `find_work` and `auto_start` in the agent config it returns, so the dashboard can restore checkbox state on load.

### 2.7 Integration Test Fixture Tags

| Tag | State Description |
|-----|-------------------|
| `main/cdd_startup_controls/all-disabled` | Project with find_work false for all roles |
| `main/cdd_startup_controls/expert-mode` | Project with both find_work and auto_start disabled (false) for all roles |
| `main/cdd_startup_controls/auto-mode` | Project with find_work true and auto_start true for all roles |

## 3. Scenarios

### Automated Scenarios

#### Scenario: Launcher Rejects Invalid Flag Combination
    Given config.json contains agents.builder with find_work false and auto_start true
    When pl-run-builder.sh is executed
    Then the script prints an error message describing the invalid combination to stderr
    And exits with status 1
    And does not invoke the claude CLI

#### Scenario: Launcher Accepts Valid Combinations Without Error
    Given config.json contains agents.builder with find_work true and auto_start false
    When pl-run-builder.sh is executed
    Then the script exits without an error related to startup controls
    And invokes the claude CLI normally

#### Scenario: Launcher Defaults Missing Fields
    Given config.json does not contain find_work or auto_start for agents.architect
    When pl-run-architect.sh reads agent config
    Then AGENT_FIND_WORK defaults to true
    And AGENT_AUTO_START defaults to false

#### Scenario: API Rejects Invalid Combination
    Given a POST /config/agents request body where agents.qa has find_work false and auto_start true
    When the endpoint processes the request
    Then it returns HTTP 400
    And config.json is not modified

#### Scenario: API Accepts Valid Payload
    Given a POST /config/agents request body with find_work true and auto_start false for all agents
    When the endpoint processes the request
    Then it returns HTTP 200
    And config.json is updated with the new values

#### Scenario: Startup Print Sequence Appears First (auto-test-only)
    Given any agent is launched with any combination of startup controls
    When the agent produces its first output
    Then the command vocabulary table appears before any other text
    And the table includes the shared commands and all role-specific commands

#### Scenario: Expert Mode Bypasses Orientation (auto-test-only)
    Given agents.builder has find_work false and auto_start false in config.json
    When the Builder is launched
    Then the command table is printed first
    And the agent outputs "find_work disabled -- awaiting instruction."
    And no status check, Critic report, or dependency graph analysis is performed

#### Scenario: Guided Mode Presents Work Plan (auto-test-only)
    Given agents.builder has find_work true and auto_start false in config.json
    When the Builder is launched
    Then orientation runs in full
    And a prioritized work plan is presented
    And the agent explicitly asks for confirmation or adjustment before beginning work

#### Scenario: Auto Mode Begins Executing Immediately (auto-test-only)
    Given agents.builder has find_work true and auto_start true in config.json
    When the Builder is launched
    Then orientation runs in full
    And a prioritized work plan is presented
    And the agent begins executing the first item immediately without asking for approval

#### Scenario: Dashboard Toggle Controls Render in Agents Section (auto-web)
    Given the CDD Dashboard is loaded and the Agents section is expanded
    When the user views any agent row
    Then the Find Work and Auto Start checkboxes appear to the right of YOLO
    And their column headers appear in the section header row on two lines each
    And their checked state matches the values in config.json

#### Scenario: Auto Start Disables When Find Work Unchecked (auto-web)
    Given the Agents section is expanded
    When the user unchecks the Find Work control for an agent
    Then the Auto Start checkbox for that agent is immediately disabled and unchecked
    And POST /config/agents is called with find_work false and auto_start false for that agent

### Manual Scenarios (Human Verification Required)

None.

## Regression Guidance
- Invalid config combination (find_work: false + auto_start: true) rejected at validation time
- Startup print sequence runs unconditionally regardless of flag values
- Config changes via dashboard POST persist to config.local.json, not config.json
- Auto Start checkbox disables when Find Work is unchecked (cascading UI constraint)
