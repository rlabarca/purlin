# Feature: Agentic Toolbox — Core Data Model

> Label: "Tool: Agentic Toolbox Core"
> Category: "Install, Update & Scripts"
> Owner: PM
> Prerequisite: features/policy_toolbox.md

## 1. Overview

This feature defines the data model, file formats, tool schema, registry formats, and resolution algorithm for the Purlin Agentic Toolbox system. The toolbox replaces the release checklist system with a general-purpose collection of agent-executable tools organized in three categories: Purlin (framework-distributed), Project (consumer-specific), and Community (shared via git repos).

Tools are independent — they can be run at any time, in any order, individually or in batches. There is no ordering, sequencing, or enable/disable layer.

---

## 2. Requirements

### 2.1 Tool Schema

Each tool (whether Purlin, Project, or Community) is a JSON object conforming to the following schema:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier. Purlin tools prefix with `purlin.`; community tools prefix with `community.`; project tools use a plain name. |
| `friendly_name` | string | Yes | Human-readable display name shown in agent output. |
| `description` | string | Yes | Prose explanation of what this tool does and why it exists. |
| `code` | string or null | No | Shell command or script path for automated execution. `null` indicates agent-only execution via `agent_instructions`. |
| `agent_instructions` | string or null | No | Natural language instructions for the agent when executing this tool. `null` if no agent-specific guidance is needed. |
| `tags` | string[] | No | Free-form labels for filtering and grouping (e.g., `["release", "audit"]`). Defaults to `[]` when absent. Not validated — any string is accepted. |
| `version` | string or null | No | Semver version string. Required for community tools. Purlin tools version with the framework. Project tools are unversioned (`null`). |
| `metadata` | object or null | No | Extended metadata. Tooling MUST ignore unrecognized keys within metadata (forward-compatible). |
| `metadata.author` | string or null | No | Email address of the tool author. Required for community tools, optional for project tools, null for purlin tools. |
| `metadata.source_repo` | string or null | No | Git URL of the source repository. Required for community tools. Set during `/pl-toolbox add` or `/pl-toolbox push`. |
| `metadata.last_updated` | string or null | No | ISO 8601 date string. Auto-set on create, edit, or pull. |

No additional top-level fields are required by the schema at this time. Tooling MUST ignore unrecognized fields with a warning, not an error (forward compatibility).

### 2.2 Purlin Tools Registry

*   **Path:** `<tools_root>/toolbox/purlin_tools.json` (resolved via `tools_root` in `.purlin/config.json`; default `tools/toolbox/purlin_tools.json`).
*   **Format:**
    ```json
    {
      "schema_version": "2.0",
      "tools": [ <tool-object>, ... ]
    }
    ```
*   **Immutability:** Consumer projects MUST NOT modify this file. See `policy_toolbox.md` Invariant 2.2.
*   **Read access:** The toolbox resolver reads this file on every invocation. It is never cached beyond the duration of a single tool invocation.

### 2.3 Project Tools Registry

*   **Path:** `.purlin/toolbox/project_tools.json`
*   **Format:**
    ```json
    {
      "schema_version": "2.0",
      "tools": [ <tool-object>, ... ]
    }
    ```
*   **Ownership:** PM-owned. PM mode agent creates and maintains this file.
*   **Absence:** If the file does not exist, it is treated as an empty tools array (`{"schema_version": "2.0", "tools": []}`). The system MUST NOT error when this file is absent.
*   **ID constraint:** Tool IDs MUST NOT use the `purlin.` or `community.` prefix. The tooling MUST reject creation of such tools with a clear error message.

### 2.4 Community Tools Registry

*   **Path:** `.purlin/toolbox/community_tools.json`
*   **Format:** This is an index file. Full tool definitions live in per-tool directories.
    ```json
    {
      "schema_version": "2.0",
      "tools": [
        {
          "id": "community.deploy_vercel",
          "source_dir": "community/deploy_vercel",
          "version": "1.2.0",
          "source_repo": "git@github.com:user/purlin-tool-deploy-vercel.git",
          "author": "user@example.com",
          "last_pull_sha": "abc123f"
        }
      ]
    }
    ```
*   **Per-tool directory:** `.purlin/toolbox/community/<tool_id>/tool.json` contains the full tool definition conforming to the tool schema (Section 2.1).
*   **Ownership:** PM-owned.
*   **Absence:** Treated as empty tools array. System MUST NOT error.

### 2.5 Resolution Algorithm

The resolver merges three sources into a unified tool list.

**Function signature:** `resolve_toolbox(purlin_path, project_path, community_path) → (resolved_tools, warnings, errors)`

**Steps:**

1. **Load purlin tools** from `<tools_root>/toolbox/purlin_tools.json`. Assign `category: "purlin"` to each.
2. **Load project tools** from `.purlin/toolbox/project_tools.json`. Validate IDs do not use reserved prefixes (`purlin.`, `community.`). Assign `category: "project"`.
3. **Load community tools** from `.purlin/toolbox/community_tools.json`. For each entry, read the full definition from `.purlin/toolbox/community/<tool_id>/tool.json`. Assign `category: "community"`.
4. **Build merged registry** keyed by ID. All IDs must be unique across all three sources:
    *   Collision between project and purlin (same base name after stripping `purlin.`): both exist in the resolved list. The project tool shadows the purlin tool for `run` operations (fuzzy matching prefers project). Both appear in `list`.
    *   Collision between project and community on exact ID: error.
    *   Purlin and community never collide (different namespace prefixes).
5. **Return resolved list** with all tools, their categories, and all schema fields.

**Error handling:**
*   Corrupt JSON in any registry file: hard error. `"Error: <path> contains invalid JSON."` The resolver does not attempt partial loading.
*   Missing registry files: treated as empty (not an error).
*   Unrecognized fields in tool objects: warning, fields are preserved in output.

### 2.6 Fuzzy Matching

All subcommands that accept a tool name support fuzzy matching against both IDs and friendly names.

*   Exact ID match always wins.
*   If no exact match: substring match against IDs and friendly names (case-insensitive).
*   If multiple matches: show all candidates and ask the user to pick.
*   If no matches: `"No tool matching '<query>'. Run /pl-toolbox list to see available tools."`

### 2.7 File Layout

```
tools/toolbox/
  purlin_tools.json           # Framework-distributed tool registry
  resolve.py                  # Resolution algorithm
  manage.py                   # CLI tool management
  audit_common.py             # Shared audit output format
  verify_zero_queue.py        # Audit scripts (moved from tools/release/)
  verify_dependency_integrity.py
  instruction_audit.py
  doc_consistency_check.py
  submodule_safety_audit.py
  test_toolbox.py             # Tests (colocated per project convention)
  test_manage.py
  test_toolbox_audit.py

.purlin/toolbox/
  project_tools.json          # Project-specific tool registry
  community_tools.json        # Community tool index
  community/                  # Community tool content
    <tool_id>/
      tool.json               # Full tool definition
      README.md               # Optional documentation
```

### 2.8 Backward Compatibility with Release Steps

The old release steps schema (`{"steps": [...]}` in `global_steps.json` and `local_steps.json`) is structurally compatible with the new tool schema. The only changes are:
*   Top-level key renamed from `"steps"` to `"tools"`.
*   `"schema_version": "2.0"` added.
*   New optional fields (`tags`, `version`, `metadata`) added.

The resolver detects old-format files by the absence of `schema_version` and the presence of a `"steps"` key (instead of `"tools"`). It reads old-format files transparently, treating `"steps"` as `"tools"`.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Resolution with all three sources populated

    Given purlin_tools.json contains 3 tools with "purlin." prefix
    And project_tools.json contains 2 tools with plain names
    And community_tools.json contains 1 tool with "community." prefix
    When the resolver runs
    Then the resolved list contains 6 tools
    And each tool has a "category" field matching its source

#### Scenario: Empty registries produce empty result

    Given purlin_tools.json has an empty tools array
    And project_tools.json does not exist
    And community_tools.json does not exist
    When the resolver runs
    Then the resolved list is empty
    And there are no warnings or errors

#### Scenario: Project tool with reserved prefix is rejected

    Given project_tools.json contains a tool with id "purlin.my_tool"
    When the resolver runs
    Then an error is returned: "purlin. prefix is reserved"
    And the resolved list is empty

#### Scenario: Community prefix in project tool is rejected

    Given project_tools.json contains a tool with id "community.my_tool"
    When the resolver runs
    Then an error is returned: "community. prefix is reserved"

#### Scenario: Old-format file is read transparently

    Given a registry file has key "steps" instead of "tools" and no "schema_version"
    When the resolver loads this file
    Then it treats "steps" as "tools"
    And no error is raised

#### Scenario: Unrecognized fields are preserved with warning

    Given a tool object contains a field "custom_field" not in the schema
    When the resolver loads this tool
    Then the field is preserved in the resolved output
    And a warning is logged

#### Scenario: Corrupt JSON in registry file

    Given purlin_tools.json contains invalid JSON
    When the resolver runs
    Then a hard error is returned with the file path

#### Scenario: Fuzzy match on partial ID

    Given a tool exists with id "purlin.verify_zero_queue"
    When the user runs "/pl-toolbox run zero"
    Then the tool "purlin.verify_zero_queue" is matched

#### Scenario: Fuzzy match on friendly name

    Given a tool exists with friendly_name "Refresh Documentation"
    When the user runs "/pl-toolbox run docs"
    Then the tool is matched

#### Scenario: Ambiguous fuzzy match shows candidates

    Given tools exist with ids "purlin.doc_consistency_check" and "doc_consistency_framework"
    When the user runs "/pl-toolbox run doc"
    Then both tools are shown as candidates
    And the user is asked to pick

#### Scenario: Project tool shadows purlin tool

    Given purlin_tools.json contains a tool with id "purlin.verify_zero_queue"
    And project_tools.json contains a tool with id "verify_zero_queue"
    When the user runs "/pl-toolbox run verify_zero_queue"
    Then the project tool executes (not the purlin tool)
    And "/pl-toolbox list" shows both tools

### Manual Scenarios (Human Verification Required)

None.
