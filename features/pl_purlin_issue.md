# Feature: Purlin Issue Report Skill

> Label: "Agent Skills: Common: /pl-purlin-issue Purlin Issue Report"
> Category: "Agent Skills: Common"
> Prerequisite: features/policy_critic.md

[TODO]

## 1. Overview

A shared skill available to all roles that generates a structured, copy-paste-ready issue report for the Purlin framework itself. Collects version info, environment context, git state, and active Critic issues into a formatted report that can be pasted into a Purlin PM session for triage. Distinct from `/pl-discovery`, which records project-level bugs.

---

## 2. Requirements

### 2.1 Deployment Detection

The skill detects whether Purlin is running as a consumer submodule or standalone:

- Consumer mode: `.purlin/.upstream_sha` exists at project root. Report includes consumer project remote, branch, and HEAD SHA.
- Standalone mode: no `.upstream_sha`. Report includes only Purlin repo fields.

### 2.2 Data Collection

The report collects:

- Purlin SHA (full), version tag, and remote URL
- Deployment mode (consumer/standalone)
- Date, OS, agent role, and `tools_root`
- Recent git history (`git log --oneline -5`)
- Working tree state (`git status --short`, max 20 lines)
- CRITICAL/HIGH items from `CRITIC_REPORT.md` (if present)
- Agent-composed context summary from conversation memory

### 2.3 Output Format

The report is presented between clear dividers (`-------- PURLIN ISSUE REPORT (COPY THIS) ---------` / `-------- END PURLIN ISSUE REPORT ---------`) in a structured Markdown table format. The user copies the text between dividers and sends it to the Purlin developer or issue tracker.

### 2.4 Command File

The skill definition lives at `.claude/commands/pl-purlin-issue.md` and is distributed to consumer projects via `init.sh` command file copy. The first line declares `**Purlin command: shared (all roles)**`.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Skill is available to all roles

    Given any agent role (PM, Engineer, QA, or PM)
    When the user invokes /pl-purlin-issue
    Then the skill executes without a role authorization error

#### Scenario: Report includes deployment mode detection

    Given a consumer project with .purlin/.upstream_sha present
    When /pl-purlin-issue is invoked
    Then the report Deployment field shows "consumer"
    And the report includes Consumer Project and Consumer HEAD fields

#### Scenario: Report includes Purlin version info

    Given any Purlin deployment
    When /pl-purlin-issue is invoked
    Then the report includes Purlin SHA, Purlin Version, and Purlin Remote fields

#### Scenario: Report is bounded by copy dividers

    Given any Purlin deployment
    When /pl-purlin-issue is invoked
    Then the output contains "-------- PURLIN ISSUE REPORT (COPY THIS) ---------"
    And the output contains "-------- END PURLIN ISSUE REPORT ---------"
    And the report content between dividers is valid Markdown

#### Scenario: Skill prompts for description when no arguments given

    Given no $ARGUMENTS are provided
    When /pl-purlin-issue is invoked
    Then the agent asks the user to describe the Purlin framework issue
    And the agent does not generate the report until a description is provided

### QA Scenarios

None.
