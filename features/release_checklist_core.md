# Feature: Release Checklist — Core Data Model

> Label: "Release Checklist: Core Data Model"
> Category: "Release Process"
> Prerequisite: features/policy_release.md

## 1. Overview

This feature defines the data model, file formats, step schema, global step definitions, and auto-discovery protocol for the Purlin release checklist system. It is the foundation on which the CDD Dashboard UI and agent-facing tooling build.

## 2. Requirements

### 2.1 Step Schema

Each release step (whether global or local) is a JSON object conforming to the following schema:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier. Global steps prefix with `purlin.`; local steps use a project-defined name. |
| `friendly_name` | string | Yes | Human-readable display name shown in the CDD Dashboard and agent output. |
| `description` | string | Yes | Prose explanation of what this step does and why it exists in the release process. |
| `code` | string or null | No | Shell command or script path for automated execution of this step. `null` indicates no automation is available. |
| `agent_instructions` | string or null | No | Natural language instructions for the Architect agent when executing this step. `null` if no agent-specific guidance is needed. |

No additional fields are permitted in the schema at this time. Tooling MUST ignore unrecognized fields with a warning, not an error (forward compatibility).

### 2.2 Global Steps Storage

*   **Path:** `<tools_root>/release/global_steps.json` (resolved via `tools_root` in `.agentic_devops/config.json`; default `tools/release/global_steps.json`).
*   **Format:** `{"steps": [ <step-object>, ... ]}`
*   **Immutability:** Consumer projects MUST NOT modify this file. See `policy_release.md` Invariant 2.2.
*   **Read access:** The CDD dashboard server and CLI tooling read this file on every checklist load. It is never cached beyond the duration of a single tool invocation.

### 2.3 Local Steps Storage

*   **Path:** `.agentic_devops/release/local_steps.json`
*   **Format:** `{"steps": [ <step-object>, ... ]}`
*   **Ownership:** Architect-owned. The Architect agent creates and maintains this file.
*   **Absence:** If the file does not exist, it is treated as an empty steps array (`{"steps": []}`). The system MUST NOT error when this file is absent.

### 2.4 Local Config (Ordering and Enable/Disable State)

*   **Path:** `.agentic_devops/release/config.json`
*   **Format:**
    ```json
    {
      "steps": [
        {"id": "purlin.record_version_notes", "enabled": true},
        {"id": "purlin.verify_zero_queue", "enabled": true},
        {"id": "purlin.verify_dependency_integrity", "enabled": true},
        {"id": "purlin.sync_evolution", "enabled": true},
        {"id": "purlin.instruction_audit", "enabled": true},
        {"id": "purlin.doc_consistency_check", "enabled": true},
        {"id": "purlin.mark_release_complete", "enabled": true},
        {"id": "purlin.push_to_remote", "enabled": true}
      ]
    }
    ```
*   **Semantics:** Defines the ordered, authoritative sequence of all steps for this project's release process. Each entry references a step by ID (global or local). Steps not listed here are excluded from the release process (unless auto-discovered; see Section 2.5).
*   **Ownership:** Architect-owned. The CDD Dashboard MAY write updates to this file when the user reorders or toggles steps via the UI.
*   **Absence:** If the file does not exist, the system auto-generates the default config by applying Section 2.5 auto-discovery to all known steps.

### 2.5 Auto-Discovery of New Global Steps

When the tooling loads the release checklist, it MUST apply the following resolution algorithm:

1.  Load all step definitions from `global_steps.json` (or treat as empty if absent).
2.  Load all step definitions from `local_steps.json` (or treat as empty if absent).
3.  Build a merged registry: `{ <id>: <step-object>, ... }` for all known steps.
4.  Load the ordered list from `config.json` (or treat as empty if absent).
5.  Identify **new steps**: any step ID in the registry that does not appear in the config.
6.  Append each new step to the end of the config with `enabled: true`, in their declaration order (global steps first, then local).
7.  Identify **orphaned entries**: any ID in the config that does not appear in the registry. Log a warning for each and skip it in the resolved output. Do NOT remove orphaned entries from the on-disk config (preserve manual config for forward compatibility).
8.  Return the fully resolved, ordered list of steps for this checklist load.

### 2.6 Local Step ID Validation

When a local step is loaded from `local_steps.json`, the tooling MUST validate that its `id` field does not begin with `purlin.`. If a violation is found, an error MUST be raised and that step MUST be excluded from the resolved list. A clear error message identifying the offending step MUST be emitted.

### 2.7 Initial Global Steps

The following 8 steps are defined in `tools/release/global_steps.json`:

| # | ID | Friendly Name |
|---|-----|--------------|
| 1 | `purlin.record_version_notes` | Record Version & Release Notes |
| 2 | `purlin.verify_zero_queue` | Verify Zero-Queue Status |
| 3 | `purlin.verify_dependency_integrity` | Verify Dependency Integrity |
| 4 | `purlin.sync_evolution` | Sync Evolution Documentation |
| 5 | `purlin.instruction_audit` | Instruction Audit |
| 6 | `purlin.doc_consistency_check` | Documentation Consistency Check |
| 7 | `purlin.mark_release_complete` | Mark Release Specification Complete |
| 8 | `purlin.push_to_remote` | Push to Remote Repository |

**Step Definitions:**

**`purlin.record_version_notes`**
- Description: "Prompts for a version number and release notes, then records them in the README.md under a '## Release Notes' section as a new dated entry."
- Code: null
- Agent Instructions: "Ask the user for the version number (e.g., 'v1.2.0') and release notes (a brief summary of what changed). Then insert a new entry into the project's README.md under a '## Release Notes' heading (creating the heading if absent). Format the entry as: `### <version> — <YYYY-MM-DD>\n\n<release notes text>`."

**`purlin.verify_zero_queue`**
- Description: "Verifies that all features are in a fully satisfied state by checking that every feature has architect: 'DONE', builder: 'DONE', and qa is 'CLEAN' or 'N/A'."
- Code: null
- Agent Instructions: "Run `tools/cdd/status.sh` and confirm that every entry in the `features` array has `architect: \"DONE\"`, `builder: \"DONE\"`, and `qa` is either `\"CLEAN\"` or `\"N/A\"`. If any feature fails this check, halt the release and report which features are not ready."

**`purlin.verify_dependency_integrity`**
- Description: "Verifies that the dependency graph is acyclic and all prerequisite links are valid."
- Code: null
- Agent Instructions: "Read `.agentic_devops/cache/dependency_graph.json`. Confirm the graph is acyclic and all prerequisite references resolve to existing feature files. If the file is stale or missing, run `tools/cdd/status.sh --graph` to regenerate it. Report any cycles or broken links."

**`purlin.sync_evolution`**
- Description: "Updates the 'Agentic Evolution' table in README.md based on PROCESS_HISTORY.md and verifies documentation is in sync."
- Code: null
- Agent Instructions: "Read PROCESS_HISTORY.md and verify the 'Agentic Evolution' table in README.md reflects all recent entries. Add or update entries as needed. Commit any changes."

**`purlin.instruction_audit`**
- Description: "Verifies that `.agentic_devops/` override files are consistent with the base instruction layer and do not introduce contradictions."
- Code: null
- Agent Instructions: "Check `.agentic_devops/HOW_WE_WORK_OVERRIDES.md`, `.agentic_devops/ARCHITECT_OVERRIDES.md`, `.agentic_devops/BUILDER_OVERRIDES.md`, and `.agentic_devops/QA_OVERRIDES.md` for rules that directly contradict the base instruction files. Check for stale path references and terminology mismatches. Fix any inconsistencies and commit."

**`purlin.doc_consistency_check`**
- Description: "Checks that README.md and project documentation accurately reflects the current feature set, with no stale descriptions, removed functionality references, or version mismatches."
- Code: null
- Agent Instructions: "Check that README.md and any project documentation (in `docs/` or equivalent) accurately reflects the current feature set. Look for: outdated feature descriptions, references to removed functionality, stale file paths, and version numbers inconsistent with the current release. Cross-check with the `features/` directory to confirm documented behavior matches specified behavior. Fix any inconsistencies and commit."

**`purlin.mark_release_complete`**
- Description: "Marks the active release specification file with the [Complete] status tag."
- Code: null
- Agent Instructions: "Open the active release feature file in `features/`. Add the `[Complete]` status tag to the file's status field. Commit the change."

**`purlin.push_to_remote`**
- Description: "Pushes the release commits and any tags to the remote repository (e.g., GitHub). This step can be disabled for air-gapped projects or when a separate CI/CD pipeline handles delivery."
- Code: "git push && git push --tags"
- Agent Instructions: "Confirm the current branch and remote configuration, then push commits and tags to the remote repository. Warn the user if they are about to force-push or if the remote is ahead. Do not proceed without explicit user confirmation for force-push scenarios."

### 2.8 Purlin-Local Release Steps

The following steps are defined in Purlin's `.agentic_devops/release/local_steps.json`. They are specific to the Purlin framework repository and do NOT appear in consumer project checklists.

**`doc_consistency_framework`**
- Friendly Name: "Framework Documentation Consistency"
- Description: "Verifies that Purlin instruction files are internally consistent with each other and with the framework's README and PROCESS_HISTORY. Purlin-specific: consumer projects do not own instruction files."
- Code: null
- Agent Instructions: "Cross-reference `instructions/HOW_WE_WORK_BASE.md`, `instructions/ARCHITECT_BASE.md`, `instructions/BUILDER_BASE.md`, `instructions/QA_BASE.md`, and `features/policy_critic.md`. Check for: direct contradictions between files, stale file path references, terminology mismatches, and lifecycle/protocol definitions that differ between the shared philosophy and role-specific instructions. Also verify that README.md and PROCESS_HISTORY.md are consistent with the current instruction file content. Fix any inconsistencies and commit."

This step is positioned in Purlin's `.agentic_devops/release/config.json` immediately after `purlin.instruction_audit`, so both override-consistency and instruction-internal-consistency checks run together before the final release steps.

## 3. Scenarios

### Automated Scenarios

#### Scenario: Full resolution with defaults
Given `global_steps.json` contains 8 step definitions and `local_steps.json` is absent or empty, and `config.json` is absent,
When the checklist is loaded,
Then the resolved list contains exactly 8 steps in their declared order from `global_steps.json`,
And all steps have `enabled: true`.

#### Scenario: Disabled step preserved
Given a local `config.json` with `purlin.push_to_remote` set to `enabled: false`,
When the checklist is loaded,
Then the resolved list includes `purlin.push_to_remote`,
And that step's `enabled` field is `false`.

#### Scenario: Auto-discovery appends new global step
Given a `config.json` listing 7 of the 8 global steps (omitting `purlin.push_to_remote`),
When the checklist is loaded,
Then `purlin.push_to_remote` is appended to the end of the resolved list with `enabled: true`.

#### Scenario: Orphaned config entry skipped with warning
Given a `config.json` containing an entry with `id: "purlin.nonexistent_step"` that does not correspond to any step in `global_steps.json` or `local_steps.json`,
When the checklist is loaded,
Then that entry is absent from the resolved list,
And a warning is logged identifying `purlin.nonexistent_step` as an unknown step ID.

#### Scenario: Local step with reserved prefix rejected
Given a `local_steps.json` containing a step with `id: "purlin.custom_deploy"`,
When the checklist is loaded,
Then an error is raised identifying `purlin.custom_deploy` as using the reserved `purlin.` prefix,
And that step is excluded from the resolved list.

### Manual Scenarios (Human Verification Required)
None. All scenarios for this feature are fully automated (unit tests against the data loading and resolution logic).

## Implementation Notes

*   The auto-discovery algorithm in Section 2.5 is designed to be idempotent: running it multiple times against the same inputs produces the same result.
*   The Builder MUST create `tools/release/global_steps.json` with the 8 step definitions from Section 2.7. The exact JSON structure follows the schema in Section 2.1.
*   The `code` field for `purlin.push_to_remote` is the only step with a non-null `code` value in the initial set. The other steps require agent judgment or interactive verification and cannot be safely automated with a single shell command.
*   There are no Manual Scenarios for this feature. Verification is entirely automated (unit tests against the data loading and resolution logic).
