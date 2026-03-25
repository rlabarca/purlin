# Feature: Topic Discovery

> Label: "Agent Skills: Common: /pl-find Topic Discovery"
> Category: "Agent Skills: Common"
> Prerequisite: features/policy_critic.md

[TODO]

## 1. Overview

A shared skill available to all roles that searches the spec system for a given topic or concern. Reports whether existing feature specs, anchor nodes, or instruction files cover the topic, and recommends whether a new spec, refinement, or anchor node update is needed.

---

## 2. Requirements

### 2.1 Shared Access

- The command is available to all roles.

### 2.2 Search Scope

- Search `features/`, `instructions/`, and `.purlin/` directories for topic keywords using Glob and Grep.

### 2.3 Report Format

- Whether an existing feature spec covers the topic (file, section, scenario).
- Whether an anchor node governs the concern.
- Whether the topic is only in instruction files.
- Recommendation: new spec, refinement, anchor node update, or already covered.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Topic found in existing feature spec

    Given features/auth_flow.md contains scenarios about authentication
    When /pl-find is invoked with topic "authentication"
    Then the output identifies features/auth_flow.md as covering the topic

#### Scenario: Topic found only in instruction files

    Given instructions/PURLIN_BASE.md mentions "commit discipline"
    And no feature spec covers commit discipline
    When /pl-find is invoked with topic "commit discipline"
    Then the output notes coverage is in instruction files only
    And recommends whether a feature spec is needed

#### Scenario: Topic not found anywhere

    Given no files mention "quantum computing"
    When /pl-find is invoked with topic "quantum computing"
    Then the output reports no coverage found
    And recommends creating a new spec if applicable

### QA Scenarios

None.
