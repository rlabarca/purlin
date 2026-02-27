# Feature: Spec-Code Audit Role Clarity

> Label: "Process: Spec-Code Audit Role Clarity"
> Category: "Process"
> Prerequisite: features/policy_critic.md

[TODO]

## 1. Overview

The `/pl-spec-code-audit` command's remediation plan section uses role-ambiguous language ("describe the specific edit — which file, which section, what changes") that does not clarify whose edits target which artifacts. When the Architect enters plan mode for a spec-code audit, the generic phrasing can reinforce the platform's implementation-oriented plan mode prompts, leading the Architect to describe code changes instead of spec changes. This feature adds explicit role-scoping to the remediation plan instructions in the command file.

---

## 2. Requirements

### 2.1 Role-Scoped Remediation Instructions

- The remediation plan instructions in `.claude/commands/pl-spec-code-audit.md` MUST distinguish between Architect FIX edits (targeting feature specs and anchor nodes only) and Builder FIX edits (targeting source code and tests only).
- The existing line "For each FIX item, describe the specific edit (which file, which section, what changes)." MUST be replaced with role-scoped guidance that names the artifact types each role owns.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Architect remediation plan describes only spec edits

    Given the `/pl-spec-code-audit` command file exists
    When the Architect reads the remediation plan instructions
    Then the instructions explicitly state that Architect FIX edits target feature specs and anchor nodes only

#### Scenario: Builder remediation plan describes only code edits

    Given the `/pl-spec-code-audit` command file exists
    When the Builder reads the remediation plan instructions
    Then the instructions explicitly state that Builder FIX edits target source code and tests only

### Manual Scenarios (Human Verification Required)

None.
