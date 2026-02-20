# How We Work: The Agentic Workflow

> **Layered Instructions:** This file is the **base layer** of the workflow philosophy, provided by the agentic-dev-core framework. Project-specific workflow additions are defined in the **override layer** at `.agentic_devops/HOW_WE_WORK_OVERRIDES.md`. At runtime, both layers are concatenated (base first, then overrides).

## 1. Core Philosophy: "Code is Disposable"
The single source of truth for any project using this framework is not the code, but the **Specifications** and **Architectural Policies** stored in the project's `features/` directory.
*   If the application code is lost, it must be reproducible from the specs.
*   We never fix bugs in code first; we fix the specification that allowed the bug.

## 2. Roles and Responsibilities

### The Architect Agent
*   **Focus:** "The What and The Why".
*   **Ownership:** Architectural Policies, Feature Specifications, instruction overrides.
*   **Key Duty:** Designing rigorous, unambiguous specifications and enforcing architectural invariants.

### The Builder Agent
*   **Focus:** "The How".
*   **Ownership:** Implementation code, tests, and the DevOps tools.
*   **Key Duty:** Translating specifications into high-quality, verified code and documenting implementation discoveries.

### The QA Agent
*   **Focus:** "The Verification and The Feedback".
*   **Ownership:** `## User Testing Discoveries` section in feature files (exclusive write access), manual verification execution, discovery lifecycle management.
*   **Key Duty:** Executing manual Gherkin scenarios, recording structured discoveries (BUG, DISCOVERY, INTENT_DRIFT, SPEC_DISPUTE), and tracking their resolution through the lifecycle.
*   **Does NOT:** Write or modify application/tool code (Builder), modify Gherkin scenarios or requirements (Architect), or make status tag commits (Builder).

### The Human Executive
*   **Focus:** "The Intent and The Review".
*   **Duty:** Providing high-level goals, performing final verification (e.g., Hardware-in-the-Loop), and managing the Agentic Evolution.

## 3. The Lifecycle of a Feature
1.  **Design:** Architect creates/refines a feature file in `features/`.
2.  **Implementation:** Builder reads the feature and implementation notes, writes code/tests, and verifies locally.
3.  **Verification:** QA Agent executes manual scenarios and records discoveries. Human Executive performs final verification as needed.
4.  **Completion:** Builder marks the status as `[Complete]`.
5.  **Synchronization:** Architect updates documentation and generates the Software Map.

## 4. Knowledge Colocation
We do not use a global implementation log. Tribal knowledge, technical "gotchas," and lessons learned are stored directly in the `## Implementation Notes` section at the bottom of each feature file.

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
The agentic-dev-core framework uses a two-layer instruction model to separate framework rules from project-specific context:

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
When used as a git submodule (e.g., at `agentic-dev/`):
1. The submodule provides the base layer (`agentic-dev/instructions/`) and all tools (`agentic-dev/tools/`).
2. The consumer project runs `agentic-dev/tools/bootstrap.sh` to initialize `.agentic_devops/` with override templates.
3. Tools resolve their paths via `tools_root` in `.agentic_devops/config.json`.
4. Upstream updates are pulled via `git submodule update` and audited with `agentic-dev/tools/sync_upstream.sh`.

## 7. User Testing Protocol

### 7.1 Discovery Section Convention
Feature files MAY contain a `## User Testing Discoveries` section as the last section before the end of the file. This section is a **live queue** of open verification findings owned exclusively by the QA Agent.

### 7.2 Discovery Types
*   **[BUG]** -- Behavior contradicts an existing scenario.
*   **[DISCOVERY]** -- Behavior exists but no scenario covers it.
*   **[INTENT_DRIFT]** -- Behavior matches the spec literally but misses the actual intent.
*   **[SPEC_DISPUTE]** -- The user disagrees with a scenario's expected behavior. The spec itself is wrong or undesirable.

### 7.3 Discovery Lifecycle
Status progression: `OPEN -> SPEC_UPDATED -> RESOLVED -> PRUNED`

*   **OPEN:** QA records the finding.
*   **SPEC_UPDATED:** Architect updates Gherkin scenarios to address it.
*   **RESOLVED:** Builder re-implements, QA re-verifies and confirms fix.
*   **PRUNED:** QA removes entry from Discoveries, adds one-liner to Implementation Notes. Git history preserves full record.

### 7.4 Queue Hygiene
*   The section only contains OPEN and SPEC_UPDATED entries (active work).
*   RESOLVED entries are pruned by the QA Agent.
*   An empty `## User Testing Discoveries` section (or its absence) means the feature is clean.

### 7.5 Feedback Routing
*   **BUG** -> Builder must fix implementation.
*   **DISCOVERY** -> Architect must add missing scenarios, then Builder re-implements.
*   **INTENT_DRIFT** -> Architect must refine scenario intent, then Builder re-implements.
*   **SPEC_DISPUTE** -> Architect must review the disputed scenario with the user and revise or reaffirm it. The scenario is **suspended** (QA skips it) until the Architect resolves the dispute.

## 8. Critic-Driven Coordination
The Critic is the project coordination engine. It validates quality AND generates role-specific action items. Every agent runs the Critic at session start.

*   **CDD** shows what IS (feature status, test results, QA status).
*   **Critic** shows what SHOULD BE DONE (role-specific action items).
*   Agents consult `CRITIC_REPORT.md` for their role-specific priorities before starting work.
*   CDD does NOT run the Critic. CDD is a lightweight state display; the Critic is an agent-facing coordination tool.
