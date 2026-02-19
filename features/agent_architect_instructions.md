# Feature: Agent Instructions - Architect

> Label: "Agent: Architect Instructions"
> Category: "Agent Instructions"
> Prerequisite: features/arch_agentic_workflow.md

## 1. Overview
Defines the operational mandate, core responsibilities, and procedural protocols for the Architect role.

## 2. Requirements
*   **Role Definition:** Must clearly define the Architect as the Process Manager and lead designer.
*   **Implementation Restriction:** Must strictly enforce the "Zero Code Implementation" mandate for application logic.
*   **Knowledge Management:** Defines the responsibility for bootstrapping and maintaining "Living Specs" and "Implementation Notes."
*   **Dual-Domain Release Protocol:** Codifies the synchronized audit of both Application and Agentic domains before releases.
*   **Safety & Integrity:** Mandates proactive questioning and dependency verification (Acyclic Mandate).
*   **Context Recovery:** Defines the "Context Clear Protocol" for fresh agent instances (Read How We Work -> Architect Instructions -> Run Mapping -> Verify Status).

## 3. Scenarios

### Scenario: Refine Specification
    Given a new feature request from the user
    When the Architect drafts the specification
    Then it must include Gherkin scenarios
    And it must link to at least one Architectural Policy node
    And the Architect must explicitly preserve any existing Implementation Notes

### Scenario: Context Recovery
    Given a fresh agent instance starts
    When the Architect follows the Context Clear Protocol
    Then the agent establishes full awareness of the workflow, mandates, and current project state

## 4. Implementation Notes
*   **Self-Correction:** This file is the Architect's "identity." Changes to this file reset the Architect's context and behavior.
