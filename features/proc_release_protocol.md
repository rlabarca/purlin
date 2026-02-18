# Feature: Dual-Domain Release Protocol

> Label: "Proc: Release Protocol"
> Category: "Process"
> Prerequisite: features/arch_agentic_workflow.md

## 1. Overview
The Release Protocol is a synchronized system audit that ensures both the Application and the Meta-System (Agentic Workflow) are verified, documented, and stable before any release.

## 2. Requirements

### 2.1 Verification Gates
*   **Application Gate:** MUST verify a PASS status from the primary project's native tests.
*   **Agentic Gate:** MUST verify a PASS status from the aggregated tests in the framework's `tools/` directory.
*   **Zero-Queue Mandate:** ALL features in both the Application and Agentic domains MUST be in the **[Complete]** state. No features may be left in [TODO] or [Ready for Verification] status at the time of release.
*   **Blocker:** The Architect is forbidden from initiating a release if either domain reports a failure or if any feature status is not [Complete].

### 2.2 Synchronization Mandates
*   **Dependency Map:** MUST regenerate dependency maps for both Application and Agentic features. The Architect must verify the absence of orphans or circular dependencies.
*   **Evolution Parity:** The project's root `README.md` must be updated to reflect the parallel milestones of the Application and Agentic Workflow.
*   **Instruction Audit:** The Architect must verify that the operational instruction files match the latest behavioral specifications in the Agentic domain.

### 2.3 Cleanup
*   **Orphan Staging:** Execute available cleanup tools to identify and move deprecated specs.

## 3. Scenarios

### Scenario: Synchronized Release
    Given Application features are [Complete]
    And Agentic features are [Complete]
    And all tests are passing in both domains
    When a release is initiated
    Then the Architect regenerates both dependency maps
    And the Architect syncs the Evolution Table in README.md

## 4. Implementation Notes
*   **Deterministic Integrity:** This protocol prevents "Process Drift" where the workflow instructions become disconnected from the actual tools in use.
