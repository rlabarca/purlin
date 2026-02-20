# Agentic Process History (Core Framework)

This log tracks the evolution of the **Agentic DevOps Core** framework itself. This repository serves as the project-agnostic engine for Spec-Driven AI workflows.

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
