# Feature: /pl-toolbox Skill

> Label: "Agent Skills: Common: /pl-toolbox Agentic Toolbox"
> Category: "Agent Skills"
> Owner: PM
> Prerequisite: features/toolbox_core.md

## 1. Overview

The `/pl-toolbox` skill provides the user-facing interface for the Agentic Toolbox system. It supports listing, running, creating, editing, copying, deleting, and sharing tools across all three categories (Purlin, Project, Community). The skill is available in all modes — any mode can list and run tools; Engineer mode is required for create, edit, copy, delete, push, and add operations.

---

## 2. Requirements

### 2.1 Subcommands

| Subcommand | Usage | Description |
|---|---|---|
| *(none)* | `/pl-toolbox` | Guided interactive menu (Section 2.2) |
| `list` | `/pl-toolbox list` | Show all tools grouped by category |
| `run` | `/pl-toolbox run <tool> [tool2 ...]` | Execute one or more tools sequentially |
| `create` | `/pl-toolbox create` | Create a new project tool interactively |
| `edit` | `/pl-toolbox edit <tool>` | Edit a project or community tool |
| `copy` | `/pl-toolbox copy <purlin-tool>` | Copy a purlin tool to project for customization |
| `add` | `/pl-toolbox add <git-url>` | Download a community tool from a git repo |
| `pull` | `/pl-toolbox pull [tool]` | Update community tool(s) from source repo |
| `push` | `/pl-toolbox push <tool> [git-url]` | Push a tool to its source repo or a new repo |
| `delete` | `/pl-toolbox delete <tool>` | Delete a project or community tool |

### 2.2 Guided No-Args Menu

When `/pl-toolbox` is invoked with no subcommand, display:

```
Agentic Toolbox
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
What would you like to do?

  1. List all tools           /pl-toolbox list
  2. Run tool(s)              /pl-toolbox run <name> [name2 ...]
  3. Create a new tool        /pl-toolbox create
  4. Add a community tool     /pl-toolbox add <git-url>
  5. Manage tools             /pl-toolbox edit|copy|delete
  6. Share a tool             /pl-toolbox push <tool> [git-url]

Enter a number or command:
```

The agent waits for user input, then executes the corresponding subcommand.

### 2.3 List Subcommand

**Output format:**

```
Agentic Toolbox — <N> tools

PURLIN (<count>)                                              source: framework
  purlin.verify_zero_queue            Verify Zero-Queue Status
  purlin.doc_consistency_check        Documentation Consistency Check

PROJECT (<count>)                                             source: .purlin/toolbox/
  submodule_safety_audit              Submodule Safety Audit

COMMUNITY (<count>)                                           source: git repos
  community.deploy_vercel             Deploy to Vercel  v1.2.0
    by: user@example.com
    repo: git@github.com:user/purlin-tool-deploy-vercel.git
```

*   Categories with zero tools are omitted from output.
*   Community tools show author and repo on indented lines below the tool entry.

### 2.4 Run Subcommand

*   Accepts one or more tool names. Multiple tools run sequentially in the order specified.
*   Tool names are resolved via fuzzy matching (see `toolbox_core.md` Section 2.6).
*   For each tool, the agent reads `agent_instructions` and/or `code` from the tool definition and executes them.
*   If `agent_instructions` is non-null, the agent follows those instructions.
*   If `code` is non-null and `agent_instructions` is null, the agent executes the shell command.
*   If both are non-null, the agent follows `agent_instructions` (which may reference the `code` command).
*   If both are null, error: `"Tool '<id>' has no instructions or code to execute."`

### 2.5 Create Subcommand

Interactive flow:

1. Prompt for tool ID (validate: non-empty, no reserved prefixes, no collision with existing tools).
2. Prompt for friendly name.
3. Prompt for description.
4. Ask whether to add `code` (shell command). If yes, prompt for the command.
5. Ask whether to add `agent_instructions` (natural language). If yes, prompt for instructions.
7. Write the new tool to `project_tools.json`.
8. Confirm: `"Created tool '<id>' in project_tools.json."`

### 2.6 Edit Subcommand

*   Resolve tool name via fuzzy matching.
*   **Purlin tool (submodule context):** Block with message: `"Purlin tools are read-only in consumer projects. Use '/pl-toolbox copy <tool>' to create an editable project copy."` Submodule context is detected by running `git -C "${TOOLS_ROOT}" rev-parse --show-superproject-working-tree 2>/dev/null` — a non-empty result means tools are inside a git submodule.
*   **Purlin tool (framework repo):** Allow editing. Read the tool definition from `purlin_tools.json`, present all fields for editing, write changes back.
*   **Project tool:** Read the tool definition from `project_tools.json`. Present all fields for editing. Write changes back.
*   **Community tool:** Read the tool definition from `.purlin/toolbox/community/<tool_id>/tool.json`. Warn: `"Local edits will diverge from upstream. Next '/pl-toolbox pull' will detect the conflict."` Present fields for editing. Write changes back.

### 2.7 Copy Subcommand

*   Resolve tool name via fuzzy matching. Only purlin tools can be copied (project and community tools are already editable).
*   Prompt for a new tool ID (strip `purlin.` prefix as default suggestion, e.g., `purlin.verify_zero_queue` → suggest `verify_zero_queue`).
*   Copy all fields from the purlin tool definition.
*   Set `metadata.last_updated` to today.
*   Write to `project_tools.json`.
*   Confirm: `"Copied 'purlin.<name>' to project tool '<new_id>'. You can now edit it with '/pl-toolbox edit <new_id>'."`

### 2.8 Delete Subcommand

*   Resolve tool name via fuzzy matching.
*   **Purlin tool (submodule context):** Block with message: `"Purlin tools cannot be deleted in consumer projects. They are distributed with the framework."` (Same submodule detection as Section 2.6 — `git rev-parse --show-superproject-working-tree`.)
*   **Purlin tool (framework repo):** Allow deletion. Show a dry-run preview, confirm, then remove from `purlin_tools.json`.
*   **Project tool:** Show a dry-run preview of what will be removed. On confirmation, remove from `project_tools.json`.
*   **Community tool:** Show a dry-run preview of what will be removed (registry entry + community directory). On confirmation, remove from `community_tools.json` and delete `.purlin/toolbox/community/<tool_id>/` directory.

### 2.9 Add, Pull, Push Subcommands

See `toolbox_community.md` for the full lifecycle specification.

### 2.10 Path Resolution

Read `.purlin/config.json` and extract `tools_root` (default: `"tools"`). Resolve project root via `PURLIN_PROJECT_ROOT` env var or by climbing from CWD until `.purlin/` is found. Set `TOOLS_ROOT = <project_root>/<tools_root>`.

### 2.11 Mode and Activation

*   `/pl-toolbox` is available in all modes (shared).
*   `list` and `run` do not require a specific mode.
*   `create`, `edit`, `copy`, `delete`, `add`, `pull`, `push` activate Engineer mode (they modify tool registries which are code-adjacent artifacts).
*   If another mode is active when a write subcommand is invoked, confirm mode switch first.

### 2.12 Error Handling

All error messages are clear, actionable, and suggest a recovery path:

*   Edit purlin tool (submodule) → suggests `copy`. Edit purlin tool (framework) → allows edit.
*   Delete purlin tool (submodule) → explains why and stops. Delete purlin tool (framework) → allows with confirmation.
*   Reserved prefix → names the prefix and explains the restriction.
*   Network failure → confirms no state was modified.
*   Missing tool.json in repo → explains what the repo needs.
*   Ambiguous fuzzy match → shows candidates.
*   Tool not found → suggests `list`.
*   Push without repo on project tool → shows the required syntax.
*   No instructions or code → explains the tool is empty.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: No-args shows guided menu

    Given the user invokes "/pl-toolbox" with no subcommand
    When the skill executes
    Then the guided menu is displayed with numbered options
    And the agent waits for user input

#### Scenario: List shows all categories

    Given purlin_tools.json contains 6 tools
    And project_tools.json contains 3 tools
    And community_tools.json contains 1 tool
    When the user runs "/pl-toolbox list"
    Then output shows PURLIN (6), PROJECT (3), COMMUNITY (1) sections
    And each tool shows id and friendly_name

#### Scenario: Run single tool

    Given a tool exists with id "purlin.verify_zero_queue" and agent_instructions set
    When the user runs "/pl-toolbox run verify_zero_queue"
    Then the agent executes the tool's agent_instructions

#### Scenario: Run multiple tools sequentially

    Given tools "purlin.verify_zero_queue" and "purlin.doc_consistency_check" exist
    When the user runs "/pl-toolbox run verify_zero_queue doc_consistency_check"
    Then both tools execute in the order specified

#### Scenario: Create project tool

    Given no tool with id "my_audit" exists
    When the user runs "/pl-toolbox create" and provides id "my_audit", friendly_name "My Audit", description "Custom audit"
    Then project_tools.json contains a new tool with id "my_audit"

#### Scenario: Edit blocked for purlin tool in submodule context

    Given the project uses purlin as a git submodule
    And the user runs "/pl-toolbox edit purlin.verify_zero_queue"
    When the skill resolves the tool
    Then the message "Purlin tools are read-only in consumer projects. Use '/pl-toolbox copy ...' to create an editable project copy." is displayed
    And no file is modified

#### Scenario: Edit allowed for purlin tool in framework repo

    Given the project is the purlin framework repository (not a submodule consumer)
    And the user runs "/pl-toolbox edit purlin.verify_zero_queue"
    When the skill resolves the tool
    Then the tool definition is presented for editing

#### Scenario: Copy purlin tool to project

    Given purlin tool "purlin.verify_zero_queue" exists
    When the user runs "/pl-toolbox copy purlin.verify_zero_queue" and accepts id "verify_zero_queue"
    Then project_tools.json contains a new tool with id "verify_zero_queue"
    And the tool definition matches the original except for id and metadata.last_updated

#### Scenario: Delete project tool with preview

    Given project tool "my_audit" exists
    When the user runs "/pl-toolbox delete my_audit"
    Then a dry-run preview is shown listing what will be removed
    And the user is asked to confirm before deletion

#### Scenario: Delete blocked for purlin tool in submodule context

    Given the project uses purlin as a git submodule
    And the user runs "/pl-toolbox delete purlin.verify_zero_queue"
    When the skill resolves the tool
    Then the message "Purlin tools cannot be deleted in consumer projects. They are distributed with the framework." is displayed

#### Scenario: Delete allowed for purlin tool in framework repo

    Given the project is the purlin framework repository (not a submodule consumer)
    And the user runs "/pl-toolbox delete purlin.verify_zero_queue"
    When the skill resolves the tool
    Then a dry-run preview is shown and the user is asked to confirm

#### Scenario: Run tool with no instructions or code

    Given a tool exists with both code and agent_instructions set to null
    When the user runs "/pl-toolbox run <tool>"
    Then an error is displayed: "Tool '<id>' has no instructions or code to execute."

### Manual Scenarios (Human Verification Required)

None.
