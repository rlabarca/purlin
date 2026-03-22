# How We Work: The Agentic Workflow

> **Layered Instructions:** This file is the **base layer** of the workflow philosophy, provided by the Purlin framework. Project-specific workflow additions are defined in the **override layer** at `.purlin/HOW_WE_WORK_OVERRIDES.md`. At runtime, both layers are concatenated (base first, then overrides).

> **Path Resolution:** All `tools/` references in this document resolve against the `tools_root` value from `.purlin/config.json`. Default: `tools/`.

## 1. Core Philosophy: Continuous Design-Driven (CDD)

Purlin is **Continuously Design-Driven**: designs evolve in sync with code, never ahead of it and never behind it. Specifications are living documents that are refined as implementation reveals new constraints, discoveries, and insights. The design is never "done" -- it is continuously updated to reflect the current truth of the system.

When code teaches us something new, we update the design first. When requirements shift, the design shifts first, and changes cascade to code. The CDD Monitor exists to make this continuous sync visible and measurable.

This philosophy rests on two principles:

### 1.1 "Code is Disposable"
The single source of truth for any project using this framework is not the code, but the **Specifications** and **Architectural Policies** stored in the project's `features/` directory.
*   If the application code is lost, it must be reproducible from the specs.
*   We never fix bugs in code first; we fix the specification that allowed the bug.

### 1.2 "Design Evolves with Code"
Specifications are not static blueprints written once and handed off. They are continuously refined through the implementation lifecycle:
*   Builder discoveries feed back into specs via Implementation Notes and the INFEASIBLE escalation.
*   QA discoveries (BUG, DISCOVERY, INTENT_DRIFT, SPEC_DISPUTE) trigger spec revisions before code fixes.
*   Anchor node changes cascade to all dependent features, triggering re-validation across the entire domain.
*   The Feature Lifecycle (TODO -> TESTING -> COMPLETE) tracks the sync state between design and implementation at all times.

### 1.3 Tool Path Resolution Protocol
Every agent MUST resolve `tools_root` from `.purlin/config.json` at session start (default: `"tools"`). All `{tools_root}/` references in instruction files, command files, and process documents resolve against this value. In consumer projects where Purlin is a submodule, `tools_root` is typically set to `"purlin/tools"` -- this single config value ensures all tool invocations resolve correctly regardless of project structure.

## 2. Roles and Responsibilities

### The Architect Agent
*   **Focus:** "The What and The Why".
*   **Ownership:** Architectural Policies, Feature Specifications, instruction overrides, and process configuration (`.purlin/release/*.json`, `.purlin/config.json`).
*   **Specification Authority:** The Architect holds specification authority over ALL project artifacts -- including DevOps scripts, launcher scripts, and bootstrap tooling -- exercised exclusively through feature files and anchor nodes, never through direct authorship of implementation files.
*   **Key Duty:** Designing rigorous, unambiguous specifications and enforcing architectural invariants.

### The PM Agent
*   **Focus:** "The Intent and The Design".
*   **Ownership:** Feature spec authoring (shared with Architect), Visual Specification sections, Figma design iteration, design artifact management, and `design_*`/`policy_*` anchor nodes (shared with Architect).
*   **Key Duty:** Translating human intent into complete, unambiguous feature specs with integrated Figma-derived Visual Specifications. Proactively challenges requirements for completeness and implementation simplicity.
*   **Does NOT:** Write code (Builder), modify `arch_*` anchor nodes or instruction files (Architect), or verify behavior (QA).
*   **Figma Authority:** When Figma MCP is available, the PM is the primary agent for reading and writing Figma designs. Other agents read Figma for reference; only the PM writes to it.

### The Builder Agent
*   **Focus:** "The How".
*   **Ownership:** ALL implementation artifacts -- application code (including `.md` files that serve as application artifacts, such as LLM instructions, prompt templates, or content files), DevOps scripts (launcher scripts, shell wrappers, bootstrap tooling), application-level configuration files, and automated tests. The Builder is the sole author of all implementation files regardless of domain.
*   **Key Duty:** Translating specifications into high-quality, verified code and documenting implementation discoveries.

### The QA Agent
*   **Focus:** "The Verification and The Feedback".
*   **Ownership:** Discovery sidecar files (`features/<name>.discoveries.md`) with exclusive lifecycle management, QA verification scripts (`tests/qa/`), QA scenario authoring (under `### QA Scenarios`), `@auto` tag management, and discovery lifecycle management.
*   **Key Duty:** Executing QA scenarios (auto and manual), recording structured discoveries (BUG, DISCOVERY, INTENT_DRIFT, SPEC_DISPUTE), and tracking their resolution through the lifecycle. QA MAY start servers for verification (port safety + cleanup mandate).
*   **Scenario Writes:** QA MAY add new scenarios under `### QA Scenarios` and add `@auto` tags to existing QA scenarios. QA MUST NOT modify Unit Tests, Requirements, Overview, or Visual Specification sections.
*   **Status Commits:** QA makes `[Complete]` status commits for features that have QA scenarios, after all QA scenarios pass with zero discoveries. Features with no QA scenarios are completed by the Builder.

### The Human Executive
*   **Focus:** "The Intent and The Review".
*   **Duty:** Providing high-level goals, performing final verification (e.g., Hardware-in-the-Loop), and managing the Agentic Evolution.

### Commit Discipline (All Roles)
Agents MUST commit at logical milestones -- never deferring all commits until session end. Implementation work on a single feature MAY be batched into one or a small number of logical commits. Status tag commits (`[Complete]`, `[Ready for Verification]`) MUST remain separate, standalone commits. Commits that trigger downstream Critic regeneration (status tags, spec edits, anchor node edits) MUST be immediate and followed by `{tools_root}/cdd/status.sh`. When in doubt, commit.

## 3. The Lifecycle of a Feature
1.  **Design:** PM and/or Architect creates/refines a feature file in `features/`. When a PM is active, the PM shapes the initial spec and Visual Specification; the Architect validates it during gap analysis.
2.  **Implementation:** Builder reads the feature and implementation notes, writes code/tests, and verifies locally.
3.  **Verification:** QA Agent executes manual scenarios and records discoveries. Human Executive performs final verification as needed. See Section 7.3 for when to invoke QA versus letting the Builder complete features directly.
4.  **Completion:** If the feature has no manual scenarios, the Builder marks `[Complete]`. If it has manual scenarios, the QA Agent marks `[Complete]` after clean verification.
5.  **Synchronization:** Architect updates documentation and regenerates the dependency graph.

## 4. Knowledge Colocation
We do not use a global implementation log. Tribal knowledge, technical "gotchas," and lessons learned are stored in **companion files** (`features/<name>.impl.md`) alongside each feature specification. Feature files themselves do not contain implementation notes.

### 4.1 Anchor Node Taxonomy
The dependency graph uses three types of anchor nodes, distinguished by filename prefix. All three function identically in the dependency system -- they cascade status resets to dependent features and are detected by the Critic for missing prerequisite links. The distinction is semantic, helping agents and humans quickly identify the domain a constraint belongs to.

| Prefix | Domain | Examples |
|--------|--------|----------|
| `arch_*.md` | Technical constraints -- system architecture, data flow, dependency rules, code patterns | `arch_data_layer.md`, `arch_api_contract.md` |
| `design_*.md` | Design constraints -- visual language, typography, spacing, interaction patterns, accessibility | `design_visual_standards.md`, `design_accessibility.md` |
| `policy_*.md` | Governance rules -- process policies, security baselines, compliance requirements, coordination rules | `policy_critic.md`, `policy_security.md` |

Every feature MUST anchor itself to the relevant anchor node(s) via `> Prerequisite:` links.

### 4.2 Cross-Cutting Standards Pattern
When a project has cross-cutting standards that constrain multiple features (visual design, API conventions, security baselines, etc.), represent them using a three-tier structure:

1.  **Anchor Node** (`arch_*.md`, `design_*.md`, or `policy_*.md`) -- Defines the constraints and invariants for the domain.
2.  **Foundation Feature** -- Implements the shared infrastructure that enforces the anchor node's constraints (e.g., CSS custom properties and design tokens, API middleware, security libraries). This feature has a `> Prerequisite:` link to its anchor node.
3.  **Consumer Features** -- Any feature that operates within the standard's domain declares `> Prerequisite:` links to both the anchor node and the foundation feature.

This structure ensures that constraint changes cascade correctly: editing an anchor node file resets all dependent features to `[TODO]`, triggering re-validation across the entire domain. The Critic detects missing prerequisite links, so consumer features that omit the dependency get flagged.

### 4.3 Companion File Convention
Implementation knowledge is stored in **companion files** separate from the feature specification.

*   **File naming:** `features/<name>.impl.md` alongside `features/<name>.md`.
*   **Standalone:** Companion files are standalone -- feature files do NOT reference or link to them. The naming convention provides discoverability.
*   **Not a feature file:** Companion files are NOT feature files. They do not appear in the dependency graph, are not processed by the Spec Gate or Implementation Gate, and are not tracked by the CDD lifecycle.
*   **Status reset exemption:** Edits to `<name>.impl.md` do NOT reset the parent feature's lifecycle status to TODO. Only edits to the feature spec (`<name>.md`) trigger resets. This ensures Builder decisions and tribal knowledge updates do not invalidate completed features.

## 5. The Release Protocol
Releases are synchronization points where the entire project state -- Specs, Architecture, Code, and Process -- is validated and pushed to the remote repository.

## 6. Layered Instruction Architecture

Instructions use a two-layer model: **base** (`instructions/` in the framework) provides core rules; **override** (`.purlin/` in the consumer project) adds project-specific context. At launch, both layers are concatenated (base first, then overrides). Use `/pl-override-edit` for guided override management with built-in conflict scanning.

### Submodule Immutability Mandate
**Agents running in a consumer project MUST NEVER modify any file inside the submodule directory** (e.g., `purlin/`). All project-specific customizations go in `.purlin/` overrides, `features/`, and root-level launcher scripts. If an agent needs to change framework behavior, it MUST use the override layer (`.purlin/*_OVERRIDES.md`), never edit base files.

## 7. User Testing Protocol

### 7.1 Discovery Sidecar Convention
User Testing Discoveries are stored in **sidecar files** (`features/<name>.discoveries.md`) alongside the feature specification (`features/<name>.md`). This separates mutable QA findings from the Architect-owned spec, preventing discovery edits from triggering lifecycle resets.

*   **File naming:** `features/<name>.discoveries.md` alongside `features/<name>.md`.
*   **Not a feature file:** Discovery sidecar files are NOT feature files. They do not appear in the dependency graph, are not processed by the Spec Gate or Implementation Gate, and are not tracked by the CDD lifecycle. The same exclusion rules as companion files (`*.impl.md`) apply.
*   **Status reset exemption:** Edits to `<name>.discoveries.md` do NOT reset the parent feature's lifecycle status to TODO.
*   **Orphan detection:** If `<name>.md` is orphaned, `<name>.discoveries.md` MUST also be flagged.
*   **Content:** A **live queue** of open verification findings. **Any agent** (Architect, Builder, QA, or PM) MAY record a new OPEN discovery. The QA Agent owns **lifecycle management**: verification, resolution confirmation, and pruning of RESOLVED entries.
*   **Queue hygiene:** An empty or absent file means the feature has no open discoveries.

### 7.2 Discovery Types
*   **[BUG]** -- Behavior contradicts an existing scenario.
*   **[DISCOVERY]** -- Behavior exists but no scenario covers it.
*   **[INTENT_DRIFT]** -- Behavior matches the spec literally but misses the actual intent.
*   **[SPEC_DISPUTE]** -- The user disagrees with a scenario's expected behavior. The spec itself is wrong or undesirable.

Discovery lifecycle: `OPEN -> SPEC_UPDATED -> RESOLVED -> PRUNED`. Use `/pl-discovery` for the full recording and lifecycle protocol.

### 7.3 Testing Responsibility Split

The Builder and QA Agent have non-overlapping testing domains. No test is verified twice.

*   **Builder-owned testing:** Unit Tests (`### Unit Tests` section, `/pl-unit-test`) and web tests (`/pl-web-test`). Results are written to `tests.json`. If all scenarios are Unit Tests (no QA scenarios in the spec), the Builder marks `[Complete]` directly -- QA is never invoked.
*   **QA-owned testing:** QA Scenarios (`### QA Scenarios` section). Scenarios are classified as `auto` (`@auto` tag -- QA can run without human judgment) or `manual` (default -- requires human interaction). QA assembles these into a batched checklist via `/pl-verify`, following the auto-first protocol (QA_BASE Section 3.3). Features with BOTH Unit Tests and QA Scenarios: QA auto-credits the Builder's Unit Test results and presents only the QA items.
*   **Handoff signal:** `[Ready for Verification]` = QA scenarios exist, QA needed. `[Complete]` = Builder verified everything (Unit Tests only), QA not needed.
*   **Dedup invariant:** QA MUST NOT re-verify Builder-completed Unit Tests. The auto-pass in QA startup (Step 1 of QA_BASE Section 3.3) enforces this.
*   **Tier-based prioritization:** Consumer projects MAY define test priority tiers (`smoke`, `standard`, `full-only`) in `QA_OVERRIDES.md`. QA reads the tier table and orders verification accordingly. "Just smoke" mode filters to smoke-tier only. See QA_BASE Section 3.2 for details.

## 8. Protocol Quick Reference

| When you need to... | Do this |
|---------------------|---------|
| Implement a feature | Invoke `/pl-build` |
| Understand Critic status | Run `{tools_root}/cdd/status.sh --role <role>` or invoke `/pl-status` |
| Create/refine a spec | Invoke `/pl-spec` |
| Create/update an anchor node | Invoke `/pl-anchor` |
| Record a QA discovery | Invoke `/pl-discovery` |
| Handle phased delivery | Invoke `/pl-delivery-plan` |
| Verify a feature (QA) | Invoke `/pl-verify` |
| Mark feature complete (QA) | Invoke `/pl-complete` |
| Edit override files | Invoke `/pl-override-edit` |

Skills carry the complete workflow protocol. Invoke the skill before executing the workflow.

## 9. Critic-Driven Coordination
The Critic is the project coordination engine. It validates quality AND generates role-specific action items. Every agent runs the Critic at session start by invoking `{tools_root}/cdd/status.sh`, which automatically runs the Critic as a prerequisite and writes the aggregate report to `CRITIC_REPORT.md`. Each agent reads their role-specific subsection of that report before beginning work. The Critic is never invoked via HTTP — agents use the CLI interface exclusively.

*   **CDD (Continuous Design-Driven) Monitor** shows what IS (per-role status: Architect, Builder, QA, PM columns).
*   **Critic** shows what SHOULD BE DONE (role-specific action items).
*   Agents consult `CRITIC_REPORT.md` for their role-specific priorities before starting work.
*   CDD does NOT run the Critic. CDD reads pre-computed `role_status` from on-disk `critic.json` files to display role-based columns on the dashboard and in the `/status.json` API.
*   **Agent Interface:** Agents access tool data via CLI commands (`{tools_root}/cdd/status.sh`, `{tools_root}/cdd/status.sh --graph`, `{tools_root}/critic/run.sh`), never via HTTP servers. The CDD Dashboard web server is for human use only. This ensures agents can always access current data without depending on server state.

### 9.1 What the Critic Validates
The Critic applies a **dual-gate model** to every feature:

*   **Spec Gate (pre-implementation):** Validates that required spec sections are present, scenarios are well-formed, and prerequisite anchor nodes are declared. This gate runs regardless of feature lifecycle status and is the primary signal for Architect action items.
*   **Implementation Gate (post-implementation):** Validates that automated tests trace to their Gherkin scenarios (traceability), that code does not violate FORBIDDEN patterns from anchor nodes (policy adherence), and optionally checks for LLM-detected logic drift (disabled by default, configurable via `config.json`).

In addition to the dual-gate, the Critic runs these supplementary audits on every pass:

*   **User Testing Audit:** Counts open BUG, DISCOVERY, INTENT_DRIFT, and SPEC_DISPUTE entries in discovery sidecar files (`features/*.discoveries.md`). Each entry is routed to the responsible role's action items.
*   **Builder Decision Audit:** Scans companion files (`features/*.impl.md`) for unacknowledged `[DEVIATION]` and `[DISCOVERY]` tags. These are flagged as HIGH-priority Architect action items.
*   **Visual Specification Detection:** Detects `## Visual Specification` sections and surfaces visual checklist items as QA action items for the visual verification pass.
*   **Untracked File Audit:** Checks git status for untracked files in Architect-owned directories and flags them as MEDIUM-priority Architect triage items.

### 9.2 Role-Specific Action Items
Per-feature Critic results are written to `tests/<feature>/critic.json`. Aggregate results across all features are written to `CRITIC_REPORT.md`, organized by role.

**Priority levels:**
*   **CRITICAL:** INFEASIBLE escalation; the release is blocked until resolved.
*   **HIGH:** Gate FAIL, open BUG entries, unacknowledged builder decisions, SPEC_DISPUTE.
*   **MEDIUM:** Traceability gaps, gate warnings, untracked files.
*   **LOW:** Informational warnings that do not block release.

**Role routing:**
*   **Architect:** Spec gaps (Spec Gate FAIL), INFEASIBLE escalations from Builder, unacknowledged builder decisions, untracked files, SPEC_DISPUTEs on Architect-owned features.
*   **Builder:** Features in TODO lifecycle, failing automated tests, traceability gaps, open BUG entries.
*   **QA:** Features in TESTING lifecycle, SPEC_UPDATED discoveries awaiting re-verification, visual verification passes.
*   **PM:** SPEC_DISPUTEs on PM-owned features or Visual Specification screens, stale/missing/unprocessed design artifacts.

Automated test status is embedded in role columns: Builder `DONE` implies tests passed; QA `CLEAN` requires `tests.json` with `status: "PASS"`; QA `N/A` means no test coverage exists.

### 9.3 Work Discovery Authority
When users ask about pending work, action items, tasks, or next steps — phrasing like "what do I have to do?", "what tasks are available?", "what's next?", "what needs work?" — the agent MUST interpret this as a request for the Critic report, not Claude Code's built-in task system. All work items are discovered exclusively through `{tools_root}/cdd/status.sh`, which generates `CRITIC_REPORT.md` with role-specific action items.

**Guardrail:** Do NOT use Claude Code's built-in TaskList, TaskGet, TaskCreate, or TaskUpdate tools for Purlin work discovery. Route all "what work do I have" queries through `/pl-status` or the role's startup protocol (`{tools_root}/cdd/status.sh --startup <role>`).

## 9. Visual Specification Convention

Feature files MAY contain a `## Visual Specification` section for features with visual/UI
components. This section uses per-screen checklists (not Gherkin) with design anchor
references. It is exempt from Gherkin traceability. The PM agent is the primary author of
Visual Specification sections. When a PM is active, the Architect defers visual spec
authoring to the PM and focuses on structural validation. The Critic detects visual spec
sections and generates QA action items for visual verification.

For the full convention (format, inheritance, design pipeline, verification methods), see
`instructions/references/visual_spec_convention.md`. Use `/pl-verify` for the complete visual verification protocol.

## 10. Phased Delivery Protocol

Large-scope changes may be split into numbered delivery phases to organize work into testable
blocks and enable parallel delivery. The delivery plan artifact lives at
`.purlin/delivery_plan.md`. QA MUST NOT mark a feature as `[Complete]` if it appears in
any PENDING phase of the delivery plan. Use `/pl-delivery-plan` for the full phased delivery
protocol (format, sizing, cross-session resumption, QA interaction).
