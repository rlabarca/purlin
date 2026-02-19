# Agentic Process History (Core Framework)

This log tracks the evolution of the **Agentic DevOps Core** framework itself. This repository serves as the project-agnostic engine for Spec-Driven AI workflows.

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
