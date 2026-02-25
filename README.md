# Purlin

![Purlin Logo](assets/purlin-logo.svg)

**Collaborative Design-Driven Agentic Development Framework**

[![Watch the video](https://img.youtube.com/vi/ob7_RzriVdI/maxresdefault.jpg)](https://youtu.be/ob7_RzriVdI)

## Overview

Purlin is a **Collaborative Design-Driven** development framework. Designs evolve in sync with code -- never ahead of it, never behind it. Specifications are living documents that are continuously refined as implementation reveals new constraints and insights.

The framework is built on four goals:

1. **Coordinate specialized agents** following a spec/test-driven framework for deterministic outcomes.
2. **Specifications and tests are the backbone** -- code is disposable. If specs are rigorous enough, any compliant agent can rebuild the entire system from scratch.
3. **Enable real people to bring expertise, amplified through agents** -- replaces meetings and ceremonies with structured, async collaboration.
4. **Code is more provably correct** with least drift from specifications.

By colocating technical implementation knowledge with behavioral specifications (Gherkin), the framework ensures that system context is never lost and that codebases can be reliably rebuilt or refactored by AI agents with minimal human intervention.

## Screenshots

*(From v0.6.0)*

**CDD Dashboard**
![CDD Dashboard](assets/PurlinCDDV0.6.0.png)

**CDD Spec Map**
![CDD Spec Map](assets/PurlinSpecMapV0.6.0.png)

**Purlin Example Workspace**
![Purlin Example Workspace](assets/PurlinWorkspaceV0.6.0.png)

## Core Concepts

### 1. Collaborative Design-Driven
The project's state is defined 100% by specification files, and those specifications evolve continuously with the code:
*   **Anchor Nodes (`arch_*.md`, `design_*.md`, `policy_*.md`):** Define the constraints of the system -- technical architecture, design standards, and governance policies. Changes cascade to all dependent features.
*   **Living Specifications (`*.md`):** Behavioral requirements (Gherkin) coupled with Implementation Notes (Tribal Knowledge). Refined through every implementation cycle -- not written once and handed off.
*   **Code is disposable; design is durable.** If all source code were deleted, the specs must be sufficient to rebuild. When code reveals new truths, the design is updated first.

### 2. Role Separation
The framework defines three distinct agent roles:
*   **The Architect:** Owns "The What and The Why." Designs specifications and enforces architectural integrity.
*   **The Builder:** Owns "The How." Implements code and tests based on specifications and documents discoveries.
*   **The QA Agent:** Owns "The Verification and The Feedback." Executes manual scenarios, records structured discoveries, and tracks their resolution.

### 3. Knowledge Colocation
Instead of separate documentation or global logs, implementation discoveries, hardware constraints, and design decisions are stored directly within the feature specifications they pertain to.

*   **Companion files (`*.impl.md`):** Implementation knowledge is stored in companion files (`<name>.impl.md`) alongside the feature spec. Companion files are standalone -- the naming convention provides discoverability without requiring links from the spec. Knowledge stays colocated -- one directory listing away from its requirements -- without bloating the spec file.
*   **Visual Specifications:** Features with UI components may include a `## Visual Specification` section with per-screen checklists and design asset references (Figma URLs, local mockups). These are Architect-owned and exempt from Gherkin traceability. They give the QA Agent a separate verification track for static appearance checks -- layout, color, typography -- distinct from interactive scenario execution.

### 4. Layered Instruction Architecture
The framework separates **framework rules** (base layer) from **project-specific context** (override layer):
*   **Base Layer** (`purlin/instructions/` in your project): Core rules, protocols, and philosophies. Stays inside the Purlin submodule -- never copied to your project. Consumed directly by the launcher scripts at runtime.
*   **Override Layer** (`.purlin/` in your project root): Project-specific customizations, domain context, and workflow additions. Created by the bootstrap script and committed to your project.

At launch, the generated launcher scripts concatenate base + override files into a single agent prompt. This allows upstream Purlin updates without merge conflicts in your project-specific configuration.

## The Agents

### File Access Permissions

The framework enforces three ownership types: **specification** (Architect), **implementation** (Builder), and **verification** (QA). Each file category has explicit access rules per role.

**Permission key:** C = Create, R = Read, W = Write/Modify, D = Delete

| File Category | Path Pattern | Architect | Builder | QA |
|---|---|---|---|---|
| Feature specs | `features/*.md` (excl. `*.impl.md`, `tombstones/`) | CRWD | R | R |
| Anchor nodes | `features/arch_*.md`, `design_*.md`, `policy_*.md` | CRWD | RW | R |
| Companion files | `features/*.impl.md` | CR | CRWD | RW |
| Tombstone files | `features/tombstones/*.md` | CRD | RD | R |
| Override: HOW_WE_WORK, ARCHITECT | `.purlin/HOW_WE_WORK_OVERRIDES.md`, `ARCHITECT_OVERRIDES.md` | RW | R | R |
| Override: BUILDER | `.purlin/BUILDER_OVERRIDES.md` | RW | RW | R |
| Override: QA | `.purlin/QA_OVERRIDES.md` | RW | R | RW |
| README / prose docs | `README.md`, `docs/**/*.md` | RW | R | R |
| Process config | `.gitignore`, `.purlin/release/*.json`, `.purlin/config.json` | RW | R | R |
| Test results | `tests/<feature>/tests.json` | R | CRW | R |
| QA verification scripts | `tests/qa/**` | R | R | CRWD |
| Tool-generated files | `critic.json`, `CRITIC_REPORT.md`, `dependency_graph.json` | R | R | R |
| Delivery plan | `.purlin/cache/delivery_plan.md` | R | CRWD | R |
| Discovery sections | `## User Testing Discoveries` in feature files | RW | CRW | CRW |
| Your project code | All files outside Purlin-managed paths | R | CRWD | R |
| Purlin submodule | `purlin/**` | — | — | — |

**Notes:**
- **Purlin-managed paths:** `features/`, `.purlin/`, `tests/`, `purlin/` (submodule), and root-level prose docs (`README.md`, `docs/`). Everything outside these paths is "your project code."
- **Your project code** covers all source files, scripts, configuration files, automated tests, and other artifacts regardless of language, location, or file extension. The Builder has full ownership; the Architect and QA have read access.
- **Instruction files** (`instructions/*.md`) live inside the Purlin submodule and are read-only for consumer projects. In the Purlin framework repository itself, the Architect has write access via `/pl-edit-base`.
- Builder anchor node writes are limited to `[DISCOVERY]` tags in companion files.
- QA companion file writes are limited to pruning one-liners.
- Builder and QA may both create (`C`) the `## User Testing Discoveries` section if it doesn't exist.
- QA verification scripts (`tests/qa/`) are QA-exclusive -- the Builder and Architect read but do not modify.
- Tool-generated files are produced by `tools/cdd/status.sh` or `tools/critic/run.sh` -- no agent writes directly.

### Shared Commands

| Command | Description |
|---|---|
| `/pl-status` | Check CDD status and role-specific action items |
| `/pl-find <topic>` | Discover where a topic belongs in the spec system |
| `/pl-override-edit` | Edit an override file (role-scoped: Builder/QA can only edit their own file; Architect can edit any) |
| `/pl-override-conflicts` | Check an override file against its base layer for contradictions |
| `/pl-agent-config [<role>] <key> <value>` | Modify agent config in `.purlin/config.json` safely (routes to main project config from isolated worktrees) |
| `/pl-local-push` | Merge isolation branch to main -- runs pre-merge handoff checklist (isolated sessions only) |
| `/pl-local-pull` | Pull latest commits from main into the current isolation branch (isolated sessions only) |

---

### The Architect

The Architect owns the specification system. All feature requirements, architectural constraints, and governance rules flow through this role. Code is never written here -- only the specs that make code possible.

| Command | Description |
|---|---|
| `/pl-spec <topic>` | Add or refine a feature spec (routes to edit or create after discovery) |
| `/pl-anchor <topic>` | Create or update an architectural, design, or policy anchor node |
| `/pl-tombstone <name>` | Retire a feature -- checks dependents, generates tombstone for Builder |
| `/pl-release-check` | Execute the CDD-controlled release checklist step by step |
| `/pl-release-run [<step>]` | Run a single release step by name without the full checklist |
| `/pl-release-step [create\|modify\|delete]` | Create, modify, or delete a local release step |
| `/pl-spec-code-audit` | Bidirectional spec-code audit -- finds spec gaps and code-side deviations |
| `/pl-edit-base` | Modify a base instruction file (Purlin repo only -- not distributed to consumer projects) |

**Workflow examples:**

*Adding a new capability:*
```
/pl-find "webhook delivery retries"
→ Agent: "Nothing exists. A new spec makes sense."
/pl-spec "webhook delivery retries"
→ Agent scaffolds feature with Gherkin template, prerequisite stubs
```

*Retiring a deprecated feature:*
```
/pl-tombstone legacy_notifications
→ Agent: "3 features reference this. Here's the impact. Confirm?"
→ Tombstone created, feature file deleted, commit staged
```

---

### The Builder

The Builder translates specifications into working code and tests. It owns the implementation -- never the requirements. When a spec is impossible to implement as written, the Builder escalates rather than improvising.

| Command | Description |
|---|---|
| `/pl-build [name]` | Implement pending work from the Critic backlog, or a named feature |
| `/pl-delivery-plan` | Create or review a phased delivery plan for large backlogs |
| `/pl-infeasible <name>` | Escalate a feature as unimplementable -- pauses work, notifies Architect |
| `/pl-propose <topic>` | Surface a spec change suggestion to the Architect as a structured proposal |
| `/pl-spec-code-audit` | Bidirectional spec-code audit -- finds spec gaps and code-side deviations |

**Workflow examples:**

*Standard build cycle:*
```
/pl-build
→ Agent reads Critic report, checks tombstones, begins highest-priority feature
```

*Large backlog needing phasing:*
```
/pl-delivery-plan
→ Agent: "6 TODO features. Dependency ordering suggests 3 phases:
   Phase 1 (foundation): policy_critic, python_environment
   Phase 2 (core tools): critic_tool, cdd_status_monitor
   Phase 3 (release): release_checklist_core, release_checklist_ui
   Rationale: Phase 1 unblocks all Phase 2 prerequisites.
   Adjust or confirm?"
```

---

### The QA Agent

The QA Agent verifies features against their specifications through interactive scenario execution. It owns exactly one thing in the spec system: the `## User Testing Discoveries` section of each feature file. It never modifies code, tests, or Gherkin requirements.

| Command | Description |
|---|---|
| `/pl-verify <name>` | Run interactive scenario verification for a feature |
| `/pl-discovery <name>` | Record a structured discovery (BUG, DISCOVERY, INTENT_DRIFT, SPEC_DISPUTE) |
| `/pl-complete <name>` | Mark a feature complete -- gates on all tests pass, all scenarios verified, zero open discoveries, no pending delivery phases |
| `/pl-qa-report` | Summary of open discoveries, features in TESTING, completion blockers |

**Workflow examples:**

*Verifying a feature:*
```
/pl-verify critic_tool
→ Agent loads scenarios, walks through each step interactively
→ All pass: "Ready to close. Run /pl-complete critic_tool when confirmed."
```

*Recording unexpected behavior:*
```
/pl-discovery cdd_status_monitor
→ Agent: "Describe what you observed."
→ "The graph view shows stale data after a spec change."
→ Agent: "No duplicate open. Classifying as BUG. Confirm?"
→ Discovery recorded, Builder notified via Critic on next run
```

---

## The Critic

The Critic is the **project coordination engine** -- not a pass/fail badge. It generates role-specific action items that tell each agent what to work on next.

### Dual-Gate Validation

Every feature is evaluated through two independent gates:

*   **Spec Gate (pre-implementation):** Validates structural completeness, prerequisite anchoring, and Gherkin quality. Runs before any code exists.
*   **Implementation Gate (post-implementation):** Validates traceability (automated scenarios matched to test functions), policy adherence (FORBIDDEN pattern scanning), builder decision audit, and optional LLM-based logic drift detection.

A feature that passes the Spec Gate but fails the Implementation Gate has a code problem. A feature that passes the Implementation Gate but fails the Spec Gate has a specification problem.

### Supplementary Audits

On every run, the Critic also executes:

*   **User Testing Audit:** Counts open BUG, DISCOVERY, INTENT_DRIFT, and SPEC_DISPUTE entries across all feature files.
*   **Builder Decision Audit:** Scans `## Implementation Notes` for unacknowledged `[DEVIATION]` and `[DISCOVERY]` tags (HIGH-priority Architect items).
*   **Visual Specification Detection:** Detects `## Visual Specification` sections and generates separate QA action items for visual verification.
*   **Untracked File Audit:** Flags untracked files as MEDIUM-priority Architect triage items.

### Role-Specific Action Items

The Critic outputs a `CRITIC_REPORT.md` at the project root with a role-specific action item section:

| Role | Typical Action Items |
|------|---------------------|
| **Architect** | Fix spec gaps, revise infeasible specs, acknowledge builder decisions, triage untracked files |
| **Builder** | Implement TODO features, fix failing tests, close traceability gaps, resolve open bugs |
| **QA** | Verify TESTING features, re-verify SPEC_UPDATED discoveries, run visual verification passes |

### CDD vs. The Critic

*   **CDD** shows what IS — per-role status (Architect, Builder, QA) on the dashboard.
*   **The Critic** shows what SHOULD BE DONE — imperative action items per role.

CDD does not run the Critic. It reads the `role_status` values from pre-computed `tests/<feature>/critic.json` files.

### CLI Invocation

```bash
tools/cdd/status.sh           # Run Critic automatically + show CDD status (primary agent interface)
tools/critic/run.sh           # Run Critic directly
```

Agents use the CLI exclusively. The CDD web dashboard is for human consumption only.

---

## Phased Delivery

When the Architect introduces a large batch of new or revised specs, the Builder may split work across multiple sessions using a **phased delivery plan**. Each phase produces a testable state; the user orchestrates the cycle: Builder → QA → Builder → QA → ... until the backlog is clear.

### How It Works

The Builder creates a delivery plan at `.purlin/cache/delivery_plan.md` when the user approves phased delivery. The plan contains numbered phases, each with a feature list and one of three statuses: `PENDING`, `IN_PROGRESS`, or `COMPLETE`. The file is committed to git so all agents share the same view across sessions.

```
/pl-delivery-plan
→ Agent assesses scope and dependency ordering
→ "6 TODO features. Dependency analysis suggests 3 phases:
   Phase 1 (foundation): policy_critic, python_environment
   Phase 2 (core tools): critic_tool, cdd_status_monitor
   Phase 3 (release): release_checklist_core, release_checklist_ui
   Rationale: Phase 1 unblocks all Phase 2 prerequisites.
   Adjust or confirm?"
```

The standard multi-phase cycle:

```
Builder (Phase 1)
  → QA verifies Phase 1 features
  → Builder (addresses QA bugs + implements Phase 2)
  → QA verifies Phase 2 features
  → ... until all phases COMPLETE
  → Builder deletes delivery_plan.md
```

### Rules

*   **Phasing is opt-in.** The Builder proposes phases; the user always decides whether to accept, modify, or proceed as a single session.
*   **QA is phase-gated.** QA will not mark a feature `[Complete]` if it appears in any `PENDING` phase of the delivery plan, even if all currently-delivered scenarios pass.
*   **Cross-session resumption.** If a Builder session is interrupted mid-phase, the next Builder session resumes from where it left off -- skipping features already in `TESTING` state.
*   **Spec changes trigger amendments.** If the Architect modifies specs while a plan is active, the Builder detects the mismatch on resume and proposes a plan amendment before continuing.
*   **Dashboard visibility.** While a plan is active, the CDD Dashboard annotates the active section: `ACTIVE (N) [PHASE (current/total)]`.
*   **Flexible exit.** At any approval checkpoint, the user may collapse remaining phases, re-split, or abandon phasing entirely.

---

## Isolated Teams

Purlin supports multiple concurrent agent sessions through named git worktrees -- **isolated teams**. Each isolation is an independent workspace on a dedicated branch where any agent (Architect, Builder, or QA) can work without interfering with other running sessions.

### How It Works

A single command creates one isolated team:

```bash
tools/collab/create_isolation.sh <name>
```

This creates a git worktree at `.worktrees/<name>/` on branch `isolated/<name>`. Each isolation has its own branch, its own `.purlin/` state snapshot, and its own view of `features/`. When work is complete, the agent runs `/pl-local-push` to run the pre-merge handoff checklist and merge the branch back to `main`.

```
Architect (isolated/design)          Builder (isolated/feat1)
  → designs new specs                  → implements existing backlog
  → /pl-local-push                     → /pl-local-push
       ↓ merge to main                      ↓ merge to main
                    → QA verifies combined result
```

### Rules

*   **Merge-before-proceed:** Each isolation must merge to `main` before another session that depends on its changes can start. The Critic only sees commits reachable from HEAD -- a `[Complete]` status on an unmerged branch is invisible to other agents until merged.
*   **No role assignment:** The isolation name is the identifier. `feat1`, `ui`, `hotfix` are all valid -- any agent type may use any name.
*   **Name constraints:** 1--12 characters, matching `[a-zA-Z0-9_-]+`.
*   **Dashboard visibility:** Active isolations appear in the **ISOLATED TEAMS** section of the CDD Dashboard, showing branch name, sync state relative to `main` (AHEAD / BEHIND / SAME / DIVERGED), and a file change summary by category (Specs, Tests, Code). Create and kill isolations directly from the dashboard.
*   **Agent config propagation:** When Isolated Teams Mode is active, saving agent config changes via the dashboard propagates the update to all active worktrees simultaneously.

---

## Setup & Configuration For Your Project

### 1. Install Claude Code

[Claude Code](https://docs.anthropic.com/en/docs/claude-code) must be installed before using Purlin. Purlin agents run exclusively inside Claude Code sessions.

### 2. Add Purlin as a Submodule

Your project must be an initialized git repository. If it isn't already:

```bash
git init
```

Then add Purlin as a submodule:

```bash
git submodule add https://github.com/rlabarca/purlin purlin
git submodule update --init
```

### 3. Run the Bootstrap Script

```bash
./purlin/tools/bootstrap.sh
```

This creates in your project root:
*   `.purlin/` -- override templates and config (MUST be committed to your project)
*   `run_architect.sh` / `run_builder.sh` / `run_qa.sh` -- layered launcher scripts
*   `features/` directory

Your Architect agent will guide you through customizing the overrides for your project on first launch.

### 4. Launch Agents

```bash
./run_architect.sh   # Architect agent
./run_builder.sh     # Builder agent
./run_qa.sh          # QA agent
```

### 5. Run the CDD Dashboard

```bash
./purlin/tools/cdd/start.sh
```

Open **http://localhost:8086** in your browser. The dashboard has two modes:

*   **Status view:** Real-time feature status by role (Architect, Builder, QA), the release checklist, and workspace / isolated team state. The **Agent Config** panel lets you configure model, effort, permissions, and startup behavior for each agent directly from the browser -- changes are written to `.purlin/config.json` and committed automatically.
*   **Spec Map view:** An interactive dependency graph of all feature files, showing prerequisite chains and category groupings. Toggle between Status and Spec Map using the view mode controls in the dashboard header.

### 6. Startup Controls (Optional)

Each agent's session behavior is governed by two per-agent flags in `.purlin/config.json`:

| Flag | Default | Behavior |
|---|---|---|
| `startup_sequence` | `true` | Runs full orientation on launch (Critic report, dependency graph, action items). Set to `false` to skip straight to the command table. |
| `recommend_next_actions` | `true` | After orientation, presents a prioritized work plan and asks for approval. Requires `startup_sequence: true`. Set to `false` to orient silently then await direction. |

Both `false` activates expert mode: the command table is printed and the agent waits for a direct instruction. The **Agent Config** panel in the CDD Dashboard provides UI toggles for these flags without editing `config.json` directly.

### Python Environment (Optional)

The framework's Python tools use only the standard library -- no packages need to be installed for core functionality. However, optional features (e.g., LLM-based logic drift detection in the Critic) require third-party packages.

All tool scripts auto-detect a `.venv/` at the project root. To set up:

```bash
python3 -m venv .venv
.venv/bin/pip install -r purlin/requirements-optional.txt
```

No additional configuration is needed -- all shell scripts that invoke Python use a shared resolver (`tools/resolve_python.sh`) that checks for the venv automatically. The resolution priority is:
1. `$AGENTIC_PYTHON` env var (explicit override)
2. `$PURLIN_PROJECT_ROOT/.venv/`
3. Climbing detection from script directory
4. System `python3`, then `python`

This works on macOS, Linux, and Windows via WSL or Git Bash. Native PowerShell is not supported.

### Updating the Submodule

```bash
cd purlin && git pull origin main && cd ..
git add purlin
./purlin/tools/sync_upstream.sh   # Audit changes, update sync marker
git commit -m "chore: update purlin submodule"
```

The sync script shows a changelog of what changed in `instructions/` and `tools/`, and flags any structural changes that may require override updates.

### Gitignore Guidance

**`.purlin/` MUST be committed** to your project. It contains project-specific overrides, config, and the upstream sync marker. The bootstrap script will warn if it detects `.purlin` in your `.gitignore`.

## Directory Structure

**In your project (created by bootstrap):**
*   `purlin/` -- The Purlin submodule. Contains all framework tooling and base instruction files.
*   `.purlin/` -- Your project's override layer.
    *   `ARCHITECT_OVERRIDES.md` -- Project-specific Architect rules.
    *   `BUILDER_OVERRIDES.md` -- Project-specific Builder rules.
    *   `QA_OVERRIDES.md` -- Project-specific QA verification rules.
    *   `HOW_WE_WORK_OVERRIDES.md` -- Project-specific workflow additions.
    *   `config.json` -- `tools_root`, critic configuration, agent settings, and dashboard port.
*   `features/` -- Your project's feature specifications.
*   `run_architect.sh` / `run_builder.sh` / `run_qa.sh` -- Agent launcher scripts.

**Inside the Purlin submodule (`purlin/`):**
*   `instructions/` -- Base instruction layer (framework rules). Read by launcher scripts at runtime; never copied to your project.
*   `tools/` -- Python-based DevOps tools (CDD Dashboard, Critic, Bootstrap, Upstream Sync, Release Step management).
*   `purlin-config-sample/` -- Override templates used by the bootstrap script.

## Releases

### v0.6.0 — 2026-02-24

**Isolated Teams**
- Named git worktrees for concurrent agent sessions (`tools/collab/create_isolation.sh`, `tools/collab/kill_isolation.sh`)
- Dashboard section with per-isolation state tracking (AHEAD/BEHIND/SAME/DIVERGED), file change summary, and create/kill controls
- `/pl-local-push` and `/pl-local-pull` commands for merge-before-proceed workflow
- Agent config propagation to active worktrees

**Agent Configuration**
- Dashboard panel for per-agent model, effort, permissions, and startup behavior settings
- `/pl-agent-config` skill for worktree-safe config modification from agent sessions
- Per-agent `startup_sequence` and `recommend_next_actions` startup control flags (expert mode: both false)

**Spec Map (renamed from Software Map)**
- Interactive dependency graph with node position persistence and conditional zoom/pan preservation
- Recenter Graph button and inactivity timeout for auto-redraw

**Critic Enhancements**
- Language-agnostic test file discovery with tiered extraction (Python, JS/TS, shell, generic fallback)
- Companion `.impl.md` file detection in section completeness checks
- Builder Decision Audit extended to scan anchor node companion files
- Visual specification detection supports numbered section headers
- Targeted scope filters QA action items to manual scenarios only
- Structured status detection and RESOLVED discovery pruning signal

**Companion File Convention**
- All implementation notes migrated from inline `## Implementation Notes` to standalone `*.impl.md` companion files
- Feature files no longer contain implementation notes; companion files are standalone (no cross-links)
- Companion file edits exempt from lifecycle status resets

**Process & Documentation**
- File access permissions formalized across all roles (README permissions table)
- Bidirectional spec-code audit (`/pl-spec-code-audit`) shared between Architect and Builder
- `/pl-status` uncommitted changes check added to Architect protocol
- Complete QA verification pass across all 31 features

**Getting started:**

This is tested to be started with a new project right now. You can ask the architect to scan your code and build an initial feature map but the behavior will be undefined. It would be an interesting experiment though!

**Known limitations:**

- Built exclusively for Claude Code. Supporting additional models is a goal but model feature disparity makes that non-trivial.
- Local concurrent collaboration is supported via Isolated Teams (named worktrees). Cross-machine and remote worker support is a planned future direction.
- The release checklist is long enough to stress context windows. For now, the checklist can be interrupted and resumed with: `/pl-release-run start with step X, steps 1 through X-1 have passed`. Modularizing the checklist to reduce token cost is a planned improvement.

### v0.5.0 — 2026-02-22

- Initial release of Purlin: Collaborative Design-Driven Agentic Development Framework
- CDD Dashboard with role-based status columns, release checklist UI, and software map
- Critic coordination engine with dual-gate validation, regression scoping, and role-specific action items
- Release checklist system with global and local steps, config-driven ordering
- Phased delivery protocol for multi-session builder workflows
- Submodule bootstrap and upstream sync tooling
- Visual specification convention for UI features
- Layered instruction architecture (base + project override layers)
- Tombstone protocol for structured feature retirement

**Known limitations:**

- Built exclusively for Claude Code. Supporting additional models is a goal but model feature disparity makes that non-trivial.
- Local concurrent collaboration is supported via Isolated Teams (named worktrees). Cross-machine and remote worker support is a planned future direction.
- The release checklist is long enough to stress context windows. For now, the checklist can be interrupted and resumed with: `/pl-release-run start with step X, steps 1 through X-1 have passed`. Modularizing the checklist to reduce token cost is a planned improvement.

