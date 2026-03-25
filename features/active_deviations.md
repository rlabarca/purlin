# Feature: Active Deviations Reference

> Label: "Shared Agent Definitions: Active Deviations Protocol"
> Category: "Shared Agent Definitions"
> Prerequisite: features/purlin_mode_system.md

## 1. Overview

The Active Deviations reference (`instructions/references/active_deviations.md`) defines the protocol for how Engineer mode records implementation decisions that diverge from the spec, and how PM mode reviews them. It defines the companion file table format, the decision hierarchy, the three Engineer-to-PM flows, and builder decision tags.

---

## 2. Requirements

### 2.1 Table Format

- MUST define the Active Deviations table at the top of companion files (`features/<name>.impl.md`).
- Table columns: Spec says, Implementation does, Tag, PM status.
- PM status values: PENDING, ACCEPTED, REJECTED.

### 2.2 Decision Hierarchy

- MUST define: spec is baseline, active deviations are overrides.
- No deviation → follow spec exactly.
- PENDING → follow deviation (provisional).
- ACCEPTED → follow deviation (PM ratified).
- REJECTED → follow spec (PM overruled).

### 2.3 Three Engineer-to-PM Flows

- Flow 1 INFEASIBLE (blocking): halt work, document, propose alternative. Use `/pl-infeasible`.
- Flow 2 Inline Deviation (non-blocking): build continues, add row to table.
- Flow 3 SPEC_PROPOSAL (proactive): suggest spec change. Use `/pl-propose`.

### 2.4 Engineer Decision Tags

- MUST define: `[CLARIFICATION]` (INFO), `[AUTONOMOUS]` (WARN), `[DEVIATION]` (HIGH), `[DISCOVERY]` (HIGH), `[INFEASIBLE]` (CRITICAL).
- MUST define format: `**[TAG]** <description> (Severity: <level>)`
- Cross-feature discoveries go in the target feature's companion file.

### 2.5 PM Review Protocol

- PM reviews unacknowledged entries via `/pl-status` (scan.py surfaces them).
- PM marks `[ACKNOWLEDGED]` and accepts, rejects, or requests clarification.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Table format defined with correct columns

    Given references/active_deviations.md exists
    When the table format section is parsed
    Then the table has columns: Spec says, Implementation does, Tag, PM status

#### Scenario: Decision hierarchy covers all PM status values

    Given references/active_deviations.md exists
    When the hierarchy section is parsed
    Then it covers PENDING, ACCEPTED, and REJECTED
    And it defines what the Engineer should do for each

#### Scenario: All three flows defined

    Given references/active_deviations.md exists
    When the flows section is parsed
    Then INFEASIBLE, inline deviation, and SPEC_PROPOSAL are defined
    And each references the correct skill

#### Scenario: All builder decision tags defined with severity

    Given references/active_deviations.md exists
    When the tags section is parsed
    Then CLARIFICATION, AUTONOMOUS, DEVIATION, DISCOVERY, INFEASIBLE are defined
    And each has a severity level

## Regression Guidance
- Verify companion file gate in /pl-build references this tag format
- Verify scan.py deviation scanner recognizes all tags defined here
