# Feature: Agent Instructions - Builder

> Label: "Agent: Builder Instructions"
> Category: "Agent Instructions"
> Prerequisite: features/arch_agentic_workflow.md

## 1. Overview
Defines the implementation protocols and domain-aware requirements for the Builder role.

## 2. Requirements

### 2.1 Domain-Aware Implementation
*   **Application Context (`features/`):** 
    *   Targets: Primary system source code.
    *   Tests: MUST be placed in the project's standard test directory.
*   **Agentic Context (`./features/`):**
    *   Targets: `tools/`.
    *   Tests: MUST be colocated within the tool's directory.
    *   Constraint: NEVER place Agentic/Process tests in the primary application's test folder.

### 2.2 Pre-Flight Checks
*   **Consult the Architecture:** Identify if the task is "Application" or "Agentic" and read the corresponding `arch_*.md`.
*   **Knowledge Base:** Read `## Implementation Notes` in the target file and its prerequisites.

### 2.3 Commit & Status Protocol
*   **Tag Format:** Must include the full path: `[Complete <path_to_feature>]`.
*   **Tag Mapping:** 
    *   `[TODO]`: Active work.
    *   `[Ready for Verification]`: Ready for final verification.
    *   `[Complete]`: Logic and verification passed.

### 2.5 Domain-Specific Test Execution
*   **Command Isolation:** The Builder MUST NOT use global application test scripts when working in the Agentic domain.
*   **Local Test Runners:** The Builder must look for and execute test scripts located within the specific tool's directory.
*   **Standard Reporting (MANDATORY):** Every Agentic test execution MUST generate or update a `test_status.json` file in the tool's directory.
    *   **Format:** `{"status": "PASS" | "FAIL", "timestamp": "...", "message": "..."}`
*   **No Pollution:** Running Agentic tests must never trigger a re-compilation or execution of the primary application tests.

### 2.6 Agentic Team Orchestration
*   **Delegation Mandate:** The Builder is encouraged to act as a "Lead Developer" and delegate complex sub-tasks to specialized sub-agents.
*   **Specialized Personas:** The Builder may spawn internal personas (e.g., "The Critic") to improve implementation quality.

## 3. Scenarios

### Scenario: Implementing a Workflow Tool
    Given a feature in `./features/`
    When the Builder implements the script
    Then all code must stay within `tools/`
    And any tests must be internal to the tools directory
    And a test_status.json must be generated upon verification

### Scenario: Complex Feature Delegation
    Given a high-complexity feature specification
    When the Builder plans the implementation
    Then the Builder identifies sub-tasks suitable for delegation
    And the Builder manages the output of specialized sub-agents

## 4. Implementation Notes
*   **Context Isolation:** The Builder must maintain a strict mental firewall between the application domain and the workflow automation domain.
