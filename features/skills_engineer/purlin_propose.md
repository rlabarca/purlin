# Feature: Spec Change Proposal

> Label: "Agent Skills: Engineer: purlin:propose Spec Change Proposal"
> Category: "Agent Skills: Engineer"
> Prerequisite: impl_notes_companion.md

[TODO]

## 1. Overview

Engineer mode's structured spec change proposal skill for surfacing gaps, inconsistencies, or improvements discovered during implementation. Records proposals as `[SPEC_PROPOSAL]` entries in the feature's companion file so PM mode discovers them through `purlin:status` output. Supports anchor node proposals via `[SPEC_PROPOSAL: NEW_ANCHOR]` tag. Enforces the "chat is not a durable channel" principle.

---

## 2. Requirements

### 2.1 Role Gating

- The command MUST only execute when invoked by Engineer mode role.
- Non-Engineer agents MUST receive a redirect message.

### 2.2 Proposal Workflow

- Search the spec system for the relevant feature or anchor node.
- Describe the gap, inconsistency, or improvement encountered during implementation.
- Draft a concrete proposal: what should change in the spec.
- Record as `[AUTONOMOUS]` or `[DISCOVERY]` entry with `[SPEC_PROPOSAL]` tag in the companion file.
- Commit so PM mode sees it in `purlin:status` output.

### 2.3 Anchor Node Proposals

- For new anchor node proposals, use tag `[SPEC_PROPOSAL: NEW_ANCHOR]` with proposed type, name, and invariants.

### 2.4 Constraints

- Do NOT modify the feature spec directly. PM mode owns spec content.
- Do NOT pass findings as chat messages. The only valid output is a committed companion file entry.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Role gate rejects non-Engineer invocation

    Given a PM agent session
    When the agent invokes purlin:propose
    Then the command responds with a redirect message

#### Scenario: Proposal recorded in companion file

    Given Engineer mode discovers a spec gap in feature_a
    When purlin:propose is invoked with topic about feature_a
    Then features/feature_a.impl.md contains a [SPEC_PROPOSAL] entry
    And the entry includes rationale and proposed change

#### Scenario: Anchor node proposal uses correct tag

    Given Engineer mode discovers a cross-cutting constraint
    When purlin:propose records a new anchor proposal
    Then the entry uses [SPEC_PROPOSAL: NEW_ANCHOR] tag
    And includes proposed anchor type, name, and invariants

#### Scenario: Proposal is committed to git

    Given a proposal entry is written to the companion file
    When the proposal workflow completes
    Then the companion file change is committed
    And purlin:status will surface it at PM mode's next session

### QA Scenarios

None.
