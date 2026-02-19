# How We Work: The Agentic Workflow

## 1. Core Philosophy: "Code is Disposable"
The single source of truth for any project using this framework is not the code, but the **Specifications** and **Architectural Policies** stored in the project's `features/` directory.
*   If the application code is lost, it must be reproducible from the specs.
*   We never fix bugs in code first; we fix the specification that allowed the bug.

## 2. Roles and Responsibilities

### The Architect Agent
*   **Focus:** "The What and The Why".
*   **Ownership:** `ARCHITECT_INSTRUCTIONS.md`, Architectural Policies, Feature Specifications.
*   **Key Duty:** Designing rigorous, unambiguous specifications and enforcing architectural invariants.

### The Builder Agent
*   **Focus:** "The How".
*   **Ownership:** Implementation code, tests, and the DevOps tools.
*   **Key Duty:** Translating specifications into high-quality, verified code and documenting implementation discoveries.

### The Human Executive
*   **Focus:** "The Intent and The Review".
*   **Duty:** Providing high-level goals, performing final verification (e.g., Hardware-in-the-Loop), and managing the Agentic Evolution.

## 3. The Lifecycle of a Feature
1.  **Design:** Architect creates/refines a feature file in `features/`.
2.  **Implementation:** Builder reads the feature and implementation notes, writes code/tests, and verifies locally.
3.  **Verification:** Human Executive or automated systems perform final verification.
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
