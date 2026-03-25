# Feature: /pl-release Release Checklist

> Label: "Agent Skills: Engineer: /pl-release Release Checklist"
> Category: "Agent Skills: Engineer"
> Prerequisite: features/purlin_agent_launcher.md

## 1. Overview

The `/pl-release` skill consolidates release operations (check, run, step) into a single command with subcommands. It replaces the old `/pl-release-check`, `/pl-release-run`, and `/pl-release-step` skills.

---

## 2. Requirements

### 2.1 Subcommands

- `check` -- Verify release readiness against the release checklist. Zero-queue mandate: all features must have Engineer DONE and QA CLEAN/N/A.
- `run` -- Execute a single named release step from the config.
- `step` -- Manage release steps (add, remove, reorder, enable, disable).

### 2.2 Consolidation

- Old skill files (`pl-release-check.md`, `pl-release-run.md`, `pl-release-step.md`) MUST be deleted.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Check verifies zero-queue mandate

    Given all features are COMPLETE
    When /pl-release check is invoked
    Then it reports release readiness as PASS

#### Scenario: Check fails with TODO features

    Given 2 features are in TODO state
    When /pl-release check is invoked
    Then it reports the blocking features

### Manual Scenarios (Human Verification Required)

None.
