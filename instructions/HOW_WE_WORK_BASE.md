# How We Work: The Agentic Workflow

> **Layered Instructions:** This file is the **base layer** of the workflow philosophy, provided by the Purlin framework. Project-specific workflow additions are defined in the **override layer** at `.agentic_devops/HOW_WE_WORK_OVERRIDES.md`. At runtime, both layers are concatenated (base first, then overrides).

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

## 2. Roles and Responsibilities

### The Architect Agent
*   **Focus:** "The What and The Why".
*   **Ownership:** Architectural Policies, Feature Specifications, instruction overrides, and DevOps process scripts (launcher scripts, shell wrappers, bootstrap tooling).
*   **Key Duty:** Designing rigorous, unambiguous specifications and enforcing architectural invariants.

### The Builder Agent
*   **Focus:** "The How".
*   **Ownership:** Implementation code, tests, and DevOps tool implementation (Python logic, test suites).
*   **Key Duty:** Translating specifications into high-quality, verified code and documenting implementation discoveries.

### The QA Agent
*   **Focus:** "The Verification and The Feedback".
*   **Ownership:** `## User Testing Discoveries` section in feature files (exclusive write access), manual verification execution, discovery lifecycle management.
*   **Key Duty:** Executing manual Gherkin scenarios, recording structured discoveries (BUG, DISCOVERY, INTENT_DRIFT, SPEC_DISPUTE), and tracking their resolution through the lifecycle.
*   **Does NOT:** Write or modify application/tool code (Builder), or modify Gherkin scenarios or requirements (Architect).
*   **Status Commits:** QA makes `[Complete]` status commits for features that have manual scenarios, after all manual scenarios pass with zero discoveries. Features with no manual scenarios are completed by the Builder.

### The Human Executive
*   **Focus:** "The Intent and The Review".
*   **Duty:** Providing high-level goals, performing final verification (e.g., Hardware-in-the-Loop), and managing the Agentic Evolution.

## 3. The Lifecycle of a Feature
1.  **Design:** Architect creates/refines a feature file in `features/`.
2.  **Implementation:** Builder reads the feature and implementation notes, writes code/tests, and verifies locally.
3.  **Verification:** QA Agent executes manual scenarios and records discoveries. Human Executive performs final verification as needed.
4.  **Completion:** If the feature has no manual scenarios, the Builder marks `[Complete]`. If it has manual scenarios, the QA Agent marks `[Complete]` after clean verification.
5.  **Synchronization:** Architect updates documentation and regenerates the dependency graph.

## 4. Knowledge Colocation
We do not use a global implementation log. Tribal knowledge, technical "gotchas," and lessons learned are stored directly in the `## Implementation Notes` section at the bottom of each feature file.

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
Implementation Notes may be extracted to a separate **companion file** to reduce feature file size and context window usage.

*   **File naming:** `features/<name>.impl.md` alongside `features/<name>.md`.
*   **Stub format:** When a companion file exists, the feature file's `## Implementation Notes` section is reduced to: `See [<name>.impl.md](<name>.impl.md) for implementation knowledge, builder decisions, and tribal knowledge.`
*   **Not a feature file:** Companion files are NOT feature files. They do not appear in the dependency graph, are not processed by the Spec Gate or Implementation Gate, and are not tracked by the CDD lifecycle.
*   **Status reset exemption:** Edits to `<name>.impl.md` do NOT reset the parent feature's lifecycle status to TODO. Only edits to the feature spec (`<name>.md`) trigger resets. This ensures Builder decisions and tribal knowledge updates do not invalidate completed features.
*   **Backward compatibility:** Features with inline Implementation Notes (no companion file) continue to work unchanged.

## 5. The Release Protocol
Releases are synchronization points where the entire project state -- Specs, Architecture, Code, and Process -- is validated and pushed to the remote repository.

### 5.1 Milestone Mutation (The "Single Release File" Rule)
We do not maintain a history of release files in the project's features directory.
1. There is exactly ONE active Release Specification file.
2. When moving to a new release, the Architect **renames** the existing release file to the new version and updates the objectives.
3. The previous release's tests are preserved as **Regression Tests** in the new file.
4. Historical release data is tracked via `PROCESS_HISTORY.md` and the project's root `README.md`.

## 6. Layered Instruction Architecture

### Overview
The Purlin framework uses a two-layer instruction model to separate framework rules from project-specific context:

*   **Base Layer** (`instructions/` directory in the framework): Contains the framework's core rules, protocols, and philosophies. These are read-only from the consumer project's perspective and are updated by pulling new versions of the framework.
*   **Override Layer** (`.agentic_devops/` directory in the consumer project): Contains project-specific customizations, domain context, and workflow additions. These are owned and maintained by the consumer project.

### How It Works
At agent launch time, the launcher scripts (`run_claude_architect.sh`, `run_claude_builder.sh`, `run_claude_qa.sh`) concatenate the base and override files into a single prompt:

1. Base HOW_WE_WORK is loaded first (framework philosophy).
2. Role-specific base instructions are appended (framework rules).
3. HOW_WE_WORK overrides are appended (project workflow additions).
4. Role-specific overrides are appended (project-specific rules).

This ordering ensures that project-specific rules can refine or extend (but not silently contradict) the framework's base rules.

### Submodule Consumption Pattern
When used as a git submodule (e.g., at `purlin/`):
1. The submodule provides the base layer (`purlin/instructions/`) and all tools (`purlin/tools/`).
2. The consumer project runs `purlin/tools/bootstrap.sh` to initialize `.agentic_devops/` with override templates.
3. Tools resolve their paths via `tools_root` in `.agentic_devops/config.json`.
4. Upstream updates are pulled via `cd purlin && git pull origin main && cd ..` and audited with `purlin/tools/sync_upstream.sh`.

### Submodule Immutability Mandate
**Agents running in a consumer project MUST NEVER modify any file inside the submodule directory** (e.g., `purlin/`). The submodule is a read-only dependency. Specifically:
*   **NEVER** edit files in `<submodule>/instructions/`, `<submodule>/tools/`, `<submodule>/features/`, or any other path inside the submodule.
*   **NEVER** commit changes to the submodule from a consumer project. The submodule is only modified from its own repository.
*   All project-specific customizations go in the consumer project's own files: `.agentic_devops/` overrides, `features/`, and root-level launcher scripts.
*   If an agent needs to change framework behavior, it MUST do so via the override layer (`.agentic_devops/*_OVERRIDES.md`), never by editing base files.

### Override Management Protocol

**Override File Ownership (Role-Scoped Write Access):**

Each override file has a designated set of agents permitted to modify it:

| Override File | Who May Edit |
|---|---|
| `.agentic_devops/HOW_WE_WORK_OVERRIDES.md` | Architect only |
| `.agentic_devops/ARCHITECT_OVERRIDES.md` | Architect only |
| `.agentic_devops/BUILDER_OVERRIDES.md` | Builder (own) and Architect |
| `.agentic_devops/QA_OVERRIDES.md` | QA (own) and Architect |

No agent may modify another agent's exclusive override file. The Architect has universal override access as the process owner.

**Base File Protection:**

Consumer project agents MUST NOT modify base instruction files under any circumstances — governed by the Submodule Immutability Mandate above. If a consumer project needs to change framework behavior, changes go into the appropriate override file in `.agentic_devops/`.

Agents in the Purlin framework's own repository (not a consumer project) may modify base files, but MUST use `/pl-edit-base` to do so. Direct editing without this command is prohibited.

**Override Editing Rules (apply in all contexts):**
1. Read existing content first. Never overwrite without reading.
2. Additive only. Do not delete or contradict existing rules.
3. No contradictions with base. Surface conflicts with `/pl-override-conflicts` before committing.
4. No code or script content. Override files are prose instruction documents only.
5. Commit after editing.
6. Architect: update `PROCESS_HISTORY.md` when the change affects workflow.

**Commands:** `/pl-override-edit` (role-scoped edit), `/pl-override-conflicts` (conflict scan, all roles), `/pl-edit-base` (base file edit — Purlin repo only, never distributed to consumers).

### Path Resolution Conventions
In a submodule setup, the project tree contains two `features/` directories and two `tools/` directories. The following conventions prevent ambiguity:

*   **`features/` directory:** Always refers to `<project_root>/features/` -- the **consumer project's** feature specs. In a submodule setup, this is NOT the framework submodule's own `features/` directory. The framework's features are internal to the submodule and are not scanned by consumer project tools.
*   **`tools/` references:** All `tools/` references in instruction files are shorthand that resolves against the `tools_root` value from `.agentic_devops/config.json`. In standalone mode, `tools_root` is `"tools"`. In submodule mode, `tools_root` is `"<submodule>/tools"` (e.g., `"purlin/tools"`). Agents MUST read `tools_root` from config before constructing tool paths -- do NOT assume `tools/` is a direct child of the project root.
*   **`AGENTIC_PROJECT_ROOT`:** All launcher scripts (both standalone and bootstrap-generated) export this environment variable as the authoritative project root. All Python and shell tools check this variable first, falling back to directory-climbing detection only when it is not set.

## 7. User Testing Protocol

### 7.1 Discovery Section Convention
Feature files MAY contain a `## User Testing Discoveries` section as the last section before the end of the file. This section is a **live queue** of open verification findings. **Any agent** (Architect, Builder, or QA) MAY record a new OPEN discovery when they encounter a bug or unexpected behavior during their work. The QA Agent owns the **lifecycle management** of the section: verification, resolution confirmation, and pruning of RESOLVED entries.

### 7.2 Discovery Types
*   **[BUG]** -- Behavior contradicts an existing scenario.
*   **[DISCOVERY]** -- Behavior exists but no scenario covers it.
*   **[INTENT_DRIFT]** -- Behavior matches the spec literally but misses the actual intent.
*   **[SPEC_DISPUTE]** -- The user disagrees with a scenario's expected behavior. The spec itself is wrong or undesirable.

### 7.3 Discovery Lifecycle
Status progression: `OPEN -> SPEC_UPDATED -> RESOLVED -> PRUNED`

*   **OPEN:** Any agent records the finding.
*   **SPEC_UPDATED:** Architect updates Gherkin scenarios to address it.
*   **RESOLVED:** Builder re-implements, QA re-verifies and confirms fix.
*   **PRUNED:** QA removes entry from Discoveries, adds one-liner to Implementation Notes. Git history preserves full record.

### 7.4 Queue Hygiene
*   The section only contains OPEN and SPEC_UPDATED entries (active work).
*   RESOLVED entries are pruned by the QA Agent.
*   An empty `## User Testing Discoveries` section (or its absence) means the feature is clean.

### 7.5 Feedback Routing

**From User Testing Discoveries (any agent may record, routed by type):**
*   **BUG** -> Builder must fix implementation. **Exception:** when the BUG is in instruction-file-driven agent behavior (startup protocol ordering, role compliance, slash command gating), the recorder MUST set `Action Required: Architect` in the discovery entry. The Architect fixes it by strengthening the relevant instruction file. The Critic routes BUG action items by reading the `Action Required` field — the default is Builder, but `Action Required: Architect` overrides this for instruction-level bugs.
*   **DISCOVERY** -> Architect must add missing scenarios, then Builder re-implements.
*   **INTENT_DRIFT** -> Architect must refine scenario intent, then Builder re-implements.
*   **SPEC_DISPUTE** -> Architect must review the disputed scenario with the user and revise or reaffirm it. The scenario is **suspended** (QA skips it) until the Architect resolves the dispute.

**Builder-to-Architect (from Implementation):**
*   **INFEASIBLE** -> The feature cannot be implemented as specified (technical constraints, contradictory requirements, or dependency issues). Builder halts work on the feature, records a detailed rationale in Implementation Notes, and skips to the next feature. Architect must revise the spec before the Builder can resume.

## 8. Critic-Driven Coordination
The Critic is the project coordination engine. It validates quality AND generates role-specific action items. Every agent runs the Critic at session start by invoking `tools/cdd/status.sh`, which automatically runs the Critic as a prerequisite and writes the aggregate report to `CRITIC_REPORT.md`. Each agent reads their role-specific subsection of that report before beginning work. The Critic is never invoked via HTTP — agents use the CLI interface exclusively.

*   **CDD (Continuous Design-Driven) Monitor** shows what IS (per-role status: Architect, Builder, QA columns).
*   **Critic** shows what SHOULD BE DONE (role-specific action items).
*   Agents consult `CRITIC_REPORT.md` for their role-specific priorities before starting work.
*   CDD does NOT run the Critic. CDD reads pre-computed `role_status` from on-disk `critic.json` files to display role-based columns on the dashboard and in the `/status.json` API.
*   **Agent Interface:** Agents access tool data via CLI commands (`tools/cdd/status.sh`, `tools/cdd/status.sh --graph`, `tools/critic/run.sh`), never via HTTP servers. The CDD Dashboard web server is for human use only. This ensures agents can always access current data without depending on server state.

### 8.1 What the Critic Validates
The Critic applies a **dual-gate model** to every feature:

*   **Spec Gate (pre-implementation):** Validates that required spec sections are present, scenarios are well-formed, and prerequisite anchor nodes are declared. This gate runs regardless of feature lifecycle status and is the primary signal for Architect action items.
*   **Implementation Gate (post-implementation):** Validates that automated tests trace to their Gherkin scenarios (traceability), that code does not violate FORBIDDEN patterns from anchor nodes (policy adherence), and optionally checks for LLM-detected logic drift (disabled by default, configurable via `config.json`).

In addition to the dual-gate, the Critic runs these supplementary audits on every pass:

*   **User Testing Audit:** Counts open BUG, DISCOVERY, INTENT_DRIFT, and SPEC_DISPUTE entries in `## User Testing Discoveries` sections. Each entry is routed to the responsible role's action items.
*   **Builder Decision Audit:** Scans `## Implementation Notes` for unacknowledged `[DEVIATION]` and `[DISCOVERY]` tags. These are flagged as HIGH-priority Architect action items.
*   **Visual Specification Detection:** Detects `## Visual Specification` sections and surfaces visual checklist items as QA action items for the visual verification pass.
*   **Untracked File Audit:** Checks git status for untracked files in Architect-owned directories and flags them as MEDIUM-priority Architect triage items.

### 8.2 Role-Specific Action Items
Per-feature Critic results are written to `tests/<feature>/critic.json`. Aggregate results across all features are written to `CRITIC_REPORT.md`, organized by role.

**Priority levels:**
*   **CRITICAL:** INFEASIBLE escalation; the release is blocked until resolved.
*   **HIGH:** Gate FAIL, open BUG entries, unacknowledged builder decisions, SPEC_DISPUTE.
*   **MEDIUM:** Traceability gaps, gate warnings, untracked files.
*   **LOW:** Informational warnings that do not block release.

**Role routing:**
*   **Architect:** Spec gaps (Spec Gate FAIL), INFEASIBLE escalations from Builder, unacknowledged builder decisions, untracked files.
*   **Builder:** Features in TODO lifecycle, failing automated tests, traceability gaps, open BUG entries.
*   **QA:** Features in TESTING lifecycle, SPEC_UPDATED discoveries awaiting re-verification, visual verification passes.

### 8.3 Automated Test Status in the CDD Dashboard
Automated test results are NOT reported as a separate column. They are surfaced through the existing Builder and QA role columns:

*   **Builder column:** `DONE` means the spec is structurally complete and no open BUGs exist (automated tests passed). `FAIL` means `tests/<feature>/tests.json` exists with `status: "FAIL"` (automated tests failed).
*   **QA column:** `CLEAN` requires `tests/<feature>/tests.json` to exist with `status: "PASS"` (automated tests exist and passed). `N/A` means no `tests.json` exists (no automated test coverage).

In short: Builder `DONE` implies automated tests passed. QA `CLEAN` vs `N/A` signals whether automated test coverage exists at all. There is no separate "test status" indicator -- automated test health is embedded in the role status model.

## 9. Visual Specification Convention

### 9.1 Purpose
Feature files MAY contain a `## Visual Specification` section for features with visual/UI components. This section provides checklist-based visual acceptance criteria with optional design asset references, distinct from functional Gherkin scenarios.

### 9.2 Section Format
The section is placed between `## Implementation Notes` (or its stub -- see Section 4.3) and `## User Testing Discoveries` (or at the end of the file if no discoveries section exists):

```markdown
## Visual Specification

### Screen: <Screen Name>
- **Reference:** [Figma](<url>) | `docs/mockups/<file>` | N/A
- [ ] <Visual acceptance criterion 1>
- [ ] <Visual acceptance criterion 2>
```

**Key properties:**
*   **Optional** -- only present when the feature has a visual/UI component.
*   **Per-screen subsections** -- one feature can have multiple screens, each as a `### Screen:` subsection.
*   **Design asset references** -- Figma URLs, local PDF/image paths, or "N/A" when no reference exists.
*   **Checklist format** -- not Gherkin. Subjective visual checks are better as checkboxes than Given/When/Then.
*   **Separate from functional scenarios** -- QA can batch all visual checks across features instead of interleaving with functional verification.

### 9.3 Ownership and Traceability
*   The `## Visual Specification` section is **Architect-owned** (like the rest of the spec). QA does NOT modify it.
*   Visual specification items are **exempt from Gherkin traceability**. They do not require automated scenarios or test functions.
*   The Critic detects visual spec sections and generates separate QA action items for visual verification.

### 9.4 Design Asset Storage
*   Design assets referenced by visual specs may be stored as project-local files (e.g., `docs/mockups/`) or as external URLs (e.g., Figma links).
*   Local file paths are relative to the project root.
*   There is no mandatory storage location -- projects choose what fits their workflow.

### 9.5 Verification Methods
Visual checklist items are verified by the QA Agent during the visual verification pass (QA_BASE Section 5.4). The QA Agent MAY use screenshot-assisted verification: the user provides screenshots and the agent auto-checks items verifiable from a static image (layout, positioning, typography, color). Items requiring interaction, temporal observation, or implementation inspection are confirmed manually by the human tester.

### 9.6 Visual vs Functional Classification
When a feature has UI components, the Architect MUST classify each acceptance criterion:

*   **Visual Specification** (checklist item): Verifiable from a static screenshot -- layout, colors, typography, element presence/absence, spacing. No interaction required.
*   **Manual Scenario** (Gherkin): Requires user interaction (clicks, hovers, typing), temporal observation (waiting for refresh/animation), or multi-step functional verification (start server, trigger action, observe result).

The goal is to **minimize Manual Scenarios** by moving all static visual checks to the Visual Specification section. Manual Scenarios should only test behavior that cannot be verified from a screenshot.

## 10. Phased Delivery Protocol

### 10.1 Purpose
When the Architect introduces large-scale changes (multiple new feature files, major revisions across existing features), the Builder may need to split work across multiple sessions to manage context window limits and ensure quality. The Phased Delivery Protocol provides a persistent coordination artifact that lets the Builder propose splitting work into numbered phases, each producing a testable state. The user orchestrates the cycle: Builder (Phase 1) -> QA (verify Phase 1) -> Builder (fix bugs + Phase 2) -> QA -> ... until complete.

### 10.2 The Delivery Plan Artifact
*   **Path:** `.agentic_devops/cache/delivery_plan.md`
*   **Created by:** Builder, when user approves phased delivery.
*   **Committed to git:** Yes (all agents read it across sessions).
*   **Deleted by:** Builder, when the final phase completes.
*   **Format:** The plan contains a summary, numbered phases (each with status, feature list, completion commit, and QA bugs addressed), and a plan amendments section. Phase statuses are PENDING, IN_PROGRESS, or COMPLETE. Exactly one phase may be IN_PROGRESS at a time. COMPLETE phases are immutable historical record.
*   **Intra-Feature Phasing:** A feature MAY appear in multiple phases. Targeted delivery within a feature uses the existing `[Scope: targeted:...]` mechanism. No new scope types are needed.

### 10.3 Cross-Session Resumption
When a delivery plan exists at session start, the Builder resumes from the next PENDING phase. QA bugs recorded during prior phases are addressed first, before new phase work begins. If the IN_PROGRESS phase was interrupted mid-session, the Builder resumes that phase, skipping features already in TESTING state.

### 10.4 QA Interaction
The QA Agent MUST check for a delivery plan at `.agentic_devops/cache/delivery_plan.md` during startup. If the plan exists, QA classifies each TESTING feature as either "fully delivered" (appears only in COMPLETE phases) or "more work coming" (appears in a PENDING phase). QA MUST NOT mark a feature as `[Complete]` if it appears in any PENDING phase of the delivery plan, even if all currently-delivered scenarios pass. QA informs the user which features are phase-gated.

### 10.5 Phasing is Optional
Phased delivery is never automatic. The Builder proposes phasing based on scope assessment heuristics, and the user always decides whether to accept phasing, modify the phase breakdown, or proceed with a single-session delivery. At any approval checkpoint, the user may collapse remaining phases, re-split, or abandon phasing entirely.

### 10.6 Architect Awareness
If the Architect modifies feature specs while a delivery plan is active, the Builder detects the mismatch on resume and proposes a plan amendment. Minor changes (added scenarios, clarified requirements) are auto-updated. Major changes (new features, removed phases, restructured dependencies) require user approval before continuing.

### 10.7 CDD Dashboard Integration
When a delivery plan exists, the CDD Dashboard's ACTIVE section heading displays the current phase progress as an inline annotation: `ACTIVE (<count>) [PHASE (<current>/<total>)]`. The `/status.json` API and CLI tool include an optional `delivery_phase` field with `current` and `total` values. When all phases are COMPLETE or no delivery plan exists, the phase annotation and API field are omitted.
