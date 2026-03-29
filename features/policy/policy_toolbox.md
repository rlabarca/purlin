# Policy: Agentic Toolbox

> Label: "Policy: Agentic Toolbox"
> Category: "Policy"

## 1. Purpose

This policy establishes the governance rules and invariants for the Purlin Agentic Toolbox system. The toolbox is a collection of agent-executable tools organized in three categories — Purlin, Project, and Community — that can be run at any time, in any order. All features that implement toolbox functionality anchor here.

This policy replaces `policy_release.md`. The "release checklist" concept is retired; tools are independent and run individually via `purlin:toolbox run`.

## 2. Invariants

### 2.1 Tool ID Namespacing
*   All toolbox tool IDs MUST be unique across the Purlin, Project, and Community namespaces within a given project.
*   Purlin tool IDs MUST use the `purlin.` prefix. This namespace is reserved exclusively for tools defined in Purlin's own `scripts/toolbox/purlin_tools.json`.
*   Community tool IDs MUST use the `community.` prefix. This namespace is reserved for tools installed from external git repositories.
*   Project tool IDs MUST NOT use the `purlin.` or `community.` prefix. Consumer projects SHOULD use a short project-specific namespace (e.g., `myproject.deploy_staging`) or a plain name (e.g., `deploy_staging`).
*   Attempting to define a project tool with a `purlin.` or `community.` ID is an error; the tooling MUST reject it with a clear message explaining the reserved prefix.

### 2.2 Immutability of Purlin Tools in Consumer Projects
*   Consumer projects MUST NOT modify `scripts/toolbox/purlin_tools.json`. In a submodule deployment, this file resides inside the submodule directory and is subject to the Submodule Immutability Mandate.
*   Only Purlin's own PM agent modifies purlin tools. Consumer-project agents create and manage project and community tools exclusively.
*   To customize a purlin tool, users copy it to the project category via `purlin:toolbox copy`, which creates an editable project tool with a new (non-reserved) ID.

### 2.3 Tool Availability
*   All tools that exist in any of the three registries are available for execution. There is no enable/disable mechanism.
*   To remove a project or community tool, use `purlin:toolbox delete`. Purlin tools cannot be deleted — they are distributed with the framework.
*   If a project tool has the same base name (after stripping the `purlin.` prefix) as a purlin tool, the project tool shadows the purlin tool for `purlin:toolbox run`. Both remain visible in `purlin:toolbox list`.

### 2.4 Community Tool Integrity
*   Each community tool is stored in its own directory under `.purlin/toolbox/community/<tool_id>/`.
*   Community tools MUST track `source_repo` (git URL), `version` (semver), and `author` (email) in the community registry.
*   Local edits to a community tool create a divergence from upstream. The next `purlin:toolbox pull` detects the divergence and offers resolution options — it never silently overwrites local changes.
*   Single tool per repository: each community tool source repo contains exactly one `tool.json` at its root.

### 2.5 Forward Compatibility
*   The tool schema supports unrecognized fields. Tooling MUST ignore unrecognized fields with a warning, never an error.
*   Old-format tool definitions (without `version` or `metadata` fields) are valid. Missing new fields default to `null`.
*   The `schema_version` field in registry files enables format detection. Absence of `schema_version` indicates legacy format (pre-toolbox).

### 2.6 PM Ownership
*   The `.purlin/toolbox/` directory (`project_tools.json`, `community_tools.json`, and `community/` subdirectories) is PM-owned.
*   Engineer mode executes tools via `purlin:toolbox run` but does not modify tool registries.
*   QA mode can run tools for verification but does not modify tool registries.

### 2.7 Self-Contained Prerequisite Setup
*   Tools that depend on external services, MCP servers, or CLI utilities MUST auto-configure those prerequisites programmatically when they are missing. The agent MUST NOT ask the user to run CLI commands or perform manual setup steps.
*   When a configured MCP server is not loaded in the current session, the agent MUST direct the user to type `/mcp` in Claude Code, select the relevant MCP server, and authenticate.
*   Credentials and secrets are the sole exception: the agent MUST ask the user for secret values (never guess or generate them), but MUST write the resulting config files automatically.
*   Tool `agent_instructions` encode the complete setup procedure. If a tool's prerequisites change, the `agent_instructions` MUST be updated to reflect the new auto-configuration flow.

### 2.8 Destructive Operation Safety
*   All destructive operations (`delete`, `push`, and `pull` when overwriting local edits) MUST show a dry-run preview before executing. The user confirms or cancels.
*   No `--force` flag exists. The preview-then-confirm flow is always enforced.

## 3. FORBIDDEN Patterns

*   `purlin.` prefix in project tool IDs (Invariant 2.1). Pattern: `"id"\s*:\s*"purlin\.[^"]*"` in `.purlin/toolbox/project_tools.json`.
*   `community.` prefix in project tool IDs (Invariant 2.1). Pattern: `"id"\s*:\s*"community\.[^"]*"` in `.purlin/toolbox/project_tools.json`.
*   Direct modification of `scripts/toolbox/purlin_tools.json` in consumer projects (Invariant 2.2).
*   Silent overwrite of locally-edited community tools during `pull` (Invariant 2.4).

## Scenarios

No automated or manual scenarios. This is a policy anchor node — its "scenarios" are
process invariants enforced by instruction files and tooling.
