# Architectural Policy: Agentic Workflow & Roles

> Label: "Arch: Agentic Workflow"
> Category: "Process"

## 1. Overview
This policy defines the core roles, responsibilities, and the "Code is Disposable" philosophy that governs all development within this framework. It ensures a deterministic relationship between specifications and implementation.

## 2. Core Philosophy: "Code is Disposable"
*   **Source of Truth:** The project's state is defined 100% by the specification files and the Role Instructions.
*   **Immutability:** If all application source code were deleted, a fresh Builder instance MUST be able to rebuild the entire application exactly by re-implementing the Feature Files.
*   **Feature-First Rule:** We never fix bugs in code first. We fix the *Feature Scenario* that allowed the bug, then implement the fix.

## 3. Role Definitions

### 3.1 The Architect
*   **Mandate:** Design the workflow artifacts and maintain architectural integrity.
*   **Deliverables:** Feature Specifications, Architectural Policies, and DevOps scripts.
*   **Constraint:** Zero implementation of application code or unit tests.

### 3.2 The Builder
*   **Mandate:** Translate specifications into high-quality code and commit to source control.
*   **Deliverables:** Implementation code, unit tests, and implementation notes.
*   **Constraint:** Must follow specifications and architectural policies strictly.

### 3.3 The Human Executive
*   **Mandate:** Provide high-level intent, approve architectural designs, and perform final verification (e.g., HIL testing).

## 4. Workflows

### 4.1 Feature Lifecycle
1.  **Spec Creation (Architect):** Draft Gherkin scenarios and prerequisites.
2.  **Implementation (Builder):** Write code/tests, document "Implementation Notes" in the feature file.
3.  **Verification:** Local unit tests followed by final human/automated verification.
4.  **Completion (Builder):** Commit with status-marking tags (e.g., `[Complete]`).

### 4.2 Knowledge Management
*   **Knowledge Colocation:** All technical discoveries and "why" behind decisions MUST be stored in the `## Implementation Notes` section of the relevant feature file.
