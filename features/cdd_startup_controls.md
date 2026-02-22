# Feature: CDD Startup Controls

> Label: "Tool: CDD Startup Controls"
> Category: "Install, Update & Scripts"
> Prerequisite: features/models_configuration.md
> Prerequisite: features/agent_launchers_common.md
> Prerequisite: features/cdd_agent_configuration.md


## 1. Overview

Two per-agent boolean flags (`startup_sequence` and `recommend_next_actions`) control how much orientation an agent performs at session start. A startup print sequence (agent name + command vocabulary table) runs unconditionally at the beginning of every session, regardless of these flags.

The flags allow expert users to bypass orientation and hand-holding while keeping new-project defaults fully guided.


## 2. Requirements

### 2.1 Config Schema

*   **New fields:** Each agent entry in `config.json` (`agents.architect`, `agents.builder`, `agents.qa`) gains two new boolean fields:
    *   `startup_sequence` (boolean, default `true`): When `true`, the agent runs its full orientation at session start (status check, Critic report, dependency graph, triage). When `false`, the agent skips orientation and awaits a direct instruction.
    *   `recommend_next_actions` (boolean, default `true`): When `true`, after orientation the agent presents a prioritized work plan and waits for approval before proceeding. When `false`, the agent orients silently and then awaits direction.
*   **Invalid combination:** `startup_sequence: false` with `recommend_next_actions: true` is not meaningful. This combination MUST be rejected (see Section 2.3).
*   **Valid combinations:**

    | `startup_sequence` | `recommend_next_actions` | Behavior |
    |--------------------|--------------------------|----------|
    | `true` | `true` | Full guided session (default for new projects) |
    | `true` | `false` | Agent orients, then awaits direction |
    | `false` | `false` | Expert mode: print command table, await instruction |
    | `false` | `true` | **Invalid** |

*   **Canonical schema extension** (both `config.json` and `purlin-config-sample/config.json` MUST be updated to add the new fields with defaults `true`):

```json
"agents": {
    "architect": { "model": "...", "effort": "...", "bypass_permissions": true, "startup_sequence": true, "recommend_next_actions": true },
    "builder":   { "model": "...", "effort": "...", "bypass_permissions": true, "startup_sequence": true, "recommend_next_actions": true },
    "qa":        { "model": "...", "effort": "...", "bypass_permissions": true, "startup_sequence": true, "recommend_next_actions": true }
}
```

*   **Fallback:** If either field is absent from `config.json`, the launcher MUST default both to `true`.

### 2.2 Startup Print Sequence (Always-On)

*   **Unconditional:** Every agent session begins by printing a command vocabulary table as its very first output, regardless of `startup_sequence` or `recommend_next_actions` values. This behavior is not configurable.
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
*   **Implementation:** This behavior is encoded in each role's instruction files (Architect-owned). The instruction files for `instructions/ARCHITECT_BASE.md`, `instructions/BUILDER_BASE.md`, and `instructions/QA_BASE.md` are updated by the Architect as a companion action to this feature's delivery. The Builder does not modify instruction files.

### 2.3 Launcher Validation

*   Each launcher (`run_architect.sh`, `run_builder.sh`, `run_qa.sh`) MUST read `startup_sequence` and `recommend_next_actions` for its role from `config.json` at startup, before invoking Claude.
*   **Invalid combination check:** When `startup_sequence` is `false` and `recommend_next_actions` is `true`, the launcher MUST print an error message to stderr describing the invalid combination and exit with status 1 without invoking Claude.
*   **No behavioral injection:** The launchers do not conditionally modify the prompt or session message based on these flags. Actual conditional startup behavior is driven by the agent's instruction files (which read the flags from `config.json` directly).

### 2.4 Conditional Startup Behavior (Instruction-Driven)

*   **How agents read their flags:** Each agent reads `startup_sequence` and `recommend_next_actions` from `config.json` at session start using its standard Bash tool access, before executing any other startup step.
*   **When `startup_sequence: true`:** Execute the full startup orientation sequence as currently specified in the role's instruction file (run `tools/cdd/status.sh`, read Critic report, check dependency graph, perform triage).
*   **When `startup_sequence: false`:** Skip orientation entirely. After printing the command table, output a single line: `"startup_sequence disabled — awaiting instruction."` Then await user input.
*   **When `recommend_next_actions: true` (requires `startup_sequence: true`):** After completing orientation, present the prioritized work plan and explicitly ask for confirmation or adjustment before proceeding.
*   **When `recommend_next_actions: false` (with `startup_sequence: true`):** Complete orientation silently, then output a brief status summary (feature counts by status, open Critic items count), and await user direction without presenting a full work plan.

### 2.5 Dashboard Toggle Controls

*   **Location:** Within the existing Agents section (from `features/cdd_agent_configuration.md`), each agent row gains two checkbox controls appended to the right of the existing YOLO checkbox.
*   **Controls per row:** Two checkboxes with no inline labels; each is identified by its column header in the section header row (see `cdd_agent_configuration.md` Section 2.1):
    *   `startup_sequence` → column header **"Startup"** / **"Sequence"** (two lines)
    *   `recommend_next_actions` → column header **"Suggest"** / **"Next"** (two lines)
*   **Constraint enforcement:** When the user unchecks the Startup Sequence control, the Suggest Next checkbox for that agent MUST be simultaneously disabled and unchecked. Re-checking Startup Sequence re-enables Suggest Next to its previous state.
*   **Persistence:** Changes are written via `POST /config/agents` immediately, using the same debounce and pending-write-lock pattern as existing model/effort/YOLO controls (see `cdd_agent_configuration.md` Section 2.1).
*   **Styling:** Native checkboxes using `accent-color: var(--purlin-accent)`. No inline label text is rendered beside the checkboxes in agent rows; column headers provide all identification.
*   **Grid layout:** The agent row grid extends by two columns: `(agent name | model | effort | YOLO | Startup/Sequence | Suggest/Next)`. Column alignment is consistent across all three agent rows per the grid rules in `cdd_agent_configuration.md` Section 2.1. Disabled controls use `opacity: 0.4` to signal unavailability; their column space is preserved.

### 2.6 API Extension

*   **`POST /config/agents`:** The endpoint MUST accept `startup_sequence` and `recommend_next_actions` fields within each agent object. Validation rules:
    *   Both MUST be boolean if present.
    *   The combination `startup_sequence: false` + `recommend_next_actions: true` for any agent MUST be rejected with HTTP 400.
*   **`GET /status` (config portion):** The status endpoint response MUST include `startup_sequence` and `recommend_next_actions` in the agent config it returns, so the dashboard can restore checkbox state on load.


## 3. Scenarios

### Automated Scenarios

#### Scenario: Launcher Rejects Invalid Flag Combination
    Given config.json contains agents.builder with startup_sequence false and recommend_next_actions true
    When run_builder.sh is executed
    Then the script prints an error message describing the invalid combination to stderr
    And exits with status 1
    And does not invoke the claude CLI

#### Scenario: Launcher Accepts Valid Combinations Without Error
    Given config.json contains agents.builder with startup_sequence true and recommend_next_actions false
    When run_builder.sh is executed
    Then the script exits without an error related to startup controls
    And invokes the claude CLI normally

#### Scenario: Launcher Defaults Missing Fields to True
    Given config.json does not contain startup_sequence or recommend_next_actions for agents.architect
    When run_architect.sh reads agent config
    Then AGENT_STARTUP defaults to true
    And AGENT_RECOMMEND defaults to true

#### Scenario: API Rejects Invalid Combination
    Given a POST /config/agents request body where agents.qa has startup_sequence false and recommend_next_actions true
    When the endpoint processes the request
    Then it returns HTTP 400
    And config.json is not modified

#### Scenario: API Accepts Valid Payload
    Given a POST /config/agents request body with startup_sequence true and recommend_next_actions false for all agents
    When the endpoint processes the request
    Then it returns HTTP 200
    And config.json is updated with the new values

### Manual Scenarios (Human Verification Required)

#### Scenario: Startup Print Sequence Appears First
    Given any agent is launched with any combination of startup controls
    When the agent produces its first output
    Then the command vocabulary table appears before any other text
    And the table includes the shared commands and all role-specific commands

#### Scenario: Expert Mode Bypasses Orientation
    Given agents.builder has startup_sequence false and recommend_next_actions false in config.json
    When the Builder is launched
    Then the command table is printed first
    And the agent outputs "startup_sequence disabled — awaiting instruction."
    And no status check, Critic report, or dependency graph analysis is performed

#### Scenario: Guided Mode Presents Work Plan
    Given agents.builder has startup_sequence true and recommend_next_actions true in config.json
    When the Builder is launched
    Then orientation runs in full
    And a prioritized work plan is presented
    And the agent explicitly asks for confirmation or adjustment before beginning work

#### Scenario: Orient-Only Mode Skips Work Plan
    Given agents.builder has startup_sequence true and recommend_next_actions false in config.json
    When the Builder is launched
    Then orientation runs in full
    And a brief status summary is output
    And no work plan is presented; the agent awaits user direction

#### Scenario: Dashboard Toggle Controls Render in Agents Section
    Given the CDD Dashboard is loaded and the Agents section is expanded
    When the user views any agent row
    Then the Startup Sequence and Suggest Next checkboxes appear to the right of YOLO
    And their column headers appear in the section header row on two lines each
    And their checked state matches the values in config.json

#### Scenario: Suggest Next Disables When Startup Sequence Unchecked
    Given the Agents section is expanded
    When the user unchecks the Startup Sequence control for an agent
    Then the Suggest Next checkbox for that agent is immediately disabled and unchecked
    And POST /config/agents is called with startup_sequence false and recommend_next_actions false for that agent


## Implementation Notes

### BUG Resolution: startup_sequence Flag Ignored (2026-02-22)
Initial implementation ran full orientation despite `startup_sequence: false`. Fixed by Architect adding explicit flag-gating sections (5.0.1/2.0.1/3.0.1) to all three BASE instruction files. Re-verified PASS 2026-02-22.

### Ownership Boundary
The Builder implements: config schema updates (both `config.json` and `purlin-config-sample/config.json`), launcher validation logic, dashboard checkbox controls, and API validation. The Architect separately updates instruction files (`instructions/ARCHITECT_BASE.md`, `instructions/BUILDER_BASE.md`, `instructions/QA_BASE.md`) to add the startup print sequence and conditional startup behavior. Instruction files are not Builder-owned.

### Config Reading Pattern for New Fields
Launchers read the new flags with the same Python one-liner pattern used for existing agent fields:
```sh
eval "$(python3 -c "
import json, sys
try:
    cfg = json.load(open('.purlin/config.json'))
    a = cfg.get('agents', {}).get('ROLE', {})
    print('AGENT_STARTUP=' + ('true' if a.get('startup_sequence', True) else 'false'))
    print('AGENT_RECOMMEND=' + ('true' if a.get('recommend_next_actions', True) else 'false'))
except Exception:
    print('AGENT_STARTUP=true')
    print('AGENT_RECOMMEND=true')
")"
```
The `ROLE` placeholder is substituted per-launcher (`architect`, `builder`, `qa`).

### Suggest-Next Disable Logic
The "Startup Sequence" checkbox `onchange` handler: when unchecked, sets `checkbox_suggest_next.disabled = true` and `checkbox_suggest_next.checked = false`, then marks both controls as pending. When re-checked, restores `checkbox_suggest_next.disabled = false` and restores the checkbox to its pre-disable state (cached locally before the disable action).

### Dashboard Grid Extension
The base agent row grid from `cdd_agent_configuration.md` uses `grid-template-columns: 64px 140px 80px 60px` (agent-name | model | effort | YOLO). Extend with two fixed-width columns: `grid-template-columns: 64px 140px 80px 60px 60px 60px` (agent-name | model | effort | YOLO | Startup/Sequence | Suggest/Next). The column header row gains two new cells with two-line text ("Startup" / "Sequence" and "Suggest" / "Next") using `<br>` or CSS wrapping; no inline labels appear in the agent data rows.

### QA Verification (2026-02-22)
All 6 manual scenarios PASS. Expert Mode BUG (QA invokes /pl-status before reading startup flags) re-verified PASS after Architect added CRITICAL prohibition to QA_BASE.md Section 3.0.

### **[CLARIFICATION]** BUG Ownership: /pl-status Invocation Before Flag Read (Severity: INFO)
The BUG "QA agent invokes /pl-status before reading startup flags" was in Architect scope, not Builder scope. All Builder-owned code (launchers, API validation, dashboard checkboxes, config schema) was implemented and passing 19/19 tests. The bug was an LLM agent behavior issue: the QA agent did not follow the instruction ordering in `QA_BASE.md` Section 3.0.1. Fixed 2026-02-22 by adding a CRITICAL prohibition to `QA_BASE.md` Section 3.0: the print-table step must output the pre-formatted text verbatim with no tool or skill invocations. The Builder has no mechanism to enforce instruction-level behavior from launchers (per Section 2.3: "No behavioral injection"). This case also drove a SOP update — see `HOW_WE_WORK_BASE.md` Section 7.5 and `policy_critic.md` Section 2.4 for the new `Action Required: Architect` override mechanism for instruction-level BUGs.

## User Testing Discoveries
