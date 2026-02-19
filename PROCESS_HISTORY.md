# Agentic Process History (Core Framework)

This log tracks the evolution of the **Agentic DevOps Core** framework itself. This repository serves as the project-agnostic engine for Spec-Driven AI workflows.

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
