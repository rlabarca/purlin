# Purlin Process History (Core Framework)

This log tracks the evolution of the **Purlin** framework itself. This repository serves as the project-agnostic engine for Continuous Design-Driven AI workflows.

## [2026-02-22] Override Instruction Management Formalization

- **Problem:** No formal protocol governed which agent could edit which override file, no tooling detected contradictions between overrides and base files, and no safe mechanism existed for Purlin-framework-level base file edits.
- **Solution:** Three new slash commands + instruction file updates across all role BASE files + spec update to bootstrap distribution.
    - `pl-override-edit` — role-scoped guided override edit with conflict pre-scan and commit
    - `pl-override-conflicts` — shared soft-check analysis (CONFLICT / WARNING / INFO)
    - `pl-edit-base` — Purlin-local only; guided base file modification with mandatory PROCESS_HISTORY.md entry
- **Files changed:** `HOW_WE_WORK_BASE.md` (new Override Management Protocol subsection), `ARCHITECT_BASE.md`, `BUILDER_BASE.md`, `QA_BASE.md` (soft checks, override write access, authorized commands), `features/submodule_bootstrap.md` Section 2.18 (exclusion rule — Builder to implement in bootstrap.sh and sync_upstream.sh), `features/submodule_sync.md` Section 2.6 (same exclusion rule), 3 new `.claude/commands/pl-*.md` files.

## [2026-02-22] Slash Command Distribution via Bootstrap + Sync

- **Scope:** New `.claude/commands/` command files, spec additions to `submodule_bootstrap.md` and `submodule_sync.md`, startup print sequence + authorized commands sections added to all three role instruction files, and corresponding script implementations in `bootstrap.sh` and `sync_upstream.sh`.
- **Problem:** The `/pl-*` commands documented in `README.md` and `features/cdd_startup_controls.md` were vocabulary notation only — no `.claude/commands/` files existed anywhere in the project. Claude Code had no awareness of them. Consumer projects receiving Purlin via submodule had no mechanism to get command files distributed or kept up to date.
- **Solution:** Three-part implementation.
    1. **Command file definitions:** Created `.claude/commands/` with 14 `pl-*.md` files. Shared commands (`/pl-status`, `/pl-find`) have no role gate. Role-owned commands (Architect: `/pl-spec`, `/pl-anchor`, `/pl-tombstone`, `/pl-release-check`; Builder: `/pl-build`, `/pl-delivery-plan`, `/pl-infeasible`, `/pl-propose`; QA: `/pl-verify`, `/pl-discovery`, `/pl-complete`, `/pl-qa-report`) open with an owner declaration and a refusal instruction for other roles.
    2. **Instruction file updates:** Added startup print sequence (always-on command vocabulary table, section 5.0/2.0/3.0 in each role's startup protocol) and authorized commands list with role prohibition to `ARCHITECT_BASE.md`, `BUILDER_BASE.md`, and `QA_BASE.md`.
    3. **Distribution mechanism:** Bootstrap (Section 2.18) copies command files to `<project>/.claude/commands/` at init time, skipping consumer-modified files. Sync (Section 2.6) diffs command files between SHAs: auto-copies unmodified changed files, warns on locally modified files, reports new commands added and deleted commands to clean up.
- **Changes:**
    - `.claude/commands/` — 14 new command definition files.
    - `instructions/ARCHITECT_BASE.md` — Section 5.0 (startup print sequence), Section 9 (authorized commands + prohibition).
    - `instructions/BUILDER_BASE.md` — Section 2.0 (startup print sequence), Section 9 (authorized commands + prohibition).
    - `instructions/QA_BASE.md` — Section 3.0 (startup print sequence), Section 8 (authorized commands + prohibition).
    - `features/submodule_bootstrap.md` — Section 2.18 (command file distribution), 3 new automated scenarios.
    - `features/submodule_sync.md` — Section 2.6 (command file sync), 4 new automated scenarios.
    - `tools/bootstrap.sh` — Section 5b (command file copy loop with skip-if-newer guard).
    - `tools/sync_upstream.sh` — Section 3b (command file sync with SHA-based modification detection).

## [2026-02-22] CDD Startup Controls Feature Spec

- **Scope:** New feature spec only (Builder implements config/launcher/dashboard; Architect updates instruction files separately).
- **Problem:** The agreed design for `startup_sequence` and `recommend_next_actions` config flags (recorded as a design note in PROCESS_HISTORY.md earlier today) had no feature spec. Without a spec, the Builder cannot implement and the Architect has no formal artifact to drive instruction file changes.
- **Solution:** Added `features/cdd_startup_controls.md` formalizing the full feature. The spec covers: config schema (two new booleans per agent, defaults `true`, invalid combination rejection), startup print sequence (always-on command vocabulary table, instruction-file-driven, not configurable), conditional startup behavior (four valid state combinations with defined agent behaviors), launcher validation (exits non-zero on invalid combo), dashboard toggle controls (two checkboxes per agent row in the Models section, constraint enforcement between them), and API extension (`POST /config/agents` validates new fields). Ownership boundary is explicit in Implementation Notes: config/launcher/dashboard changes go to Builder; instruction file changes (`ARCHITECT_BASE.md`, `BUILDER_BASE.md`, `QA_BASE.md`) are Architect-owned companion work.
- **Changes:**
    - **features/cdd_startup_controls.md:** New feature spec.

## [2026-02-22] README Agent Reference Section + CDD Startup Controls Design Record

- **Scope:** README documentation update and design record only (no instruction files, no tool code affected).
- **Problem 1:** The README described agent roles abstractly but gave users no operational reference for what to ask each agent. New and returning users had no command vocabulary or workflow examples to get started.
- **Problem 2:** The design for per-agent startup control flags (`startup_sequence`, `recommend_next_actions`) was agreed in discussion but not recorded anywhere. Without a design record, the spec would need to be reconstructed from scratch before the Builder could implement it.
- **Solution 1 (README Agent Reference):** Added a new `## The Agents` section to `README.md` between `## Core Concepts` and `## Setup & Configuration`. The section contains: a Shared Commands table (`/pl-status`, `/pl-find`); per-agent subsections for Architect, Builder, and QA Agent -- each with a role description, command vocabulary table, and two workflow examples. Command tables surface: `/pl-spec`, `/pl-anchor`, `/pl-tombstone`, `/pl-release-check` (Architect); `/pl-build`, `/pl-delivery-plan`, `/pl-infeasible`, `/pl-propose` (Builder); `/pl-verify`, `/pl-discovery`, `/pl-complete`, `/pl-qa-report` (QA).
- **Solution 2 (Design Record):** The CDD startup controls design is recorded here for future Builder spec authorship. Two new boolean flags per agent in `config.json`: `startup_sequence` (agent runs CDD orientation on launch) and `recommend_next_actions` (agent presents prioritized work plan after orientation). Valid combinations: `true/true` (full guided session, default); `true/false` (agent orients, then awaits direction); `false/false` (expert mode, print commands and await instruction); `false/true` (invalid -- rejected). A startup print sequence (agent name + command table) runs unconditionally regardless of flag state. Dashboard surface: two checkboxes in the Agent Configuration section alongside provider/model selectors. Implementation scope (for future Builder spec): `config.json` schema, agent instruction conditionals, dashboard toggle UI, `agentic_devops.sample/config.json` defaults.
- **Changes:**
    - **README.md:** `## The Agents` section added between `## Core Concepts` and `## Setup & Configuration`.
    - **PROCESS_HISTORY.md:** This entry.

## [2026-02-22] Removed Chat Delegation Prompts + Introduced Tombstone Protocol

- **Scope:** Instruction file changes only (no feature specs or tool code affected).
- **Problem 1:** The Architect's startup protocol and Section 2 (ZERO CODE MANDATE) allowed and encouraged producing chat-based "delegation prompts" for the Builder. This contradicted the "feature files as single source of truth" principle — Builder work items described only in chat are not discoverable from project artifacts and break the self-directing startup protocol.
- **Problem 2:** The existing guidance to delete a feature file when retiring a feature left the Builder with no instruction about which code to remove. The feature file -- the Builder's only input -- is gone.
- **Solution 1 (No Chat Delegation):** Added a new `### NO CHAT-BASED DELEGATION MANDATE` in `instructions/ARCHITECT_BASE.md` Section 2. Removed the "provide a Builder delegation prompt" clause from the ZERO CODE MANDATE last bullet. Removed the "Delegate to Builder" option from Responsibility 13 (Untracked File Triage). Removed item 4 (Delegation Prompts) from Section 5.2 Work Plan presentation.
- **Solution 2 (Tombstone Protocol):** Added `### Feature Retirement (Tombstone Protocol)` to `instructions/ARCHITECT_BASE.md` Section 7. The protocol requires the Architect to write a `features/tombstones/<feature_name>.md` file (canonical format: files to delete, dependencies to check, context) before deleting the feature file, committing both together. Added a Tombstone Check as step 6 to `instructions/BUILDER_BASE.md` Section 2.1, tombstone items at the top of the Builder work plan, and a new `## 4. Tombstone Processing` section (before regular feature work). Old sections 4–7 renumbered to 5–8.
- **Changes:**
    - **instructions/ARCHITECT_BASE.md:** NO CHAT-BASED DELEGATION MANDATE added; ZERO CODE MANDATE last bullet updated; Responsibility 13 "Delegate to Builder" option removed; Section 5.2 item 4 (Delegation Prompts) removed; Tombstone Protocol added to Section 7.
    - **instructions/BUILDER_BASE.md:** Tombstone Check added as startup step 6; work plan action items updated to list tombstones first; new Section 4 (Tombstone Processing) added; old sections 4–7 renumbered to 5–8; stale cross-reference in 2.2.0 corrected from "step 2.1.6" to "step 2.1.5".

## [2026-02-22] Removed `purlin.run_tool_tests` Release Step

- **Scope:** Spec update and JSON file changes (Builder-implemented).
- **Problem:** `purlin.run_tool_tests` had two overlapping issues: (1) Purlin-internal language ("Purlin DevOps tool test suite") that is meaningless to consumer projects, and (2) architectural redundancy — per HOW_WE_WORK_BASE Section 8.1, `Builder: DONE` already guarantees automated tests passed; `verify_zero_queue` (Step 2) confirms this for every feature. Running a separate test-discovery step afterward double-checks a guarantee the CDD model already provides.
- **Solution:** Remove `purlin.run_tool_tests` from the global release steps entirely. The release checklist reduces from 9 to 8 global steps. The "environmental regression" counterargument (tests passed then but not now) is a CI/CD concern, not an agent release checklist concern.
- **Changes:**
    - **features/release_checklist_core.md:** Section 2.4 config example, Section 2.7 table and step definitions, "Full resolution with defaults" scenario, and Implementation Notes all updated from 9 to 8 steps; `purlin.run_tool_tests` entry removed.
    - **tools/release/global_steps.json:** `purlin.run_tool_tests` step object removed (Builder-delegated).
    - **.agentic_devops/release/config.json:** `{"id": "purlin.run_tool_tests", "enabled": true}` entry removed (Builder-delegated).
    - **Unit tests for `release_checklist_core`:** Builder must update the "Full resolution with defaults" test to expect 8 steps.

## [2026-02-21] Cosmetic First-Pass Guard

- **Scope:** Spec gap fix and code correction; no new features.
- **Problem:** `compute_regression_set()` in `tools/critic/critic.py` applied cosmetic scope suppression unconditionally when `[Scope: cosmetic]` was found in the most recent status commit. This caused the QA Agent to skip first-time verification for features that had never passed QA (`role_status.qa = "TODO"`). The root cause was a spec gap: neither `features/critic_tool.md` Section 2.12 nor `features/policy_critic.md` Section 2.8 defined a precondition requiring a prior clean QA pass before cosmetic suppression could apply.
- **Solution:**
    - `features/policy_critic.md` Section 2.8: Added **Cosmetic First-Pass Guard** paragraph specifying that cosmetic scope may only suppress verification when the prior on-disk `tests/<feature>/critic.json` shows `role_status.qa == "CLEAN"`. When no prior clean pass exists, the Critic must escalate to `full` and append a `cross_validation_warning`.
    - `features/critic_tool.md` Section 2.12: Updated `cosmetic` bullet to include the First-Pass Guard requirement. Updated the "Regression Scope Cosmetic" scenario to add the prior-CLEAN precondition. Added new scenario "Cosmetic Scope Does Not Skip First-Time Verification".
    - `tools/critic/critic.py`: Added `_get_previous_qa_status()` helper that reads the prior `critic.json`. Modified `compute_regression_set()` cosmetic branch to call the guard and escalate when `qa != 'CLEAN'`. Updated three existing cosmetic tests to mock `_get_previous_qa_status` returning `'CLEAN'`. Added new `TestRegressionScopeCosmeticFirstPassGuard` test class with three cases.
- **Changes:**
    - **features/policy_critic.md:** Section 2.8 Cosmetic First-Pass Guard added.
    - **features/critic_tool.md:** Section 2.12 cosmetic bullet updated; new scenario added; existing scenario precondition tightened.
    - **tools/critic/critic.py:** `_get_previous_qa_status()` added; `compute_regression_set()` cosmetic branch guarded.
    - **tools/critic/test_critic.py:** New `TestRegressionScopeCosmeticFirstPassGuard` class; three existing cosmetic tests extended with prior-CLEAN mock.

## [2026-02-21] Formalized Release Process Checklist

- **Scope:** Spec additions and instruction refinement only (Builder implements tooling and dashboard changes).
- **Problem:** The release protocol lived exclusively in `instructions/ARCHITECT_BASE.md` Section 8 as duplicated prose. It had no machine-readable structure, no UI surface, no way for consumer projects to customize steps, and no separation between the push-to-remote step and the rest of the audit.
- **Solution:**
    - New anchor node `features/policy_release.md` establishes governance rules: `purlin.` namespace reservation for global step IDs, immutability of global steps in consumer projects, local config as single source of truth for ordering and enable/disable state, auto-discovery safety (new global steps appended automatically), and toggleability of `purlin.push_to_remote`.
    - New feature `features/release_checklist_core.md` defines the step schema (id, friendly_name, description, code, agent_instructions), storage paths for `global_steps.json` and `local_steps.json`, local config format, the 5-step auto-discovery resolution algorithm, local step ID validation, and the 9 initial global steps with full definitions.
    - New feature `features/release_checklist_ui.md` specifies the CDD Dashboard "RELEASE CHECKLIST" section: collapsed/expanded states, drag-to-reorder (HTML5 DnD or existing library), enable/disable checkbox per step, Step Detail Modal, section state persistence via `localStorage`, and two new API endpoints (`GET /release-checklist`, `POST /release-checklist/config`).
    - `instructions/ARCHITECT_BASE.md` Section 8 replaced: prose audit checklist removed and replaced with a reference to the new release checklist feature specs.
- **Builder delegation:** Builder must implement `tools/release/global_steps.json` (9 initial step definitions), `tools/cdd/serve.py` additions for the two new endpoints, and CDD Dashboard frontend additions for the new section, drag-reorder, and modal.
- **Changes:**
    - **features/policy_release.md:** New anchor node.
    - **features/release_checklist_core.md:** New feature spec.
    - **features/release_checklist_ui.md:** New feature spec.
    - **instructions/ARCHITECT_BASE.md:** Section 8 updated to reference the release checklist system.

## [2026-02-21] Auto-Critic Integration in status.sh

- **Scope:** Spec and instruction changes only (Builder implements the script change).
- **Problem:** Builder agents consistently forgot to run `tools/critic/run.sh` after status commits (Step 4.F), resulting in stale `CRITIC_REPORT.md` and `critic.json` files between sessions.
- **Solution:** Specify that `tools/cdd/status.sh` automatically runs the Critic before outputting status, guarded by a `CRITIC_RUNNING` env var to prevent infinite recursion (since `run.sh` already invokes `status.sh` internally to refresh `feature_status.json`). The Builder instruction file simplifies: startup Step 3 (separate `status.sh` call) and Step 4.F (mandatory post-commit critic run) are both eliminated.
- **Changes:**
    - **features/cdd_status_monitor.md:** Section 2.6 gains Auto-Critic Integration bullet with recursion guard spec; Section 2.8 lifecycle test Verification Method and Cleanup updated to single `status.sh` command; four lifecycle integration scenarios updated from two-step `When/And` to single `When`.
    - **features/critic_tool.md:** Section 2.9 clarifies "does NOT run the Critic" applies to the web server only, not the CLI tool; Section 2.10 CDD Feature Status Dependency updated to describe new direction (status.sh → run.sh → status.sh with guard).
    - **instructions/BUILDER_BASE.md:** Section 2.1 steps 1+3 collapsed into single step; Step 4.F removed; Shutdown Protocol step 1 updated to `status.sh`.

## [2026-02-21] Multi-Provider Agent Launchers & Gemini Support

- **Scope:** Feature spec additions, instruction refinement, script and config changes (Builder-implemented).
- **Problem:** All three agent launchers failed at runtime with `ERROR: Provider 'gemini' is not yet supported for agent invocation` because provider dispatch only implemented Claude. No spec existed for the multi-provider launcher contract. Gemini 3.0 models were missing from provider configs and the `permissions` capability was incorrectly set to `false` for all Gemini models.
- **Solution:**
    - New feature spec `features/agent_launchers_common.md` defines the full multi-provider launcher contract: prompt assembly, config reading, Claude dispatch, Gemini dispatch (`GEMINI_SYSTEM_MD` injection, `--yolo` flag), concurrent safety, role-specific tool restrictions, and unsupported provider error handling.
    - Category renamed from `"Initialization & Update"` to `"Install, Update & Scripts"` across four feature files (`agent_configuration.md`, `python_environment.md`, `submodule_bootstrap.md`, `submodule_sync.md`).
    - `features/agent_configuration.md` updated: script names updated to `run_architect.sh` etc.; provider dispatch description updated to include Gemini as a supported provider.
    - `features/submodule_bootstrap.md` updated: Section 2.5 and all scenarios updated to new script names; new Section 2.17 (Provider Detection Integration) specifies that bootstrap runs `detect-providers.sh` after config patching, merges available provider models into config, and prints a detection summary.
    - `instructions/ARCHITECT_BASE.md` Zero Code Implementation Mandate tightened: DevOps script exception removed. Architect write access is now strictly limited to feature specs, instruction files, and prose docs. All script and code changes are Builder-delegated.
    - Gemini 3.0 Pro and 3.0 Flash added to provider configs; `permissions` capability updated to `true` for all Gemini models.
    - Launcher scripts renamed from `run_claude_*.sh` to `run_architect.sh`, `run_builder.sh`, `run_qa.sh`.
    - `README.md` updated: all script name references updated; new `## Supported Providers` section added with provider table, capability notes, and install hints.
- **Changes:**
    - **features/agent_launchers_common.md:** New file.
    - **features/agent_configuration.md:** Category rename; script name and provider dispatch description updates.
    - **features/submodule_bootstrap.md:** Category rename; Section 2.5, Section 2.17, and scenario script name updates.
    - **features/python_environment.md:** Category rename.
    - **features/submodule_sync.md:** Category rename.
    - **instructions/ARCHITECT_BASE.md:** Zero Code Mandate tightened; DevOps script exception removed.
    - **tools/providers/gemini.sh:** Added Gemini 3.0 Pro and 3.0 Flash; `permissions: true` for all models.
    - **agentic_devops.sample/config.json:** Added full Gemini provider section.
    - **.agentic_devops/config.json:** Added Gemini 3.0 models; fixed `permissions` to `true` for all Gemini models.
    - **run_architect.sh, run_builder.sh, run_qa.sh:** New provider-agnostic launchers.
    - **run_claude_architect.sh, run_claude_builder.sh, run_claude_qa.sh:** Deleted.
    - **tools/bootstrap.sh:** Updated launcher generation to use new script names, added Gemini dispatch block, added detect-providers integration (Section 2.17).
    - **README.md:** Script name references updated; Supported Providers section added.

## [2026-02-21] Hard Submodule Prohibition in Sample Override Templates

- **Scope:** Documentation/template hardening -- no feature spec or instruction base file changes.
- **Problem:** The "Submodule Immutability Mandate" in `HOW_WE_WORK_BASE.md` Section 6 is buried in a long document. Consumer-project agents could miss it or fail to recognize they are in a consumer project rather than the Purlin repo itself. One existing sample file (`HOW_WE_WORK_OVERRIDES.md`) had a soft, one-paragraph reminder that was easy to overlook.
- **Solution:** Added a `## HARD PROHIBITION: Purlin Submodule Is Read-Only` block as the **first section** in all four `agentic_devops.sample/` override templates. This block is installed verbatim into every consumer project by `bootstrap.sh`, so every agent reads it before any project-specific rules. The pre-existing soft-reminder section in `HOW_WE_WORK_OVERRIDES.md` was replaced (consolidated into the new top-of-file block). `ARCHITECT_OVERRIDES.md` also received an "Instruction File Scope Clarification" section resolving the ambiguity in `ARCHITECT_BASE.md` Section 4 Responsibility #2 ("refine instruction files" means `.agentic_devops/` overrides, not `purlin/instructions/`).
- **Changes:**
    - **agentic_devops.sample/HOW_WE_WORK_OVERRIDES.md:** Replaced "Submodule Immutability (DO NOT REMOVE)" with top-of-file HARD PROHIBITION block.
    - **agentic_devops.sample/ARCHITECT_OVERRIDES.md:** Added top-of-file HARD PROHIBITION block and "Instruction File Scope Clarification" section.
    - **agentic_devops.sample/BUILDER_OVERRIDES.md:** Added top-of-file HARD PROHIBITION block.
    - **agentic_devops.sample/QA_OVERRIDES.md:** Added top-of-file HARD PROHIBITION block.

## [2026-02-21] Builder: Post-Commit Critic Run Mandate

- **Scope:** Instruction refinement -- no feature spec changes.
- **Problem:** The Builder had no instruction to run `tools/critic/run.sh` after status commits during a session. This created a staleness window where `critic.json` files (powering the CDD dashboard and action-item queues) lagged behind actual project state until the Shutdown Protocol's final critic run.
- **Solution:** Added Step 4.F "Post-Commit Critic Run (MANDATORY)" to Section 4 of `instructions/BUILDER_BASE.md`, directly after the Phase Completion Check (Step 4.E). The rule mirrors the Architect's Responsibility 6 pattern, with the Builder's trigger being status commits (`[Ready for Verification]` or `[Complete]`) rather than spec edits. Also updated the Shutdown Protocol (Section 5) to clarify its run is the "final" critic run, distinguishing it from the per-status-commit runs.
- **Changes:**
    - **instructions/BUILDER_BASE.md:** Section 4, Step 4 — added Step 4.F; Section 5 — clarified Shutdown Protocol wording.

## [2026-02-21] Phased Delivery Protocol — Builder Instruction Gaps Resolved

- **Scope:** Instruction refinement -- no feature spec changes.
- **Problem:** `BUILDER_BASE.md` used the term "HIGH-complexity" in phasing heuristics without defining it, and referenced `delivery_plan.md` format in prose only (no template). Both gaps could produce inconsistent Builder behavior across sessions.
- **Solution:**
    - Added an inline definition of HIGH-complexity (4 criteria: new infrastructure, 5+ functions, 3+ files, behavioral uncertainty).
    - Added a canonical `delivery_plan.md` Markdown template with rules for status transitions, commit recording, and immutability of COMPLETE phases.
- **Changes:**
    - **instructions/BUILDER_BASE.md:** Section 2.2.1 — expanded HIGH-complexity definition and added template block.

## [2026-02-21] Provider-Agnostic Agent Configuration

- **Scope:** New feature -- config-driven agent parameters with provider-agnostic architecture. Launcher scripts, probe scripts, bootstrap, feature spec.
- **Problem:** Agent launch parameters (model, effort, permissions) were hardcoded in launcher scripts. No way to change them without editing shell scripts. No path to support non-Claude providers.
- **Solution:** Introduced **provider-agnostic agent configuration** via `config.json`:
    - `llm_providers` section defines available providers and their models with per-model capability declarations.
    - `agents` section assigns provider/model/effort/permissions per role.
    - Launcher scripts read config at startup and dispatch by provider.
    - Provider probe scripts (`tools/providers/*.sh`) auto-detect available providers.
    - Aggregator script (`tools/detect-providers.sh`) collects all probe results.
- **Changes:**
    - **features/agent_configuration.md:** New feature spec covering config schema, probe scripts, dashboard Agents section, API endpoints, launcher behavior, and bootstrap generation.
    - **config.json / sample config.json:** Added `llm_providers` and `agents` sections.
    - **tools/providers/claude.sh:** New probe script for Claude CLI detection.
    - **tools/providers/gemini.sh:** New probe script for Gemini CLI/API detection.
    - **tools/detect-providers.sh:** New aggregator script.
    - **run_claude_architect.sh, run_claude_builder.sh, run_claude_qa.sh:** Rewritten to read config, dispatch by provider, and build CLI args dynamically.
    - **tools/bootstrap.sh:** Section 5 refactored to use `generate_launcher` helper function that produces config-driven launchers with role-specific tool restrictions.
- **Impact:** Launchers now respect config.json settings. Dashboard Agents section and API endpoints are spec'd for Builder implementation.

## [2026-02-21] Phased Delivery Protocol

- **Scope:** New cross-role coordination protocol -- persistent delivery plan artifact, instruction-level changes across all three agent roles, CDD dashboard integration.
- **Problem:** When the Architect introduces large-scale changes (multiple new feature files, major revisions), the Builder agent can exhaust its context window or need complex multi-agent merges that degrade quality. No mechanism existed for the Builder to split work across multiple sessions with QA verification between phases.
- **Solution:** Introduced the **Phased Delivery Protocol** -- a persistent coordination artifact at `.agentic_devops/cache/delivery_plan.md` that lets the Builder propose splitting work into numbered phases, each producing a testable state. The user orchestrates the cycle: Builder (Phase 1) -> QA (verify Phase 1) -> Builder (fix bugs + Phase 2) -> QA -> ... until complete. Phasing is always optional and user-approved.
- **Changes:**
    - **HOW_WE_WORK_BASE.md:** Added Section 10 (Phased Delivery Protocol) with 7 subsections: Purpose (10.1), Delivery Plan Artifact (10.2), Cross-Session Resumption (10.3), QA Interaction (10.4), Phasing is Optional (10.5), Architect Awareness (10.6), CDD Dashboard Integration (10.7).
    - **BUILDER_BASE.md:** 5 insertions -- Step 2.1.6 (Delivery Plan Check), Section 2.2.0 (Resuming a Delivery Plan), Section 2.2.1 (Scope Assessment with phasing heuristics), Step 4.E (Phase Completion Check), Step 5.3 (Phase-aware shutdown message).
    - **QA_BASE.md:** 3 insertions -- Section 3.3.1 (Delivery Plan Context), Step 5.5.3 modified (delivery plan gate before marking Complete), Step 6.3.4 (Phase context in session summary).
    - **features/cdd_status_monitor.md:** Added Section 2.11 (Delivery Phase Indicator), updated API schema with optional `delivery_phase` field, 2 new automated scenarios (Delivery Phase in API Response, Delivery Phase Omitted When No Plan), 4 new visual spec items for phase annotation.
- **Commit Convention:** Defined standard commit messages for plan creation, phase completion, amendments, and deletion.
- **Impact:** `cdd_status_monitor.md` reset to TODO (spec changed). Builder must implement: delivery plan parsing in CDD status tool, `delivery_phase` field in `/status.json` API, phase annotation in dashboard ACTIVE header. No code changes required for Builder/QA instruction changes (agent behavior only).

## [2026-02-21] Merge Software Map into CDD Dashboard

- **Scope:** Architectural merge -- unified CDD Dashboard with Status and SW Map views on a single port.
- **Problem:** The CDD Status Monitor and Software Map Generator were two separate web tools sharing the same feature data, design tokens, theme system, and modal pattern, but running on different ports with independent servers. This split duplicated infrastructure (server, header, theme toggle, branding, search, modal) and forced agents to reference two separate CLI tools for graph and status data.
- **Solution:** Merged into a single **CDD Dashboard** category with two focused feature files:
    - `features/cdd_status_monitor.md` -- The dashboard shell (unified header, view mode switching, search, URL routing, CLI, config/port, branding) plus the Status view (feature tables, collapsible sections, badges, workspace).
    - `features/cdd_software_map.md` -- The SW Map view (Cytoscape.js graph rendering, category grouping, hover highlighting, graph generation, file watcher, Mermaid export). Depends on the dashboard shell via prerequisite link.
    - Deleted `features/software_map_generator.md` (requirements split between the two new files; git history preserves it).
    - Deleted `features/software_map_generator.impl.md` (tribal knowledge merged into `cdd_status_monitor.impl.md`).
- **New dashboard features specified:**
    - View mode toggle ("Status"/"SW Map") with URL hash routing (`/#status`, `/#map`).
    - Collapsible Active/Complete/Workspace sections with chevron indicators and collapsed summaries.
    - Unified search/filter box (filters status rows or graph nodes depending on active view).
    - Feature detail modal shared between both views (click feature row or graph node).
    - CLI `--graph` flag on `tools/cdd/status.sh` (replaces standalone `generate_tree.py`).
    - New API endpoints: `/dependency_graph.json`, `/feature?file=`, `/impl-notes?file=`.
    - Matched column widths between Active and Complete tables.
    - Centered status column headers, left-justified Feature column.
- **Config:** Removed `map_port` from `.agentic_devops/config.json` (9087) and `agentic_devops.sample/config.json` (8087). Single `cdd_port` serves both views.
- **Files Created:** `features/cdd_software_map.md`.
- **Files Deleted:** `features/software_map_generator.md`, `features/software_map_generator.impl.md`.
- **Files Modified:** `features/cdd_status_monitor.md`, `features/cdd_status_monitor.impl.md`, `features/design_visual_standards.md`, `features/impl_notes_companion.md`, `features/submodule_bootstrap.md`, `features/python_environment.md`, `instructions/HOW_WE_WORK_BASE.md`, `instructions/ARCHITECT_BASE.md`, `instructions/QA_BASE.md`, `.agentic_devops/QA_OVERRIDES.md`, `.agentic_devops/BUILDER_OVERRIDES.md`, `.agentic_devops/config.json`, `agentic_devops.sample/config.json`, `README.md`.
- **Impact:** `cdd_status_monitor.md` reset to TODO (spec rewritten). `cdd_software_map.md` in TODO (new). `submodule_bootstrap.md`, `python_environment.md`, `impl_notes_companion.md`, `design_visual_standards.md` reset to TODO (spec changed). Builder must implement: unified server, view mode switching, collapsible sections, search/filter, feature detail modal, CLI `--graph` flag, new API endpoints, graph generation integration.

## [2026-02-21] Fix Critic Tool Lifecycle Gap: Stale Cache + Scope Validation Surfacing

- **Scope:** Shell wrapper fix + feature spec update for Critic lifecycle freshness and scope validation visibility.
- **Problem 1 (Stale cache):** `tools/critic/run.sh` invoked `critic.py` without regenerating `feature_status.json` first. After spec edits reset features to TODO, the cached file still showed TESTING/COMPLETE, so the Critic never detected the lifecycle reset. The Builder saw zero action items for features with real spec changes.
- **Problem 2 (Silent warnings):** `compute_regression_set()` validated `targeted:` scope names and stored warnings in `cross_validation_warnings`, but these warnings were never surfaced as Builder action items or in the Critic report.
- **Solution (Part A -- stale cache):** Added CDD cache refresh to `tools/critic/run.sh`. Before invoking `critic.py`, the wrapper now calls `tools/cdd/status.sh` to regenerate `feature_status.json`. Guarded with `[ -f ]` for standalone Critic usage and `|| true` for graceful degradation.
- **Solution (Part B -- scope validation surfacing):** Updated `features/critic_tool.md` to specify that cross-validation warnings from targeted scope name validation MUST be surfaced as MEDIUM-priority Builder action items with category `scope_validation`. Added new action item table row, priority level entry, spec bullet in Section 2.12, and new automated scenario.
- **Changes:**
    - `tools/critic/run.sh`: Added CDD status refresh before `critic.py` exec.
    - `features/critic_tool.md`: Updated Section 2.10 (new Builder action item row, MEDIUM priority entry, CDD freshness guarantee), Section 2.12 (scope name validation action items bullet, targeted scope example updated), new automated scenario "Builder Action Items from Invalid Targeted Scope Names".
- **Delegation:** Builder must implement scope validation action item generation in `critic.py` `generate_action_items()` and add corresponding test cases in `test_critic.py`.

## [2026-02-21] Targeted Scope Naming Contract: Enforce Exact Scenario/Screen Names

- **Scope:** Policy spec update + CDD scenario fix.
- **Problem:** The `targeted:` scope type in status commits allowed free-form labels (e.g., `targeted:Web Dashboard Display`, `targeted:Interactive Web View`). These labels did not match any actual manual scenario or visual spec screen name, making it impossible for the QA agent to programmatically determine which verification items to test.
- **Solution:** Added a **Naming Contract** to `policy_critic.md` Section 2.8 requiring:
    - Manual scenarios: exact title from `#### Scenario: <Name>` (e.g., `targeted:Web Dashboard Auto-Refresh`).
    - Visual spec screens: `Visual:` prefix + exact screen name from `### Screen: <Name>` (e.g., `targeted:Visual:CDD Web Dashboard`).
    - Mixed targets: comma-separated (e.g., `targeted:Web Dashboard Auto-Refresh,Visual:CDD Web Dashboard`).
    - Critic MUST validate names and emit WARNING for unresolvable targets.
- **Changes:**
    - `features/policy_critic.md`: Added naming contract subsection in Section 2.8; updated scope types table example.
    - `features/cdd_status_monitor.md`: Fixed "Change Scope in API Response" scenario to use a valid scenario name (`Web Dashboard Auto-Refresh`) instead of the invalid `Web Dashboard Display`.
- **Delegation:** Builder must re-issue status commits for `cdd_status_monitor` and `software_map_generator` with corrected scope values. Builder must also implement Critic validation of `targeted:` scope names against feature spec items.

## [2026-02-21] Implementation Notes Companion Files: Extract to Reduce Feature File Size

- **Scope:** New feature spec + tool changes + instruction updates + migration of 7 existing feature files.
- **Problem:** Feature files' Implementation Notes sections consumed up to 27% of file size (worst case: `software_map_generator.md`). When agents scan feature files for requirements and scenarios, they waste context window on implementation notes they don't need for that task.
- **Solution: Companion files** (`features/<name>.impl.md`):
    - Implementation Notes extracted to companion files alongside their parent feature spec.
    - Feature file retains a one-line stub: `See [<name>.impl.md](<name>.impl.md) for implementation knowledge...`
    - Companion files are NOT feature files: excluded from dependency graph, Spec Gate, Implementation Gate, CDD lifecycle, and orphan detection.
    - **Status reset exemption:** Edits to `<name>.impl.md` do NOT reset the parent feature's lifecycle status to TODO.
    - Critic resolves companion content via `resolve_impl_notes()` for builder decision parsing and traceability overrides.
    - Software Map viewer shows tabbed modal (Specification / Implementation Notes) when companion file exists.
- **Changes:**
    - **New feature spec:** `features/impl_notes_companion.md` defining the convention.
    - **Tool exclusion filters (6 scan points):** `tools/critic/critic.py`, `tools/cdd/serve.py` (2 locations), `tools/software_map/generate_tree.py`, `tools/software_map/serve.py`, `tools/cleanup_orphaned_features.py` -- all updated to exclude `*.impl.md` from feature file discovery.
    - **Critic companion resolution:** New `resolve_impl_notes()` function in `critic.py`. `run_implementation_gate()` updated to accept `feature_path` and resolve companion content. Section completeness check correctly handles stub references.
    - **Cleanup tool:** Companion awareness added -- orphaned companion files (no parent `.md`) are flagged.
    - **Software Map serve.py:** New `/impl-notes?file=<path>` endpoint serving companion file content.
    - **Software Map index.html:** Tabbed modal UI with "Specification" and "Implementation Notes" tabs, lazy-loaded and cached.
    - **Instruction files:** `HOW_WE_WORK_BASE.md` (new Section 4.3), `ARCHITECT_BASE.md`, `BUILDER_BASE.md`, `QA_BASE.md` all updated to reference companion file convention.
    - **Test updates:** 5 new test cases in `test_critic.py` covering companion resolution, backward compatibility, exclusion filters, and stub handling.
    - **Migration:** 7 feature files migrated (critic_tool, submodule_bootstrap, submodule_sync, python_environment, design_visual_standards, cdd_status_monitor, software_map_generator). `policy_critic.md` has no Implementation Notes, not migrated.
- **Impact:** Feature specs that were migrated retain their current lifecycle status (stub replacement does not change spec content semantics). New `impl_notes_companion.md` spec in TODO state. All 173 critic tests pass.

## [2026-02-21] Visual vs Functional Test Separation: Minimize Manual Scenarios

- **Scope:** Instruction update + feature spec refinement -- codified classification rule for Visual Specification vs Manual Scenarios; moved static visual checks out of Manual Scenarios into Visual Specification sections.
- **Problem:** Several Manual Scenarios in `cdd_status_monitor.md` and `software_map_generator.md` were purely visual checks (layout, colors, typography, element presence) that could be verified from a static screenshot. Keeping them as Gherkin scenarios forced expensive interactive QA walkthroughs and prevented screenshot-assisted batch verification.
- **Classification Principle:** Visual Specification (checklist) = verifiable from a static screenshot, no interaction required. Manual Scenario (Gherkin) = requires interaction (clicks, hovers, typing), temporal observation, or multi-step functional verification.
- **Changes:**
    - **HOW_WE_WORK_BASE.md:** Added Section 9.6 (Visual vs Functional Classification) codifying the classification rule.
    - **ARCHITECT_BASE.md:** Added "Visual-First Classification" bullet to Section 3.2 (Living Specifications).
    - **cdd_status_monitor.md:** Removed 2 manual scenarios ("Web Dashboard Display", "Role Columns on Dashboard") -- all checks absorbed into Visual Specification. Slimmed "Web Dashboard Auto-Refresh" to functional core only (removed visual-stability lines already covered by Visual Spec). Added 6 new Visual Specification checklist items.
    - **software_map_generator.md:** Removed 1 manual scenario ("Interactive Web View") -- all 10 checks absorbed into Visual Specification. Added 9 new Visual Specification checklist items.
- **Manual Scenario Count:** CDD: 5 -> 3. Software Map: 6 -> 5.
- **Impact:** Both feature specs reset to TODO (spec content changed). No code changes required. QA verification effort reduced; visual checks now eligible for screenshot-assisted batch verification.

## [2026-02-21] QA Shutdown Gate: Restructured Session Conclusion for Reliable Final Critic Run

- **Scope:** QA instruction change -- restructured Session Conclusion (Section 6) to prevent the QA agent from skipping the final Critic run.
- **Problem:** The QA agent was running the Critic between features (per Section 5.5) but consistently skipping the final Critic run at session end. The final run was listed as step 5 (the last step) in Section 6, making it easy for the agent to compose its summary and "wrap up" without reaching it. This left `critic.json` files stale at the end of QA sessions.
- **Solution:** Two structural changes to make the final Critic run impossible to skip:
    1. **Section 6 reordered:** The final Critic run is now Step 1 (SHUTDOWN GATE), before git commit (Step 2) and the session summary (Step 3). The agent cannot compose a summary without having run the Critic first.
    2. **Section 2 CRITIC RUN MANDATE reinforced:** Added a session-end gate bullet explicitly cross-referencing Section 6 Step 1 and stating the agent is not permitted to present a session summary without a preceding Critic run in the same turn.
- **Changes:**
    - **QA_BASE.md Section 2 (CRITIC RUN MANDATE):** Added session-end gate bullet.
    - **QA_BASE.md Section 6 (Session Conclusion):** Rewritten from a flat 5-step list to a 3-step gated sequence with the Critic run as the mandatory first step.
- **Impact:** QA instruction change only. No code, spec, or tool changes required.

## [2026-02-21] Universal Discovery Recording: Any Agent May Report Bugs

- **Scope:** Process change to User Testing Protocol -- any agent can now record OPEN discoveries.
- **Problem:** The User Testing Discoveries section had "exclusive write access" for the QA Agent. When the Architect or Builder discovered a bug during their work, they had no way to record it in the structured format that the Critic recognizes. This meant the CDD dashboard could not reflect known bugs unless QA happened to find them during a verification pass.
- **Solution:** Changed ownership model from "QA-exclusive" to "any agent records, QA manages lifecycle":
    - Any agent (Architect, Builder, QA) MAY record a new OPEN discovery when they encounter a bug or unexpected behavior.
    - The QA Agent retains ownership of lifecycle management: verification, resolution confirmation, and pruning of RESOLVED entries.
    - Discovery entries now include a `Found by:` field identifying the recording agent.
- **Changes:**
    - **HOW_WE_WORK_BASE.md Section 7.1:** Changed "owned exclusively by the QA Agent" to "any agent may record, QA owns lifecycle management."
    - **HOW_WE_WORK_BASE.md Section 7.3:** Changed "QA records the finding" to "Any agent records the finding."
    - **HOW_WE_WORK_BASE.md Section 7.5:** Changed routing header from "QA-to-Architect/Builder" to role-agnostic "From User Testing Discoveries."
    - **policy_critic.md Section 2.4:** Broadened "QA Agent records findings" to "any agent may record findings."
- **Impact:** Process change only. No tool code changes required -- the Critic already parses discoveries by type/status regardless of who wrote them. QA_BASE.md requires no changes (QA still writes discoveries during verification; this change adds capability to other roles without removing QA's).

## [2026-02-21] Screenshot-Assisted Visual Verification for QA Agent

- **Scope:** QA workflow enhancement -- QA agent can now analyze user-provided screenshots to auto-verify visual checklist items.
- **Rationale:** Visual spec verification was fully manual: the QA agent presented the entire checklist and asked for a single PASS/FAIL. Many checklist items describe static, visible properties (layout, element presence, typography, color) that an agent can verify from a screenshot, since Claude Code is multimodal. This change lets the QA agent auto-verify what it can and only ask the user to confirm the remainder, reducing manual effort.
- **Changes:**
    - **QA_BASE.md Section 5.4:** Rewritten from a 4-step process into 6 subsections (5.4.1-5.4.6). New flow: present checklist, offer screenshot input, analyze screenshots (classify items as screenshot-verifiable vs. not), present consolidated results (auto-verified + manual confirmation list), manual fallback for users who decline screenshots, and batching optimization with screenshot support.
    - **HOW_WE_WORK_BASE.md Section 9.5:** New "Verification Methods" subsection documenting that visual checklist items MAY be verified via screenshot-assisted analysis. Informs all roles about the capability without changing any workflow.
- **What does NOT change:** Feature file format, Critic tool behavior, CDD monitor, Architect ownership of visual specs, discovery recording protocol, QA overrides.
- **Impact:** QA workflow change only. No code, spec, or tool changes required. The QA agent gains an optional capability; the existing manual fallback is preserved.

## [2026-02-21] Builder Bug Fix Resolution Mandate

- **Scope:** Process addition to BUILDER_BASE.md -- Builder must update BUG discovery status after fixing.
- **Rationale:** When the Builder fixes an OPEN [BUG] in User Testing Discoveries, nobody was updating the entry's status from OPEN to RESOLVED. This caused the Critic to keep generating Builder action items and the CDD dashboard to show Builder as TODO even after the fix was committed. The lifecycle gap meant the dashboard never reflected that Builder work was complete, blocking QA from seeing their column as TODO.
- **Changes:**
    - **BUILDER_BASE.md:** Added "Bug Fix Resolution" bullet to Section 4, Step 2 (Implement and Document). Builder MUST update BUG entry status from OPEN to RESOLVED as part of the implementation commit.
- **Impact:** Process clarification only. No tool code changes. Closes a lifecycle gap between Builder fix commits and Critic role_status computation.

## [2026-02-21] Continuous Design-Driven (CDD) Elevated to Core Tenet

- **Scope:** Elevated "Continuous Design-Driven" from a tool name (CDD Monitor) to the framework's core philosophy.
- **Rationale:** The CDD acronym already described the framework's fundamental approach -- designs evolve in sync with code -- but it was buried in the CDD Status Monitor feature description. Promoting it to a named tenet makes the philosophy explicit and discoverable.
- **Changes:**
    - **HOW_WE_WORK_BASE.md:** Renamed Section 1 from "Core Philosophy: Code is Disposable" to "Core Philosophy: Continuous Design-Driven (CDD)". Added two sub-principles: "Code is Disposable" (1.1, preserved) and "Design Evolves with Code" (1.2, new). Updated Section 8 CDD reference to include full name.
    - **README.md:** Updated tagline from "Agentic Development Framework" to "Continuous Design-Driven Development Framework". Added CDD framing to Overview. Renamed Core Concept "Spec-Driven Development" to "Continuous Design-Driven (CDD)" with evolutionary language.
    - **PROCESS_HISTORY.md:** Updated header description. This entry added.
- **Impact:** Philosophy-level change only. No structural, code, or behavioral changes. All existing specs, tools, and workflows remain valid.

## [2026-02-20] Purlin Rebranding

- **Scope:** Full product rebrand from "Agentic DevOps Core" to "Purlin". The internal `.agentic_devops/` directory name is retained for backward compatibility.
- **Changes:**
    - **README.md:** Full rewrite with new title, subtitle, four-goal overview, updated repo URL (`https://github.com/rlabarca/purlin/`), submodule examples using `purlin` directory name, logo reference (`assets/purlin-logo.svg`), compatibility note for `.agentic_devops/`, renamed Evolution table.
    - **Instruction files:** Replaced "Agentic DevOps Core" product name references with "Purlin" in `HOW_WE_WORK_BASE.md`, `ARCHITECT_BASE.md`, `BUILDER_BASE.md`, `QA_BASE.md`. Retained "Agentic Workflow" as a process/methodology term.
    - **Override files:** Updated product/repo name references in all `.agentic_devops/*_OVERRIDES.md` and `agentic_devops.sample/*_OVERRIDES.md` files.
    - **Launcher scripts:** Updated `CORE_DIR` from `agentic-dev` to `purlin` in `run_claude_architect.sh`, `run_claude_builder.sh`, `run_claude_qa.sh`.
    - **Bootstrap:** Updated printed text references in `tools/bootstrap.sh`.
    - **Sample config:** Updated `tools_root` from `agentic-dev/tools` to `purlin/tools` in `agentic_devops.sample/config.json`.
    - **Feature files:** Updated Overview text in `submodule_bootstrap.md`, `submodule_sync.md`, `python_environment.md`, `policy_critic.md`, `critic_tool.md`.
    - **New anchor node:** `features/design_visual_standards.md` created as the design system anchor node.
    - **CDD and Software Map specs:** Updated with `design_visual_standards.md` prerequisite for theming.
    - **Logo asset:** `assets/purlin-logo.svg` created.
    - **PROCESS_HISTORY.md:** Header updated, this entry added.
- **Impact:** Text-only rebrand. No structural, code, or behavioral changes. `.agentic_devops/` directory name unchanged.

## [2026-02-21] QA Dependency-Only Skip + Visual Spec Convention Enforcement

- **Problem 1 (QA over-testing on dependency-only scope):** When a feature had `dependency-only` regression scope with an empty `regression_scope.scenarios` list, the QA agent still verified all manual scenarios instead of skipping the feature. The protocol said "verify only scenarios that reference the changed prerequisite's surface area" but did not explicitly handle the empty-list case, leaving the behavior ambiguous.
- **Problem 2 (Visual check as Gherkin scenario):** CDD Status Monitor had "Scenario: Section Heading Visual Separation" as a manual Gherkin scenario, but per HOW_WE_WORK_BASE Section 9 (Visual Specification Convention), purely visual/subjective checks belong in a `## Visual Specification` section as checklist items, not as Given/When/Then scenarios.
- **Solution (QA Protocol):**
    - Section 3.3: Updated `dependency-only` presentation format to show "QA skip" when the scenarios list is empty.
    - Section 5.0: Added explicit empty-list handling -- if `regression_scope.scenarios` is empty, skip the feature entirely (same as cosmetic). Move to the next feature.
- **Solution (CDD Spec):**
    - Removed "Scenario: Section Heading Visual Separation" from Manual Scenarios (5 manual scenarios remain).
    - Added `## Visual Specification` section with a "Screen: CDD Web Dashboard" subsection containing the underline separator checklist items.
- **Files Modified:** `instructions/QA_BASE.md` (Sections 3.3, 5.0), `features/cdd_status_monitor.md` (Manual Scenarios, new Visual Specification section).
- **Impact:** CDD spec reset to TODO. No code changes required (visual spec is Architect-owned). QA protocol clarification only -- no Builder work.

## [2026-02-20] Anchor Node Taxonomy: arch_, design_, policy_ Prefixes

- **Problem:** All dependency graph anchor nodes used the single `arch_*.md` prefix regardless of domain. Visual standards (color palettes, typography, spacing) do not belong under "architectural policy," and governance rules (security baselines, compliance, coordination policies) are semantically distinct from technical constraints. The single prefix made it harder for agents and humans to quickly identify what domain a constraint file governs.
- **Solution:** Introduced a three-prefix taxonomy for anchor nodes. All three function identically in the dependency system (cascade resets, Critic prerequisite detection). The distinction is semantic:
    - `arch_*.md` -- Technical constraints (system architecture, data flow, dependency rules, code patterns).
    - `design_*.md` -- Design constraints (visual language, typography, spacing, interaction patterns, accessibility).
    - `policy_*.md` -- Governance rules (process policies, security baselines, compliance requirements, coordination rules).
- **Rename:** `features/arch_critic_policy.md` renamed to `features/policy_critic.md`. All prerequisite links updated.
- **Files Modified:**
    - `instructions/HOW_WE_WORK_BASE.md` (new Sections 4.1 Anchor Node Taxonomy, 4.2 Cross-Cutting Standards Pattern).
    - `instructions/ARCHITECT_BASE.md` (Section 3.1 broadened to three prefixes; Zero Code Mandate and Post-Commit Critic Run updated).
    - `instructions/BUILDER_BASE.md` (Pre-Flight and Escalation updated from `arch_*` to anchor node terminology).
    - `features/policy_critic.md` (renamed from `arch_critic_policy.md`; title, FORBIDDEN patterns, impl notes updated).
    - `features/critic_tool.md` (prerequisite link, all `arch_*`-only patterns broadened to three-prefix, 6 scenarios renamed/updated).
    - `features/cdd_status_monitor.md`, `features/software_map_generator.md` (prerequisite links updated).
    - `README.md` (Core Concepts section, Mermaid diagram updated).
    - `.agentic_devops/ARCHITECT_OVERRIDES.md` (cross-reference path updated).
- **Builder Impact:** Tool code (`critic.py`, `policy_check.py`, `test_critic.py`, `test_lifecycle.sh`) still uses `arch_*.md` pattern for anchor node detection. Builder must update pattern matching to recognize all three prefixes. This will surface as TODO action items via the Critic report.

## [2026-02-20] QA Process Optimization: Regression Scoping + Visual Verification

- **Problem 1 (No regression scoping):** QA tests ALL manual scenarios for every TESTING feature, even when only a small change was made. There is no way to skip QA for low-risk changes or target specific scenarios, making the QA process inefficient.
- **Problem 2 (Visual tests scattered):** Visual/UI checks are mixed into manual Gherkin scenarios across feature files with no way to reference design assets (Figma, PDFs, images) or consolidate visual verification into a dedicated pass.
- **Solution (Optimization 1 -- Smart Regression Scoping):**
    - Builder declares impact scope at status-commit time via `[Scope: ...]` trailer (full, targeted, cosmetic, dependency-only).
    - Critic reads scope, cross-validates against dependency graph, and generates scoped QA action items.
    - Cross-validation: cosmetic scope with files touching manual scenarios emits WARNING.
    - New `regression_scope` block in per-feature `critic.json`.
    - QA startup reads scope and presents filtered verification targets.
- **Solution (Optimization 2 -- Visual Specification Convention):**
    - New `## Visual Specification` section in feature files (optional, Architect-owned).
    - Per-screen checklist format with design asset references (Figma URLs, local paths).
    - Exempt from Gherkin traceability.
    - Critic detects visual specs and generates separate visual QA action items.
    - QA executes a dedicated Visual Verification Pass after functional scenarios.
    - Visual checks can be batched across features for efficiency.
- **How they interact:** Regression scoping filters WHICH features/scenarios QA verifies. Visual specification defines HOW visual checks are structured. Scope applies to visual too (cosmetic skips both, targeted skips visual unless explicitly targeted, full includes visual).
- **Files Modified:**
    - `features/arch_critic_policy.md` (new Invariants 2.8 Regression Scoping, 2.9 Visual Specification Convention; renumbered CDD Decoupling to 2.10).
    - `instructions/HOW_WE_WORK_BASE.md` (new Section 9: Visual Specification Convention).
    - `instructions/BUILDER_BASE.md` (Section 4: added [Scope: ...] commit convention with scope types table, examples, and guidance).
    - `instructions/QA_BASE.md` (Section 3.3: scoped verification targets; Section 5.0: scoped verification modes; Section 5.4: Visual Verification Pass; Section 5.5: updated Feature Summary).
    - `instructions/ARCHITECT_BASE.md` (Section 3.2: added visual spec ownership note).
    - `features/critic_tool.md` (new Sections 2.12 Regression Scope Computation, 2.13 Visual Specification Detection; renumbered Untracked File Audit to 2.14; 11 new automated scenarios).
    - `features/cdd_status_monitor.md` (added change_scope to /status.json and feature_status.json schemas; 2 new automated scenarios).
    - `PROCESS_HISTORY.md`.
- **Impact:** Feature specs (`critic_tool.md`, `cdd_status_monitor.md`, `arch_critic_policy.md`) reset to TODO. Builder must implement: `extract_change_scope()` in CDD, `compute_regression_set()` and `has_visual_spec()` in Critic, scoped QA action items, `regression_scope` and `visual_spec` blocks in critic.json, `change_scope` field in status JSON output.

## [2026-02-20] Python Environment Isolation for Submodule Consumers

- **Problem:** 2 of 7 shell scripts (`cdd/start.sh`, `software_map/start.sh`) had ad-hoc venv detection while the other 5 (`critic/run.sh`, `cdd/status.sh`, `bootstrap.sh`, `cdd/test_lifecycle.sh`, `cdd/stop.sh`) used bare `python3`. If a consumer creates a `.venv/` (e.g., to install the optional `anthropic` SDK for LLM-based logic drift), only the server scripts find it. The remaining scripts silently use system Python, creating a split-brain execution environment.
- **Solution:**
    - **New feature spec** (`features/python_environment.md`): Defines a shared Python resolution helper (`tools/resolve_python.sh`), migration of all 7 shell scripts to use it, dependency manifests (`requirements.txt`, `requirements-optional.txt`), and a bootstrap venv suggestion.
    - **Resolution priority:** `$AGENTIC_PYTHON` env var > `$AGENTIC_PROJECT_ROOT/.venv/` > climbing detection from script dir > system `python3` > system `python`. Cross-platform venv paths (Unix `.venv/bin/python3`, MSYS/MinGW `.venv/Scripts/python.exe`). Diagnostics to stderr only (no stdout pollution).
    - **Dependency manifests:** `requirements.txt` (empty/comment-only, establishes convention), `requirements-optional.txt` (`anthropic>=0.18.0`). Framework has zero required Python dependencies.
    - **Bootstrap venv suggestion** (`features/submodule_bootstrap.md` Section 2.16): After bootstrap completes, print optional venv setup guidance if `.venv/` does not exist. Informational only -- bootstrap does not fail without Python or a venv.
    - **README.md:** Added "Python Environment (Optional)" section documenting venv setup, resolution priority, and cross-platform notes.
- **Files Created:** `features/python_environment.md`.
- **Files Modified:** `features/submodule_bootstrap.md` (added Section 2.16), `README.md` (added Python Environment section), `PROCESS_HISTORY.md`.
- **Impact:** New feature spec in [TODO] state. `submodule_bootstrap.md` reset to [TODO]. Builder must implement: `tools/resolve_python.sh`, migrate 7 shell scripts, create dependency manifests, add bootstrap venv suggestion, and add test scenarios.

## [2026-02-20] Critic Spec Gate: Eliminate False-Positive WARNs

- **Problem:** The Critic Spec Gate produced persistent LOW-priority WARNs for features with legitimate states: (1) `scenario_classification` flagged features that explicitly declared "None" for Manual Scenarios as "Only Automated subsection present." (2) `policy_anchoring` flagged features with valid non-arch_*.md prerequisites as "Has prerequisite but not linked to policy file." These WARNs appeared every Architect session startup, masking a clean project state.
- **Root Cause:** The `scenario_classification` PASS condition required both subsections to have content, without recognizing explicit opt-out declarations. The `policy_anchoring` PASS condition required an arch_*.md link specifically, treating any other prerequisite as insufficient grounding.
- **Solution:**
    - **scenario_classification:** PASS now accepts "Both subsections present (with content or explicit 'None' declaration)." Features that deliberately have no manual scenarios pass clean.
    - **policy_anchoring:** PASS now accepts "Has prerequisite to non-policy file (feature is grounded)." Features linked to instruction files or other features are considered architecturally grounded. WARN is reserved for features with NO prerequisites at all.
    - **Scenario fix:** "Spec Gate No Prerequisite on Non-Policy" corrected from FAIL to WARN (matched the table definition, scenario was inconsistent).
    - **New scenarios:** "Spec Gate Non-Policy Prerequisite" (PASS), "Scenario Classification Explicit None for Manual" (PASS).
- **Files Modified:** `features/critic_tool.md` (Section 2.1 table, 1 fixed scenario, 2 new scenarios, implementation notes), `PROCESS_HISTORY.md`.
- **Impact:** Feature spec reset to TODO. Builder must implement: update `scenario_classification` check to recognize explicit "None" opt-outs, update `policy_anchoring` to accept non-arch_*.md prerequisites as PASS, fix "no prerequisite" from FAIL to WARN.

## [2026-02-20] QA Actionability: SPEC_UPDATED Lifecycle Routing + QA Status Simplification

- **Problem:** SPEC_UPDATED discoveries with `Action Required: Builder` generated Builder action items, keeping Builder=TODO even after the Builder had committed. Both `cdd_status_monitor` and `critic_tool` showed Builder=TODO when QA was the role that needed to act next. Additionally, QA=TODO triggered for OPEN items routing to Architect (condition c: HAS_OPEN_ITEMS), making the dashboard ambiguous about which agent to run.
- **Root Cause:** SPEC_UPDATED-to-Builder routing was redundant with the feature lifecycle. When the Architect updates a spec, the feature resets to TODO lifecycle, which already gives the Builder a TODO. The discovery-based routing double-counted. QA TODO conditions were too broad -- they included items that QA could not act on.
- **Solution:**
    - **Removed SPEC_UPDATED-to-Builder routing:** SPEC_UPDATED discoveries no longer generate Builder action items. Builder signaling comes exclusively from the feature lifecycle (TODO state). The `Action Required` field on discoveries is informational only.
    - **QA TODO condition (b) made lifecycle-dependent:** SPEC_UPDATED re-verify items only trigger QA=TODO when the feature is in TESTING lifecycle (Builder has committed).
    - **QA TODO condition (c) removed:** HAS_OPEN_ITEMS no longer triggers QA=TODO. OPEN items routing to Architect/Builder are not QA-actionable.
    - **QA CLEAN simplified:** Requires `tests.json` PASS only. OPEN items routing to other roles do not block CLEAN.
    - **QA N/A becomes catch-all:** Covers no tests.json, tests.json FAIL without QA-specific concerns.
    - **QA Actionability Principle:** New invariant -- QA=TODO only when QA has work to do RIGHT NOW.
- **Scenarios Updated:** "Builder Action Items from SPEC_UPDATED Discovery" reversed (now verifies NO Builder items). "QA TODO for SPEC_UPDATED Items" requires TESTING. "QA TODO for HAS_OPEN_ITEMS" replaced with "QA CLEAN Despite OPEN Discoveries Routing to Architect". New scenario: "QA CLEAN for SPEC_UPDATED in TODO Lifecycle".
- **Files Modified:** `features/arch_critic_policy.md` (Section 2.4), `features/critic_tool.md` (Sections 2.10, 2.11; 3 updated scenarios, 2 new scenarios), `PROCESS_HISTORY.md`.
- **Impact:** Both feature specs reset to TODO. Builder must implement: remove SPEC_UPDATED-to-Builder routing from `generate_action_items()`, make QA TODO condition (b) lifecycle-dependent, remove QA TODO condition (c), simplify QA CLEAN computation.

## [2026-02-20] QA Server Prohibition + CDD Run Critic Button + Spec Hygiene

- **Problem 1 (QA agent managing servers):** Despite the QA Override "Server Interaction Prohibition", the QA agent was still starting and stopping the CDD server during sessions. Root cause: QA_BASE.md Section 5.2 contained a Given-step example that cued the agent to ensure the server was running (`"Make sure the CDD server is running"`), which the agent interpreted as a directive to start/stop the process itself.
- **Problem 2 (No manual Critic trigger):** The CDD dashboard had no way for the human to trigger a Critic run from the UI. The only option was running `tools/critic/run.sh` from the terminal.
- **Problem 3 (Spec hygiene):** `submodule_bootstrap.md` and `submodule_sync.md` had no Manual Scenarios subsection (Critic WARN). `software_map_generator.md` had no `arch_*.md` prerequisite link.
- **Solution:**
    - Added "NO SERVER PROCESS MANAGEMENT" mandate to QA_BASE.md Section 2. Updated the Given-step example in Section 5.2 to instruct the human tester instead of implying agent action.
    - Added CDD Monitor Section 2.7 (Manual Critic Trigger) defining a "Run Critic" button in the dashboard top-right corner next to the update timestamp. Added automated scenario for the `/run-critic` endpoint and a manual scenario for the button UI.
    - Added explicit "Manual Scenarios: None" subsections to `submodule_bootstrap.md` and `submodule_sync.md`.
    - Added `> Prerequisite: features/arch_critic_policy.md` to `software_map_generator.md`.
- **Files Modified:** `instructions/QA_BASE.md`, `features/cdd_status_monitor.md`, `features/submodule_bootstrap.md`, `features/submodule_sync.md`, `features/software_map_generator.md`, `PROCESS_HISTORY.md`.
- **Impact:** QA agent now has a base-level prohibition against server management. CDD dashboard gains a human-triggered Critic run button (Builder must implement). Spec hygiene warnings resolved.

## [2026-02-20] CDD CLI Tool Spec + Artifact Path Alignment

- **Problem 1 (CDD status.sh):** All agent instruction files reference `tools/cdd/status.sh` as the CLI agent interface for feature status (added in the D4 architectural decision), but the CDD feature spec (`cdd_status_monitor.md`) never defined it as a requirement. The tool does not exist. Agents cannot follow their documented startup protocols.
- **Problem 2 (Stale artifact paths):** The submodule_bootstrap spec (Section 2.12) mandates generated artifacts at `.agentic_devops/cache/` and `.agentic_devops/runtime/`, but the CDD spec still referenced `tools/cdd/feature_status.json`, the Software Map spec still referenced `tools/software_map/dependency_graph.json`, and the Architect/Builder instructions still referenced the old Software Map path. The `.gitignore` also lacked entries for the new cache/runtime directories, causing untracked file noise.
- **Problem 3 (Policy anchoring):** The CDD spec had no prerequisite link despite depending on the Critic's `role_status` output contract.
- **Solution:**
    - Added Section 2.6 (CLI Status Tool) to `cdd_status_monitor.md` defining `tools/cdd/status.sh` as a CLI entry point with JSON stdout output and `feature_status.json` regeneration as a side effect.
    - Updated CDD spec Section 2.4: internal artifact path to `.agentic_devops/cache/feature_status.json`, agent contract to reference `status.sh`.
    - Updated Software Map spec Section 2.2: canonical file path to `.agentic_devops/cache/dependency_graph.json`.
    - Updated `critic_tool.md` Sections 2.10-2.11: all `feature_status.json` references to new cache path.
    - Updated `ARCHITECT_BASE.md` and `BUILDER_BASE.md`: `dependency_graph.json` references to new cache path.
    - Added `.agentic_devops/cache/` and `.agentic_devops/runtime/` to `.gitignore`.
    - Added `> Prerequisite: features/arch_critic_policy.md` to `cdd_status_monitor.md`.
- **Files Modified:** `features/cdd_status_monitor.md`, `features/critic_tool.md`, `features/software_map_generator.md`, `instructions/ARCHITECT_BASE.md`, `instructions/BUILDER_BASE.md`, `.gitignore`, `PROCESS_HISTORY.md`.
- **Impact:** CDD spec now defines the CLI tool that all instructions reference. Builder must implement `tools/cdd/status.sh`. Feature specs and instructions are now consistent with the submodule artifact isolation mandate.

## [2026-02-20] Documentation Drift: Submodule Update + README Directory (D11, D12, D13)
- **D11 (submodule update):** HOW_WE_WORK_BASE Section 6 said upstream updates are pulled via `git submodule update`, which pins to the parent's recorded commit (doesn't fetch latest). Updated to `cd agentic-dev && git pull origin main && cd ..` to match the README's correct workflow.
- **D12-D13 (README directory):** `PROCESS_HISTORY.md` was missing from the README's Directory Structure section despite being a root-level workflow artifact created by bootstrap. Added it.
- **Files Modified:** `instructions/HOW_WE_WORK_BASE.md` (Section 6), `README.md` (Directory Structure).
- **Impact:** No spec changes. Documentation corrections only.

## [2026-02-20] Documentation Drift: README Evolution Table + Stale Reference Fix (D6, D7, D8)
- **D6 (README stale):** The Agentic Evolution table in README.md stopped at v3.0.0. Added v3.1.0 row summarizing all post-v3.0.0 changes: Critic coordination engine, CDD role-based columns, escalation protocols, QA completion authority, Builder startup, CLI-first agent interface, submodule safety, and documentation drift corrections.
- **D7 (stale reference):** ARCHITECT_BASE Section 4.12 referenced `.agentic_devops/HOW_WE_WORK.md` which was deleted in v2.0.0. Updated to reference `instructions/HOW_WE_WORK_BASE.md` and override equivalents in `.agentic_devops/`.
- **D8 (terminology):** The v3.0.0 row in the Evolution table used the pre-rename "Critic Quality Gate" terminology. This is historically accurate for that version. The new v3.1.0 row uses the current "Critic Coordination Engine" name, making the rename visible in the table progression.
- **Files Modified:** `README.md` (Agentic Evolution table), `instructions/ARCHITECT_BASE.md` (Section 4.12).
- **Impact:** No spec changes. Documentation corrections only.

## [2026-02-20] Documentation Drift: Discovery Lifecycle Alignment (D5)
- **Problem:** HOW_WE_WORK_BASE Section 7.3 defined the discovery lifecycle as `OPEN -> SPEC_UPDATED -> RESOLVED -> PRUNED`, but QA_BASE Section 4.4 omitted the PRUNED state: `OPEN -> SPEC_UPDATED -> RESOLVED`. The Pruning Protocol was described separately in QA_BASE Section 4.5, so behavior was correct, but the lifecycle summary was inconsistent. An agent reading only the summary line would miss the PRUNED state.
- **Solution:** Added PRUNED to QA_BASE Section 4.4 lifecycle progression and added a PRUNED bullet with a cross-reference to Section 4.5.
- **Files Modified:** `instructions/QA_BASE.md` (Section 4.4).
- **Impact:** No spec changes. Documentation alignment only.

## [2026-02-20] Architectural Decision: Servers for Humans, CLI for Agents (D4)
- **Problem:** All three agent instruction files required agents to read `cdd_port` from config and run `curl -s http://localhost:<port>/status.json` to get feature status. This created a dependency on a running CDD server. Agents had inconsistent fallback behavior when the server was down: the Architect started it directly, the Builder ignored it, and the QA Agent delegated to the user. The core repo's Builder/QA overrides prohibited server startup, but the Architect had no such restriction.
- **Architectural Decision:** Servers (CDD dashboard, Software Map viewer) are for human use only. Agents access all tool data via CLI commands that share logic with the server but produce machine-readable output to stdout without requiring a running server.
- **Solution:**
    - Replaced all 6 `curl` references across ARCHITECT_BASE (3), BUILDER_BASE (2), and QA_BASE (1) with `tools/cdd/status.sh` CLI command.
    - Removed all `cdd_port` reading, server-not-responding fallbacks, and server startup instructions from agent protocols.
    - Added "Agent Interface" principle to HOW_WE_WORK_BASE Section 8: agents use CLI commands, never HTTP servers.
    - Updated core overrides: "Server Startup Prohibition" broadened to "Server Interaction Prohibition" in both BUILDER_OVERRIDES.md and QA_OVERRIDES.md.
- **Files Modified:** `instructions/HOW_WE_WORK_BASE.md` (Section 8), `instructions/ARCHITECT_BASE.md` (Sections 4, 5, 8), `instructions/BUILDER_BASE.md` (Sections 2, 4), `instructions/QA_BASE.md` (Section 3), `.agentic_devops/BUILDER_OVERRIDES.md`, `.agentic_devops/QA_OVERRIDES.md`.
- **Impact:** The CDD feature spec (`features/cdd_status_monitor.md`) needs to be updated to define `tools/cdd/status.sh` as a CLI entry point that shares logic with the web server. Builder must implement `tools/cdd/status.sh`. This also resolves D9 (port default mismatch in agent instructions) as a side effect -- agents no longer reference ports at all.

## [2026-02-20] Documentation Drift: INFEASIBLE Escalation in Shared Philosophy (D3)
- **Problem:** HOW_WE_WORK_BASE Section 7.5 (Feedback Routing) documented all QA-to-Architect/Builder escalation paths (BUG, DISCOVERY, INTENT_DRIFT, SPEC_DISPUTE) but omitted the Builder-to-Architect `[INFEASIBLE]` escalation. This protocol was documented in BUILDER_BASE Section 4 Step 2b and arch_critic_policy.md Section 2.3, but a Builder reading only the shared philosophy document would not know it exists.
- **Solution:** Added INFEASIBLE to Section 7.5 (Feedback Routing) as a Builder-to-Architect escalation, organized under a separate subheading from the QA-originated routes. Includes the halt-and-skip behavior and Architect revision requirement.
- **Files Modified:** `instructions/HOW_WE_WORK_BASE.md` (Section 7.5).
- **Impact:** No spec changes. Documentation gap filled.

## [2026-02-20] Documentation Drift: AGENTIC_PROJECT_ROOT in Standalone Launchers (D2)
- **Problem:** HOW_WE_WORK_BASE Section 6 stated "The generated launcher scripts export `AGENTIC_PROJECT_ROOT`" without qualifying that this only applied to bootstrap-generated launchers. The standalone launchers (`run_claude_architect.sh`, `run_claude_builder.sh`, `run_claude_qa.sh`) did not export the variable. Agents reading the shared philosophy document in standalone mode would expect the variable to exist, but it was absent.
- **Solution:** Two-pronged fix:
    - Added `export AGENTIC_PROJECT_ROOT="$SCRIPT_DIR"` to all three standalone launcher scripts after the `CORE_DIR` fallback block.
    - Updated HOW_WE_WORK_BASE Section 6 (Path Resolution Conventions) to say "All launcher scripts (both standalone and bootstrap-generated)" instead of "The generated launcher scripts."
- **Files Modified:** `run_claude_architect.sh`, `run_claude_builder.sh`, `run_claude_qa.sh`, `instructions/HOW_WE_WORK_BASE.md` (Section 6).
- **Impact:** Standalone launchers now export the variable consistently. No spec changes.

## [2026-02-20] Documentation Drift: DevOps Tools Ownership Clarification (D1)
- **Problem:** HOW_WE_WORK_BASE assigned "DevOps tools" ownership to the Builder, while ARCHITECT_BASE gave the Architect an exception to write "DevOps and Process scripts (e.g., tools/, build configurations)." Both agents write to `tools/` in practice -- the Architect writes process infrastructure (launcher scripts, shell wrappers, bootstrap tooling) and the Builder writes tool implementation code (Python logic, test suites). The ownership boundary was undefined.
- **Solution:** Made the boundary explicit in both documents:
    - HOW_WE_WORK_BASE Section 2: Architect ownership now includes "DevOps process scripts (launcher scripts, shell wrappers, bootstrap tooling)." Builder ownership changed from "the DevOps tools" to "DevOps tool implementation (Python logic, test suites)."
    - ARCHITECT_BASE Section 2: Exception narrowed from "DevOps and Process scripts (e.g., tools/, build configurations)" to "DevOps process scripts (e.g., launcher scripts, shell wrappers, bootstrap tooling)" with explicit exclusion of tool implementation code.
- **Files Modified:** `instructions/HOW_WE_WORK_BASE.md` (Section 2), `instructions/ARCHITECT_BASE.md` (Section 2).
- **Impact:** No spec changes. Documentation clarification only.

## [2026-02-20] Submodule Compatibility: Safety Requirements and Agent Guardrails
- **Problem:** Seven issues identified that would break agentic-dev-core when used as a git submodule in consumer projects. Root causes: (1) bootstrap.sh `sed` regex strips trailing commas from JSON, corrupting config.json; (2) Python tools' directory-climbing finds the submodule's own `.agentic_devops/` before the consumer project's config; (3) generated artifacts (logs, PIDs, caches) written inside `tools/`, dirtying the submodule git state; (4) no `try/except` on `json.load()` in any Python tool; (5) ambiguous `tools/` and `features/` path references in instructions; (6) `cleanup_orphaned_features.py` uses hardcoded CWD-relative paths.
- **Solution (Spec Changes -- `features/submodule_bootstrap.md`):**
    - **Section 2.10 (Config Patching JSON Safety):** sed regex must only replace the value portion, preserving commas. JSON validation step after patching. Test must verify parseability, not just grep.
    - **Section 2.11 (Project Root Environment Variable):** Launcher scripts export `AGENTIC_PROJECT_ROOT`. All Python and shell tools check this env var first. Climbing fallback reversed: try further path (submodule layout) before nearer path (standalone layout).
    - **Section 2.12 (Generated Artifact Isolation):** Logs/PIDs to `.agentic_devops/runtime/`, caches to `.agentic_devops/cache/`. Bootstrap gitignore updated.
    - **Section 2.13 (Python Tool Config Resilience):** All `json.load()` calls wrapped in try/except with fallback defaults. No unhandled crashes.
    - **Section 2.14 (Utility Script Project Root Detection):** cleanup_orphaned_features.py uses same root detection as other tools.
    - **Section 2.15 (Submodule Simulation Test Infrastructure):** Test harness must create a simulated submodule environment for automated testing of all path resolution, artifact isolation, and config resilience scenarios.
    - **10 new automated scenarios** covering JSON validity, env var export, climbing priority, artifact isolation, config resilience, cleanup script, and test sandbox.
- **Instruction Changes (`instructions/HOW_WE_WORK_BASE.md`):**
    - Added "Path Resolution Conventions" subsection to Section 6 (Layered Instruction Architecture). Clarifies that `features/` = consumer project's, `tools/` resolves via `tools_root`, and `AGENTIC_PROJECT_ROOT` is the authoritative root.
- **Override Changes (`.agentic_devops/`):**
    - `HOW_WE_WORK_OVERRIDES.md`: Added "Submodule Compatibility Mandate" with 5-point checklist for all agents.
    - `BUILDER_OVERRIDES.md`: Added "Submodule Safety Checklist (Pre-Commit Gate)" with 6-point verification for every code change.
    - `ARCHITECT_OVERRIDES.md`: Added "Submodule Compatibility Review" for spec-level verification.
    - `QA_OVERRIDES.md`: Added "Submodule Environment Verification" requiring dual-mode testing (standalone + submodule).
- **Impact:** Feature spec reset to TODO. Builder must implement: sed fix, AGENTIC_PROJECT_ROOT in launchers and all Python/shell tools, artifact path relocation, config try/except, cleanup script fix, and submodule simulation test harness.

## [2026-02-20] QA Agent: Completion Authority for Manually Verified Features
- **Problem:** After QA verified all manual scenarios as passing with zero discoveries, features remained in TESTING state with QA=TODO. The Builder was responsible for making `[Complete]` status commits, but QA had already done the verification. This created an unnecessary handoff: QA reports clean -> user asks Builder to mark complete -> Builder makes empty commit. Meanwhile, the CDD dashboard showed stale TODO status.
- **Solution:** Split completion authority based on manual scenario presence:
    - **Features with manual scenarios:** QA makes the `[Complete]` status commit immediately after clean verification (all scenarios pass, zero discoveries). No Builder handoff needed.
    - **Features without manual scenarios:** Builder marks `[Complete]` directly (unchanged behavior).
- **Files Modified:**
    - `instructions/HOW_WE_WORK_BASE.md`: Updated QA role (Section 2) to allow status commits for manually-verified features. Updated lifecycle step 4 to reflect split responsibility.
    - `instructions/BUILDER_BASE.md`: Updated status tag determination (Section 4, Step 4.A) to clarify Builder only marks `[Complete]` for features with no manual scenarios.
    - `instructions/QA_BASE.md`: Updated Feature Summary (Section 5.4) to add `[Complete]` commit after clean verification. Updated Session Conclusion (Section 6) to reflect completion tracking.
- **Impact:** Process change only. No spec or code changes. QA agent now owns the TESTING -> COMPLETE transition for features with manual scenarios.

## [2026-02-20] QA Status: Lifecycle-Independent Findings + Manual Scenario Filtering

- **Problem 1 (QA N/A hiding findings):** When the Architect modified a feature spec, the CDD lifecycle reset the feature to TODO. The Critic's QA role_status computation treated TODO lifecycle as N/A ("not ready for QA"), even when QA had already verified the feature and recorded OPEN discoveries or SPEC_DISPUTES. Result: QA completed features (cdd_status_monitor, critic_tool, software_map_generator) showed QA=N/A on the dashboard, hiding active QA findings.
- **Root Cause:** QA status definitions for FAIL and DISPUTED implicitly required TESTING/COMPLETE lifecycle state. The stated precedence (FAIL > DISPUTED > TODO > CLEAN > N/A) was correct but the implementation path allowed lifecycle-based N/A to override higher-priority statuses.
- **Problem 2 (QA TODO with 0 manual scenarios):** submodule_bootstrap was in TESTING lifecycle state but had 0 manual scenarios. The Critic generated a QA action item ("Verify submodule_bootstrap: 0 manual scenarios") and set QA=TODO, even though QA had nothing to verify. The QA agent correctly ignored it, creating a dashboard/agent discrepancy.
- **Solution (critic_tool.md Section 2.11):**
    - FAIL and DISPUTED are now explicitly lifecycle-independent. They are evaluated before lifecycle state checks.
    - TODO expanded with three conditions: (a) TESTING lifecycle + manual scenarios > 0; (b) SPEC_UPDATED items awaiting re-verification; (c) HAS_OPEN_ITEMS with OPEN discoveries routing to other roles. All conditions are lifecycle-independent.
    - N/A tightened: requires complete absence of QA engagement (no open items of any kind).
    - Added "Lifecycle independence" invariant clarifying that spec resets do NOT suppress existing QA findings.
    - Updated Lifecycle State Dependency paragraph.
- **Solution (critic_tool.md Section 2.10):** QA verification action items from TESTING status now require at least one manual scenario. Added QA Action Item Filtering note.
- **New Scenarios:** Role Status QA DISPUTED in Non-TESTING Lifecycle, Role Status QA TODO for SPEC_UPDATED Items, Role Status QA TODO for HAS_OPEN_ITEMS, Role Status QA N/A for TESTING Feature with No Manual Scenarios. Updated existing QA TODO and QA N/A scenarios.
- **Additional Changes:**
    - Resolved SPEC_DISPUTE in critic_tool.md: Converted "Critic Report Readability" manual scenario to automated "Aggregate Report Structural Completeness" scenario (CRITIC_REPORT.md is agent-facing per Section 2.9).
    - Fixed stale "--" to "??" in critic_tool.md "CDD Dashboard Role Columns" manual scenario.
    - Added Label Wrapping requirement and scenario step to software_map_generator.md. Updated DISCOVERY status to SPEC_UPDATED.
- **Files Modified:** `features/critic_tool.md` (Sections 2.10, 2.11; 5 new scenarios, 2 updated scenarios, 1 removed manual scenario, 1 new automated scenario, 1 SPEC_DISPUTE resolved), `features/software_map_generator.md` (Section 2.4, Interactive Web View scenario, DISCOVERY resolved).
- **Impact:** Both feature specs reset to TODO. Builder must implement: lifecycle-independent QA status computation, QA action item manual scenario filtering, aggregate report structural validation, label wrapping in software map.

## [2026-02-20] Agent Shutdown Protocol: Critic Regeneration on Exit
- **Problem:** After an agent completed work and committed to git, the Critic report and `critic.json` files were not regenerated. This left the CDD dashboard showing stale role status until the next agent session ran the Critic at startup. Between sessions, the dashboard could show incorrect TODO/DONE states.
- **Solution:** Added a Shutdown Protocol to all three agent instruction files requiring `tools/critic/run.sh` to be run after all work is committed, before concluding the session.
- **Files Modified:** `instructions/ARCHITECT_BASE.md` (new Section 6), `instructions/BUILDER_BASE.md` (new Section 5), `instructions/QA_BASE.md` (new step 5 in Section 6).
- **Impact:** No spec changes. Agent behavior only. Section numbers renumbered in Architect (Release Protocol -> 8) and Builder (Team Orchestration -> 6, Build Protocols -> 7).

## [2026-02-20] CDD Spec: Resolve QA Discoveries (Badge and Heading Separation)
- **SPEC_DISPUTE Resolved:** Changed the badge for missing `critic.json` from `--` to `??` throughout the spec (badge table in Section 2.2, API contract in Section 2.4, Role Status Integration in Section 2.5, and all scenario references). The `??` badge clearly indicates "not yet generated" vs `N/A` which means "not applicable."
- **DISCOVERY Resolved:** Added a Section Heading Visual Separation requirement to Section 2.3 and a new Manual Scenario ("Section Heading Visual Separation") requiring underline separators beneath "ACTIVE" and "COMPLETE" headings.
- **Discovery Statuses:** Both entries in `## User Testing Discoveries` updated from OPEN to SPEC_UPDATED.
- **Files Modified:** `features/cdd_status_monitor.md`.
- **Impact:** CDD spec reset to TODO. Builder must implement `??` badge rendering and section heading underlines.

## [2026-02-19] Builder Status: Lifecycle-Aware TODO Detection
- **Problem:** When the Architect modifies a feature spec, the CDD lifecycle correctly resets the feature to TODO. But the Critic's Builder role_status still computes DONE because: (1) existing tests still pass (structural completeness PASS), (2) keyword-based traceability produces false-positive matches for new scenarios with similar names, (3) the Builder status computation ignores lifecycle state entirely. Result: the Builder's startup shows Builder=DONE and proposes zero work for a feature with real spec changes.
- **Root Cause:** Builder status was computed purely from test/traceability/tag signals. The CDD lifecycle "Status Reset" (file edit after status commit resets to TODO) was invisible to Builder role_status.
- **Solution:** Added lifecycle state as a Builder status input in Section 2.11 of `critic_tool.md`. If a feature is in TODO lifecycle state, Builder is TODO regardless of traceability or test status. Added a corresponding HIGH-priority Builder action item ("Review and implement spec changes for <feature>") in Section 2.10. Added scenario "Builder Action Items from Lifecycle Reset."
- **Files Modified:** `features/critic_tool.md` (Sections 2.10, 2.11, new scenario).
- **Impact:** Critic spec reset to TODO. Builder must implement lifecycle-aware Builder status and action item generation in `tools/critic/critic.py`.

## [2026-02-19] Architect Delegation Prompt Scope Reduction
- **Problem:** The Architect's work plan included delegation prompts for Builder/QA spec and implementation work. This was redundant -- each agent's startup protocol already self-discovers action items from project artifacts (Critic report, feature specs, CDD status). The delegation prompts added noise and implied the Builder/QA couldn't derive their own priorities.
- **Solution:** Narrowed Section 5.2 item 4 in `ARCHITECT_BASE.md`. Delegation prompts are now restricted to git check-in of Builder-owned uncommitted files only. Spec and implementation work is NOT delegated -- agents discover it through their startup protocols.
- **Files Modified:** `instructions/ARCHITECT_BASE.md` (Section 5.2 item 4).
- **Impact:** No spec changes. Architect startup behavior only.

## [2026-02-19] QA Status: Tighten CLEAN Definition
- **Problem:** The Critic computed QA=CLEAN for features in TESTING lifecycle state that had no open user testing items. But TESTING means "awaiting QA verification" -- the QA agent hasn't touched the feature yet. This caused the CDD dashboard to show QA=CLEAN while the Critic simultaneously generated "Verify" action items for the same features, a direct contradiction.
- **Root Cause:** The QA CLEAN definition in Section 2.11 of `critic_tool.md` said "is or was in TESTING/COMPLETE lifecycle state." The TESTING inclusion was too broad -- it marked unverified features as CLEAN.
- **Solution:** Tightened QA CLEAN to require COMPLETE lifecycle state only. Features in TESTING state now always receive QA=TODO (unless elevated to FAIL/DISPUTED by open items). Added scenario "Role Status QA TODO for TESTING Feature" to enforce the constraint.
- **Files Modified:** `features/critic_tool.md` (Section 2.11 QA Status definitions, new scenario).
- **Impact:** Critic spec reset to TODO. Builder must update `compute_role_status()` in `tools/critic/critic.py`.

## [2026-02-19] Architect Startup Protocol
- **Problem:** The Architect had a "Context Clear Protocol" that was a recovery checklist, not a proactive startup sequence. Unlike the Builder (which now proposes a work plan on launch), the Architect waited passively for user direction. The Architect also had no spec-level gap analysis and no mechanism to present delegation prompts for Builder/QA work.
- **Solution:** Restructured Section 5 from "Strategic Protocols > Context Clear Protocol" into a proper "Startup Protocol" (5.1 Gather State, 5.2 Propose Work Plan, 5.3 Wait for Approval), mirroring the Builder's pattern. Added spec-level gap analysis (step 5.1.5) and untracked file triage (step 5.1.6) to the state-gathering phase. Work plan includes delegation prompts for Builder/QA. Added initial prompt to launcher script.
- **Files Modified:** `instructions/ARCHITECT_BASE.md` (Section 5 restructured, Section 6 renumbered to 7), `run_claude_architect.sh` (added initial prompt).
- **Impact:** No spec changes. Architect startup behavior only.

## [2026-02-19] Builder Startup: Spec-Level Gap Analysis
- **Problem:** The Builder's startup protocol relied entirely on the Critic report for action items. When the Critic implementation itself is stale (e.g., the Critic tool spec is in TODO state), the Critic cannot accurately report its own gaps. Additionally, the Critic's keyword-based traceability produces false-positive matches for rewritten scenarios, masking real implementation gaps. This caused the Builder to miss major implementation work (role_status computation, CDD redesign) and propose incorrect work plans.
- **Solution:** Added step 2.1.5 (Spec-Level Gap Analysis) to the Builder's startup protocol. For each feature in TODO or TESTING state, the Builder reads the full feature spec and compares Requirements/Scenarios against current implementation code, independent of the Critic report. Updated step 2.2 to include spec-level gaps alongside Critic items in the proposed work plan.
- **Files Modified:** `instructions/BUILDER_BASE.md` (Sections 2.1 and 2.2).
- **Impact:** No spec changes. Builder startup behavior only.

## [2026-02-19] Untracked File Triage Protocol
- **Problem:** Generated artifacts (critic.json, CRITIC_REPORT.md, tests.json) and uncommitted source files accumulate as untracked files in the working directory. No clear ownership or process existed for deciding whether to commit or gitignore them. Multiple agents (Architect, Builder, tool scripts) all produce files.
- **Solution:** The Architect is the single triage point for all untracked files.
- **Critic Changes** (`features/critic_tool.md`):
    - New Section 2.12 (Untracked File Audit): Critic runs `git status --porcelain`, detects untracked files, generates MEDIUM-priority Architect action items for each.
    - Added untracked file row to action item generation table (Section 2.10).
    - Added 2 new automated scenarios (detection, aggregate report).
- **Architect Instruction Changes** (`instructions/ARCHITECT_BASE.md`):
    - New responsibility 13 (Untracked File Triage): Architect must gitignore generated artifacts, commit Architect-owned files, or delegate Builder-owned files with a specific prompt for the user.
- **Gitignore Updates** (`.gitignore`):
    - Added `tests/*/critic.json` and `CRITIC_REPORT.md` (previously orphaned generated artifacts).
- **Impact:** Critic spec reset to TODO. Builder must implement the untracked file audit.

## [2026-02-19] CDD Role-Based Status Redesign + Critic role_status
- **Problem:** CDD showed a single-dimensional lifecycle (TODO/TESTING/COMPLETE) with Tests and QA columns. This told you WHAT was wrong but not WHO needed to act. A feature showing "HAS_OPEN_ITEMS" could mean the Builder needs to fix a bug, the Architect needs to revise a disputed spec, or QA needs to re-verify. Escalation states (SPEC_DISPUTE, INFEASIBLE) were tracked by the Critic but invisible on the CDD dashboard.
- **Design Principle:** Critic computes everything, CDD just reads and displays it.
- **Critic Tool Changes** (`features/critic_tool.md`):
    - Added `role_status` object to per-feature `critic.json` schema (Section 2.7): `architect` (DONE/TODO), `builder` (DONE/TODO/FAIL/INFEASIBLE/BLOCKED), `qa` (CLEAN/TODO/FAIL/DISPUTED/N/A).
    - New Section 2.11 (Role Status Computation) with precedence rules for each role.
    - Added 12 new automated scenarios for role_status computation and output.
- **CDD Spec Changes** (`features/cdd_status_monitor.md`):
    - Dashboard redesigned: three lifecycle sections (TODO/TESTING/COMPLETE) replaced with two groups (Active/Complete).
    - Table columns changed: Feature | Tests | QA replaced with Feature | Architect | Builder | QA.
    - New badge/color mapping for all role status values.
    - Active section sorted by urgency (red states first).
    - **Breaking API change:** `/status.json` now returns flat `features` array with role fields. No more `todo`/`testing`/`complete` sub-arrays. No more `test_status` or `qa_status` fields.
    - Internal `feature_status.json` retains old format for Critic consumption (not part of public API).
    - Replaced QA Status scenarios with Role Status equivalents. Updated Zero-Queue, dashboard, and column scenarios.
- **Policy Changes** (`features/arch_critic_policy.md`):
    - Section 2.8 (CDD Decoupling) updated: CDD reads `role_status` (not just `user_testing.status`).
    - Section 4 (Output Contract) updated to include `role_status` in per-feature output.
- **Instruction Changes:**
    - `instructions/ARCHITECT_BASE.md`: Zero-Queue Mandate updated -- verifies all features have `architect: DONE`, `builder: DONE`, `qa: CLEAN|N/A` instead of checking empty arrays.
    - `instructions/HOW_WE_WORK_BASE.md`: Section 8 updated to describe CDD's role-based columns.
- **Impact:** Both feature specs reset to TODO. Builder must implement: Critic `role_status` computation, CDD role-based dashboard, new `/status.json` schema, `feature_status.json` format split.

## [2026-02-19] Escalation Protocols: SPEC_DISPUTE and INFEASIBLE
- **Problem:** Two feedback loops lacked clean protocols: (1) During QA testing, the user disagrees with a scenario's expected behavior (the spec is wrong, not the code). (2) During implementation, the Builder discovers a feature is infeasible as specified. Both cases require escalation back to the Architect, but existing discovery types and decision tags didn't capture these semantics.
- **QA: New Discovery Type `[SPEC_DISPUTE]`:**
    - User rejects a scenario's expected behavior during testing.
    - QA records it in User Testing Discoveries with the user's rationale.
    - The disputed scenario is **suspended** -- QA skips it in future sessions until the Architect resolves the dispute.
    - Routes to Architect (like DISCOVERY and INTENT_DRIFT).
    - Generates HIGH-priority Architect action item in Critic report.
- **Builder: New Decision Tag `[INFEASIBLE]` (Severity: CRITICAL):**
    - Feature cannot be implemented as specified (technical constraints, contradictory requirements, dependency issues).
    - Builder records the tag with detailed rationale in Implementation Notes, then **halts work** and skips to the next feature.
    - Generates CRITICAL-priority Architect action item in Critic report (highest priority).
    - Architect must revise the spec before Builder can resume.
- **Files Modified:**
    - `instructions/HOW_WE_WORK_BASE.md`: Added SPEC_DISPUTE to discovery types (7.2), feedback routing (7.5), and QA role description (Section 2).
    - `instructions/QA_BASE.md`: Added SPEC_DISPUTE to discovery types (4.1), recording protocol (4.2), scenario walkthrough (5.2), feedback routing (Section 7). Added scenario suspension protocol.
    - `instructions/BUILDER_BASE.md`: Added INFEASIBLE to decision categories (4.2b) with halt-and-skip rule.
    - `features/arch_critic_policy.md`: Added INFEASIBLE to Builder Decision Transparency (2.3), SPEC_DISPUTE to User Testing Feedback Loop (2.4).
    - `features/critic_tool.md`: Added SPEC_DISPUTE/INFEASIBLE to action item table (2.10), added CRITICAL priority level, updated user testing audit (2.6), extended JSON schema with spec_disputes count, added 3 new automated scenarios.
- **Impact:** Feature specs reset to TODO. Builder must implement: SPEC_DISPUTE parsing in user testing audit, INFEASIBLE parsing in builder decisions, CRITICAL priority in action item generation.

## [2026-02-19] Builder Self-Directing Startup Protocol
- **Problem:** The Builder required an elaborate handoff prompt from the Architect describing what to implement. This contradicted the "specs are the source of truth" philosophy -- if the specs and Critic report are complete, the Builder should derive its own work plan.
- **Solution:** Added Section 2 (Startup Protocol) to `BUILDER_BASE.md`:
    - **2.1 Gather Project State:** Builder automatically runs the Critic, reads action items, checks CDD status, and reads the dependency graph.
    - **2.2 Propose a Work Plan:** Builder presents a structured summary to the user: action items grouped by feature, feature queue state, recommended execution order, and estimated scope.
    - **2.3 Wait for Approval:** Builder asks the user "Ready to go, or would you like to adjust the plan?" before starting work.
- **Structural Changes:** Renumbered sections (Feature Status Lifecycle -> 3, Implementation Protocol -> 4, Team Orchestration -> 5, Build Protocols -> 6). Pre-Flight Checks streamlined to per-feature context gathering (architecture and implementation notes), since the Critic run moved to the session-level startup.
- **Impact:** The Architect no longer needs to compose implementation prompts. The user launches the Builder and says "go."

## [2026-02-19] Critic as Project Coordination Engine
- **Problem:** The Critic was a pass/fail badge on the CDD dashboard, but agents need a single source of truth for project health and role-specific priorities. The CDD dashboard showing `CRITIC: FAIL` on features was confusing -- CDD should show objective state, not coordination signals.
- **Architectural Shift:** Critic redefined from "quality gate" to "project coordination engine." CDD shows what IS (feature status, test results, QA status). Critic shows what SHOULD BE DONE (role-specific action items).
- **Policy Changes** (`features/arch_critic_policy.md`):
    - Renamed from "Critic Quality Gate" to "Critic Coordination Engine".
    - New Invariant 2.6 (Agent Startup Integration): every agent MUST run the Critic at session start.
    - New Invariant 2.7 (Role-Specific Action Items): Critic generates imperative action items per role.
    - New Invariant 2.8 (CDD Decoupling): Critic is agent-facing; CDD is human-facing.
    - Deprecated `critic_gate_blocking` config key (retained as no-op for backward compatibility).
- **Critic Tool Spec Changes** (`features/critic_tool.md`):
    - Added Bash test file discovery (`test_*.sh`) with `[Scenario]` marker parsing to traceability engine.
    - New Section 2.10 (Role-Specific Action Item Generation) with per-role derivation rules and priority levels.
    - Section 2.9 (CDD Integration) decoupled: removed `critic_status` from CDD, CDD only reads `user_testing.status` for QA column.
    - Extended `critic.json` schema with `action_items` object (architect/builder/qa arrays).
    - Extended `CRITIC_REPORT.md` with "Action Items by Role" section (Architect/Builder/QA subsections).
    - Added 7 new automated scenarios (bash discovery, bash matching, action items per role, JSON output, aggregate report).
    - Removed "CDD Reads Critic Status" scenario. Updated "CDD Dashboard Critic Badge" to "CDD Dashboard QA Column".
- **CDD Spec Changes** (`features/cdd_status_monitor.md`):
    - Dashboard columns changed: Feature | Tests | Critic -> Feature | Tests | QA.
    - QA column shows CLEAN (green) or HAS_OPEN_ITEMS (orange), read from `user_testing.status` in on-disk `critic.json`.
    - Removed `critic_status` from status JSON (top-level and per-feature). Added optional `qa_status` per feature.
    - Removed `critic_gate_blocking` logic. No status transition blocking.
    - Replaced critic-status scenarios with qa-status equivalents.
- **Instruction Changes:**
    - `HOW_WE_WORK_BASE.md`: Added Section 8 (Critic-Driven Coordination).
    - `ARCHITECT_BASE.md`: Added step 5 to Context Clear Protocol (run Critic, review Architect action items).
    - `BUILDER_BASE.md`: Added "Run the Critic" to Pre-Flight Checks (review Builder action items).
    - `QA_BASE.md`: Updated Startup Protocol step 3.3 to use QA action items from CRITIC_REPORT.md.
- **Impact:** All three feature specs reset to TODO. Builder must implement: bash test discovery, action item generation, CDD QA column replacement, and critic_gate_blocking removal.

## [2026-02-19] Critic and CDD Spec Refinements (QA Feedback)
- **Problem:** QA verification revealed CRITIC:FAIL badges on nearly every feature in the CDD dashboard due to incorrect evaluation of policy files, overly strict policy anchoring, and list-based layout making badges hard to scan.
- **Critic Spec Changes** (`features/critic_tool.md`):
    - Policy files (`arch_*.md`) now receive reduced Spec Gate evaluation (checks Purpose/Invariants instead of Overview/Requirements/Scenarios) and are exempt from the Implementation Gate entirely.
    - Policy anchoring severity relaxed: "No prerequisite" downgraded from FAIL to WARN. FAIL now only triggers when a referenced prerequisite file is missing on disk.
    - Added two new automated scenarios for policy file handling.
- **CDD Spec Changes** (`features/cdd_status_monitor.md`):
    - Dashboard layout changed from lists with inline badges to tables with columns (Feature, Tests, Critic).
    - Blank cells when no `tests.json` or `critic.json` exists (no misleading badges).
    - Updated manual verification scenario for table layout.
- **Stale Prerequisite Fix** (`features/submodule_bootstrap.md`):
    - Updated prerequisite from `HOW_WE_WORK.md` to `instructions/HOW_WE_WORK_BASE.md`.
- **Impact:** All three feature specs reset to TODO. Builder must re-implement critic policy file handling, CDD table layout, and re-run tests.

## [2026-02-19] QA Agent: Interactive Verification Workflow
- **Problem:** The QA process required the human tester to manually edit `.md` files, run scripts, and understand the discovery recording format. Too cumbersome for practical use.
- **Solution: Interactive-First QA Agent:**
    - Rewrote `instructions/QA_BASE.md` to make the QA agent fully interactive. The human tester only answers PASS/FAIL and describes what they see. The agent handles all file operations, critic execution, discovery recording, and git commits.
    - Added Startup Protocol (Section 3): agent automatically runs the critic tool, checks CDD status, identifies TESTING features, and begins walking the user through scenarios.
    - Added Scenario-by-Scenario Walkthrough (Section 5): agent presents each Given/When/Then step with concrete instructions, asks PASS/FAIL, and records discoveries on behalf of the user.
    - Added Session Conclusion (Section 6): agent summarizes results and routes feedback.
- **New Script:** `tools/critic/run.sh` -- executable convenience wrapper for the critic tool.
- **Impact:** QA persona instructions only (no code changes). The human tester never interacts with feature files directly.

## [2026-02-19] v3.0.0 Critic Quality Gate System + QA Persona
- **Problem:** Four failure modes in the Architect-Builder async workflow: underspecification, invisible autonomy, no automated traceability, and user testing gaps.
- **Solution: Critic Quality Gate System:**
    - **Dual-Gate Validation:** Spec Gate (pre-implementation) validates feature spec completeness, Gherkin quality, policy anchoring, and prerequisite integrity. Implementation Gate (post-implementation) validates traceability, policy adherence, builder decisions, and optional LLM-based logic drift detection.
    - **Traceability Engine:** Automated keyword matching between Gherkin scenario titles and test function names/bodies (2+ keyword threshold). Manual scenarios exempt.
    - **Policy Adherence Scanner:** Scans for FORBIDDEN pattern violations defined in `arch_*.md` files.
    - **Logic Drift Engine (LLM):** Optional semantic comparison of scenario intent vs. test implementation. Disabled by default (`critic_llm_enabled: false`).
    - **Per-Feature Output:** `tests/<feature>/critic.json` with spec_gate, implementation_gate, and user_testing sections.
    - **Aggregate Report:** `CRITIC_REPORT.md` at project root.
- **QA Agent (New Role):**
    - Third agent role alongside Architect and Builder.
    - Owns `## User Testing Discoveries` section in feature files (exclusive write access).
    - Records structured discoveries: [BUG], [DISCOVERY], [INTENT_DRIFT].
    - Discovery lifecycle: OPEN -> SPEC_UPDATED -> RESOLVED -> PRUNED.
    - New instruction file: `instructions/QA_BASE.md`.
    - New override files: `.agentic_devops/QA_OVERRIDES.md`, `agentic_devops.sample/QA_OVERRIDES.md`.
    - New launcher: `run_claude_qa.sh`.
- **Builder Decision Protocol:**
    - Added Step 2b to `instructions/BUILDER_BASE.md`.
    - Structured tags: [CLARIFICATION] (INFO), [AUTONOMOUS] (WARN), [DEVIATION] (HIGH), [DISCOVERY] (HIGH).
    - DEVIATION and DISCOVERY require Architect acknowledgment before COMPLETE.
- **New Architectural Policy:** `features/arch_critic_policy.md` -- defines invariants for the Critic system (Dual-Gate, Traceability, Builder Decision Transparency, User Testing Feedback Loop, Policy Adherence).
- **New Feature Spec:** `features/critic_tool.md` -- specifies the Critic tool implementation.
- **HOW_WE_WORK_BASE.md Updates:**
    - Added QA Agent to Section 2 (Roles and Responsibilities).
    - Updated Section 3 (Feature Lifecycle) to include QA verification step.
    - Updated Section 6 (Layered Architecture) to reference QA launcher.
    - Added Section 7 (User Testing Protocol) with discovery types, lifecycle, queue hygiene, and feedback routing.
- **Feature Spec Updates:**
    - `features/cdd_status_monitor.md`: Added Section 2.5 (Critic Status Integration) with per-feature `critic_status`, top-level aggregation, dashboard badge, and optional blocking. Added automated and manual scenarios. Resets to TODO.
    - `features/submodule_bootstrap.md`: Added QA launcher to Section 2.5, updated bootstrap scenario to include QA files, added QA launcher concatenation scenario. Resets to TODO.
- **Config Changes:** Added `critic_llm_model`, `critic_llm_enabled`, `critic_gate_blocking` to both `.agentic_devops/config.json` and `agentic_devops.sample/config.json`.
- **README.md:** Added QA role to Role Separation section, QA launcher documentation, `instructions/QA_BASE.md` to directory structure, updated Agentic Evolution table.
- **Impact:** New feature specs are in [TODO] state. Modified feature specs reset to [TODO]. Builder must implement the Critic tool (`tools/critic/`), CDD critic integration, and bootstrap QA launcher generation.

## [2026-02-19] v2.0.0 Submodule-Ready Layered Architecture
- **Problem:** Consumer projects adopted the framework via `cp -r agentic_devops.sample .agentic_devops`, creating a fork that diverges permanently with no merge path for upstream updates. Framework rules and project-specific context lived in the same monolithic files.
- **Solution: Layered Instruction Architecture:**
    - **Base Layer** (`instructions/`): New directory containing `ARCHITECT_BASE.md`, `BUILDER_BASE.md`, `HOW_WE_WORK_BASE.md`. These hold all framework-generic rules extracted from the former monolithic instruction files. Read-only from the consumer's perspective.
    - **Override Layer** (`.agentic_devops/`): Restructured to contain only thin override files (`ARCHITECT_OVERRIDES.md`, `BUILDER_OVERRIDES.md`, `HOW_WE_WORK_OVERRIDES.md`) with project-specific rules. Consumer projects customize these without touching framework code.
    - **Launcher Scripts** (`run_claude_architect.sh`, `run_claude_builder.sh`): Rewritten to concatenate base + override files into a temporary prompt file at launch time. Detect standalone vs. submodule mode automatically.
- **Sample Directory Restructure** (`agentic_devops.sample/`):
    - Replaced monolithic `ARCHITECT_INSTRUCTIONS.md`, `BUILDER_INSTRUCTIONS.md`, `HOW_WE_WORK.md` with override templates (`*_OVERRIDES.md`).
    - Updated `config.json` to include `tools_root: "agentic-dev/tools"` for submodule path resolution.
- **New Tool Feature Specs:**
    - `features/submodule_bootstrap.md`: Specifies `tools/bootstrap.sh` for initializing consumer projects. Includes project root detection, override directory creation, launcher generation, gitignore guidance, and tool start script config discovery (submodule-aware climbing logic).
    - `features/submodule_sync.md`: Specifies `tools/sync_upstream.sh` for auditing upstream changes after submodule updates. Includes SHA comparison, changelog display, and structural change flagging.
- **Core Override Files:**
    - `.agentic_devops/ARCHITECT_OVERRIDES.md`: Contains only the "Sample Sync Prompt" rule (core-specific).
    - `.agentic_devops/BUILDER_OVERRIDES.md`: Contains only the "Server Startup Prohibition" rule (core-specific).
    - `.agentic_devops/HOW_WE_WORK_OVERRIDES.md`: Minimal (core has no special workflow deviations).
    - `.agentic_devops/config.json`: Added `tools_root: "tools"` (standalone mode).
- **Deleted Files:** `.agentic_devops/ARCHITECT_INSTRUCTIONS.md`, `.agentic_devops/BUILDER_INSTRUCTIONS.md`, `.agentic_devops/HOW_WE_WORK.md` (replaced by base+override split).
- **Port Allocation Convention:** Core uses 9086/9087; consumer projects default to 8086/8087. No collision when both run simultaneously.
- **README.md:** Added "Using as a Submodule" section, layered architecture explanation, update/sync workflow, gitignore guidance, port allocation table. Updated Agentic Evolution table.
- **Impact:** All new tool feature specs are in `[TODO]` state. Builder must implement `tools/bootstrap.sh`, `tools/sync_upstream.sh`, and update `tools/cdd/start.sh` and `tools/software_map/start.sh` for submodule-aware config discovery.

## [2026-02-18] Colocate HOW_WE_WORK.md into .agentic_devops/
- **Change:** Moved `HOW_WE_WORK.md` from project root into `.agentic_devops/HOW_WE_WORK.md`. Added a copy to `agentic_devops.sample/` for distribution to adopting projects.
- **Rationale:** All workflow-defining artifacts (role instructions, config, and now the process philosophy) are colocated in a single distributable folder. This prepares the framework for clean adoption by external projects.
- **Reference Updates:** Updated path references in `.agentic_devops/ARCHITECT_INSTRUCTIONS.md` (Context Clear Protocol, Process History Purity, Feature Scope Restriction), `agentic_devops.sample/ARCHITECT_INSTRUCTIONS.md` (Context Clear Protocol, Process History Purity), and `README.md` (Directory Structure).
- **Sample Sync Coverage:** The existing "Sample Sync Prompt" rule (Architect item 6) already covers any file inside `.agentic_devops/`, so HOW_WE_WORK.md is now automatically included in that mandate.

## [2026-02-18] Remove Dual-Domain Separation (Single-Project Simplification)
- **Problem:** The CDD Monitor and Software Map specs carried a dual-domain model ("Application" vs "Agentic Core") with a "Meta Mode" workaround for when both domains pointed to the same `features/` directory. With agentic-dev-core tracked as its own standalone project, this separation was vestigial complexity.
- **Spec Changes:**
    - `features/cdd_status_monitor.md`: Removed Section 2.1 "Domain Separation", removed `domains` wrapper from JSON schema (flat `features` object), removed "Domain Isolation" scenario, simplified UI to single feature list, removed Meta Mode and Two-Column Layout implementation notes.
    - `features/software_map_generator.md`: Removed `domains` wrapper from JSON schema (flat `features` array), removed Meta Mode implementation note.
- **Instruction Updates:**
    - `.agentic_devops/ARCHITECT_INSTRUCTIONS.md`: Removed Application/Agentic domain language from Source of Truth, Feature Design, Context Clear Protocol. Renamed "Dual-Domain Release Protocol" to "Release Protocol" and simplified verification steps.
    - `.agentic_devops/BUILDER_INSTRUCTIONS.md`: Removed Application/Agentic domain firewall from Executive Summary and Pre-Flight Checks. Simplified testing protocol to remove domain-specific branching.
- **Supporting Files:**
    - `HOW_WE_WORK.md`: Removed Application/Agentic domain distinction from Core Philosophy.
    - `tools/README.md`: Simplified CDD description.
    - `.agentic_devops/config.json`: Removed `is_meta_agentic_dev` flag (no longer needed).
- **Impact:** Both feature specs reset to `[TODO]`. Builder must re-implement to match simplified schemas.

## [2026-02-18] CDD Monitor: JSON API Endpoint for Agent Status Queries
- **Problem:** Agents were reading `tools/cdd/feature_status.json` from disk, but this file is only generated as a side-effect of web dashboard requests. When no dashboard request has been made, the file does not exist, causing agents to fail and resort to port-scanning.
- **Spec Change:** Added `/status.json` API endpoint requirement to `features/cdd_status_monitor.md`. This endpoint serves fresh JSON directly with `Content-Type: application/json`. The disk file remains as a secondary artifact.
- **Agent Contract:** All agent instructions (Architect and Builder, active and sample) updated to use `curl -s http://localhost:<cdd_port>/status.json` instead of reading the file from disk. Port is sourced from `.agentic_devops/config.json` (`cdd_port` key). Agents MUST NOT guess ports or scrape the web dashboard.
- **Scenario Updated:** "Agent Reads Feature Status" scenario rewritten to specify the config-driven port discovery and API call protocol.
- **Commit Mandate Broadened:** Renamed "Instruction Commit Mandate" to "Commit Mandate" in both Architect instruction files (active and sample). Now covers ALL Architect-owned artifacts (specs, policies, instructions, process history, scripts), not just instruction files.

## [2026-02-18] Software Map: Interactive View Requirements & Manual Verification Protocol
- **Problem:** Automated tests cannot meaningfully validate web dashboard rendering and visual layout. The Builder was attempting to start servers and scrape HTML.
- **Scenario Classification:** Both CDD Monitor and Software Map feature specs now separate scenarios into "Automated Scenarios" (API/data, tested by Builder) and "Manual Scenarios (Human Verification Required)" (web UI, verified by User).
- **Server Startup Prohibition:** Added rule to active `BUILDER_INSTRUCTIONS.md` (Section 5): the Builder MUST NOT start DevOps tool servers. The Builder must instruct the User to start them and provide the exact command. This rule is specific to agentic-dev-core and is NOT propagated to the sample template.
- **Test Scope Notes:** Added explicit "Test Scope" implementation notes to both feature specs defining the boundary between automated and manual verification.
- **Software Map Interactive View:** Expanded Section 2.4 with detailed requirements: zoom-to-fit on load (with zoom persistence on refresh), search/filter input, feature detail modal (markdown rendering, X close button, click-outside-to-close), and hover highlighting (immediate neighbors only). Added four new manual verification scenarios.

## [2026-02-18] Builder: Feature Status Lifecycle Protocol
- **Status Lifecycle Table:** Added explicit Section 2 to `BUILDER_INSTRUCTIONS.md` defining the TODO/TESTING/COMPLETE state machine and the git commit tags that drive each transition.
- **Critical Rule:** Documented that any feature file edit (including Implementation Notes) resets status to TODO. The status tag commit MUST be the last commit touching the feature file.
- **Two-Commit Protocol:** Step 2 (Implement) now produces a work commit without a status tag. Step 4 (Status Tag) is a separate commit that transitions the feature out of TODO.
- **Pre-Flight Status Check:** Added `feature_status.json` verification to Pre-Flight Checks so the Builder confirms the feature's current state before starting work.
- **Post-Commit Verification:** Step 4C now requires the Builder to read `feature_status.json` and confirm the status transition took effect.
- **Removed Status Reset Footnote:** The scattered "Status Reset" note in Build & Environment Protocols was eliminated. Status management is now fully integrated into the main protocol flow.

## [2026-02-18] CDD Monitor: Machine-Readable Output
- **Machine-Readable Agent Interface:** Added `feature_status.json` requirement to the CDD Status Monitor spec. This JSON file at `tools/cdd/feature_status.json` is the canonical interface for all agent status queries. Agents MUST NOT scrape the web dashboard.
- **Instruction Updates:** Updated `ARCHITECT_INSTRUCTIONS.md` (Status Management, Context Clear Protocol, Release Protocol Zero-Queue Mandate) and `BUILDER_INSTRUCTIONS.md` (Status Reset) to reference `feature_status.json` as the agent interface. Applied to both active and sample instruction files.

## [2026-02-18] Software Map: Machine-Readable Output & Reactive Generation
- **Machine-Readable Agent Interface:** Added `dependency_graph.json` requirement to the Software Map Generator spec. This JSON file is the canonical interface for all agent tooling. Agents MUST NOT use the web UI or parse Mermaid files.
- **Reactive File Watching:** Added requirement for the tool to auto-regenerate outputs when feature files change while the server is running.
- **Instruction Updates:** Updated `ARCHITECT_INSTRUCTIONS.md` (Context Clear Protocol, Dependency Integrity, Release Protocol) and `BUILDER_INSTRUCTIONS.md` (Pre-Flight Checks) to reference `dependency_graph.json` as the agent interface.

## [2026-02-18] Feature Scope Restriction & Duplicative Spec Cleanup
- **Duplicative Feature Removal:** Deleted 5 feature files (`agent_architect_instructions.md`, `agent_builder_instructions.md`, `proc_release_protocol.md`, `proc_history_management.md`, `arch_agentic_workflow.md`) that restated content already captured in the instruction files and `HOW_WE_WORK.md`.
- **Prerequisite Update:** Redirected prerequisite links in remaining tooling features (`cdd_status_monitor.md`, `software_map_generator.md`) from the removed `arch_agentic_workflow.md` to `HOW_WE_WORK.md`.
- **Feature Scope Restriction Mandate:** Added item 13 to `ARCHITECT_INSTRUCTIONS.md` Section 4, restricting feature files to buildable tooling and application behavior only. Process, workflow, and instruction behavior are governed exclusively by the instruction files.

## [2026-02-18] v1.0.1 Tool Refinement & Custom Port Isolation
- **Configuration Isolation:** Refactored CDD and Software Map tools to respect `.agentic_devops/config.json`, enabling custom port mapping (9086/9087) to avoid system-wide conflicts.
- **Meta-Mode Support:** Enhanced CDD Monitor to dynamically hide the "Application" domain when `is_meta_agentic_dev` is set to true.
- **Instruction Refinement:** Updated `agent_architect_instructions.md` and `agent_builder_instructions.md` feature specifications to include Context Recovery Protocol, Team Orchestration (delegation), and standardized reporting requirements.
- **Tool Stability:** Verified background execution and port listening status for core DevOps tools.
- **Software Map Fixes:** 
    - Resolved Python syntax error in `generate_tree.py` (multiline strings).
    - Fixed Mermaid graph file paths to ensure correct serving relative to `index.html`.
    - Implemented dynamic tab hiding in Software Map based on `is_meta_agentic_dev` config.
