# Feature: Purlin Issue Report Skill

> Label: "Agent Skills: Common: purlin:purlin-issue Purlin Issue Report"
> Category: "Agent Skills: Common"

[TODO]

## 1. Overview

A shared skill that generates a structured, copy-paste-ready bug report for the Purlin framework. The report is designed for one workflow: paste it into a Purlin Engineer session and have that agent debug and fix the issue. Every field exists to help the receiving agent find and fix the problem faster.

Distinct from `purlin:discovery`, which records project-level bugs.

---

## 2. Requirements

### 2.1 Issue Context Collection (Interactive)

The skill collects the debugging essentials through structured prompts:

1. **What happened** — description of the issue (from `$ARGUMENTS` or interactive prompt)
2. **What command/skill was running** — the `purlin:*` command or user action that triggered the issue
3. **What was the error** — if the error is visible in the current conversation context, the agent extracts it automatically and asks the user to confirm before including it. Otherwise, asks the user to paste or describe the error output (traceback, unexpected result, or wrong behavior).
4. **What was expected** — what should have happened instead

### 2.2 Automatic Context Gathering

The report automatically collects (no user input needed):

- **Purlin version**: SHA, version tag, remote URL
- **Deployment mode**: consumer (`.purlin/.upstream_sha` exists) or standalone
- **Environment**: OS, current mode (Engineer/PM/QA/none — read from session state, not legacy role markers), branch, plugin version
- **Config state**: contents of `.purlin/config.local.json` if it exists, otherwise `.purlin/config.json` — the resolved config the agent is actually using
- **Relevant files**: if the failing command is a known skill, include the skill file path (`skills/<name>/SKILL.md`). If a feature was being worked on, include the feature spec path.
- **Recent git history**: `git log --oneline -5`
- **Working tree state**: `git status --short` (max 20 lines)
- **Conversation context**: agent-composed 2-3 sentence summary of what led to the issue — what was being attempted, what mode was active, what sequence of actions preceded the failure

### 2.3 Output Format

The report has two sections designed for different consumers:

**Section 1 — Reproduction Block** (what the receiving agent reads first):
- Command that failed
- Error output
- Expected behavior
- Steps to reproduce (agent-composed from conversation context)
- Relevant files

**Section 2 — Environment Snapshot** (reference context):
- Version/deployment table
- Config state
- Git state

The report is bounded by clear copy dividers. Everything between the dividers is valid Markdown that can be pasted directly into a Purlin agent session as a task prompt.

### 2.4 Consumer vs Standalone Fields

- **Consumer mode** (`.purlin/.upstream_sha` exists): includes consumer project remote, branch, HEAD SHA, and Purlin submodule path
- **Standalone mode**: includes only Purlin repo fields

### 2.5 Command File

The skill definition lives at `skills/purlin-issue/SKILL.md`. The first line declares `**Purlin command: shared (all roles)**`.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Skill prompts for description when no arguments given

    Given no $ARGUMENTS are provided
    When purlin:purlin-issue is invoked
    Then the agent asks the user to describe the Purlin framework issue
    And the agent does not generate the report until a description is provided

#### Scenario: Skill extracts error from conversation context

    Given the user encountered an error in the current conversation
    When purlin:purlin-issue is invoked
    Then the agent extracts the error output from the conversation
    And asks the user to confirm it is correct before including it

#### Scenario: Report includes reproduction block first

    Given a complete issue description
    When the report is generated
    Then the first section after the divider is the Reproduction Block
    And it contains: Command, Error Output, Expected, Steps to Reproduce, Relevant Files

#### Scenario: Deployment mode detection

    Given a consumer project with .purlin/.upstream_sha present
    When purlin:purlin-issue is invoked
    Then the report Deployment field shows "consumer"
    And the report includes consumer project remote, branch, and HEAD fields

#### Scenario: Config state is included

    Given any Purlin deployment
    When purlin:purlin-issue is invoked
    Then the report includes the resolved config contents
    And uses config.local.json if it exists, otherwise config.json

#### Scenario: Mode detection uses session state

    Given the agent is in Engineer mode
    When purlin:purlin-issue is invoked
    Then the report Mode field shows "Engineer"
    And does not attempt legacy role marker detection

#### Scenario: Report is bounded by copy dividers

    Given any Purlin deployment
    When purlin:purlin-issue is invoked
    Then the output contains "-------- PURLIN ISSUE REPORT (COPY THIS) ---------"
    And the output contains "-------- END PURLIN ISSUE REPORT ---------"
    And the report content between dividers is valid Markdown

### QA Scenarios

None.
