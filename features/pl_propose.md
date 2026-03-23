# Feature: Spec Change Proposal

> Label: "/pl-propose Spec Change Proposal"
> Category: "Agent Skills"
> Prerequisite: features/policy_critic.md
> Prerequisite: features/impl_notes_companion.md

[TODO]

## 1. Overview

The Builder's structured spec change proposal skill for surfacing gaps, inconsistencies, or improvements discovered during implementation. Records proposals as `[SPEC_PROPOSAL]` entries in the feature's companion file so the Architect discovers them through the Critic report. Supports anchor node proposals via `[SPEC_PROPOSAL: NEW_ANCHOR]` tag. Enforces the "chat is not a durable channel" principle.

---

## 2. Requirements

### 2.1 Role Gating

- The command MUST only execute when invoked by the Builder role.
- Non-Builder agents MUST receive a redirect message.

### 2.2 Proposal Workflow

- Search the spec system for the relevant feature or anchor node.
- Describe the gap, inconsistency, or improvement encountered during implementation.
- Draft a concrete proposal: what should change in the spec.
- Record as `[AUTONOMOUS]` or `[DISCOVERY]` entry with `[SPEC_PROPOSAL]` tag in the companion file.
- Commit so the Architect sees it in the Critic report.

### 2.3 Anchor Node Proposals

- For new anchor node proposals, use tag `[SPEC_PROPOSAL: NEW_ANCHOR]` with proposed type, name, and invariants.

### 2.4 Constraints

- Do NOT modify the feature spec directly. The Architect owns spec content.
- Do NOT pass findings as chat messages. The only valid output is a committed companion file entry.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Role gate rejects non-Builder invocation

    Given an Architect agent session
    When the agent invokes /pl-propose
    Then the command responds with a redirect message

#### Scenario: Proposal recorded in companion file

    Given the Builder discovers a spec gap in feature_a
    When /pl-propose is invoked with topic about feature_a
    Then features/feature_a.impl.md contains a [SPEC_PROPOSAL] entry
    And the entry includes rationale and proposed change

#### Scenario: Anchor node proposal uses correct tag

    Given the Builder discovers a cross-cutting constraint
    When /pl-propose records a new anchor proposal
    Then the entry uses [SPEC_PROPOSAL: NEW_ANCHOR] tag
    And includes proposed anchor type, name, and invariants

#### Scenario: Proposal is committed to git

    Given a proposal entry is written to the companion file
    When the proposal workflow completes
    Then the companion file change is committed
    And the Critic report will surface it at the Architect's next session

### QA Scenarios

None.
