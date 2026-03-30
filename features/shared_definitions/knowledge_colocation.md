# Feature: Knowledge Colocation Reference

> Label: "Shared Agent Definitions: Knowledge Colocation"
> Category: "Shared Agent Definitions"
> Prerequisite: purlin_sync_system.md

## 1. Overview

The knowledge colocation reference (`references/knowledge_colocation.md`) defines where implementation knowledge, architectural constraints, and verification findings are stored. It covers anchor nodes (arch/design/policy), companion files, discovery sidecars, the cross-cutting standards pattern, and discovery types with lifecycle.

---

## 2. Requirements

### 2.1 Anchor Node Taxonomy

- MUST define three prefixes: `arch_*.md` (Engineer, technical), `design_*.md` (PM, visual), `policy_*.md` (PM, governance).
- MUST state: editing an anchor resets all dependent features to TODO.
- MUST state: every feature anchors to relevant nodes via `> Prerequisite:` links.

### 2.2 Cross-Cutting Standards Pattern

- MUST define the three-tier structure: Anchor Node → Foundation Feature → Consumer Features.
- MUST explain prerequisite link requirements for each tier.

### 2.3 Companion Files

- MUST define naming: `features/<name>.impl.md`.
- MUST state: standalone (feature files do NOT reference them), not a feature file, not in dependency graph.
- MUST state: edits do NOT reset lifecycle status (status reset exemption).
- MUST state: Engineer-owned (see file_classification.md).
- For Active Deviations table format, MUST reference `references/active_deviations.md`.

### 2.4 Discovery Sidecars

- MUST define naming: `features/<name>.discoveries.md`.
- MUST state: QA owns lifecycle, any mode can record new OPEN entries.
- MUST state: same exclusion rules as companion files (not a feature file, status reset exempt).
- MUST state: empty or absent file = no open discoveries.

### 2.5 Discovery Types and Lifecycle

- MUST define: `[BUG]`, `[DISCOVERY]`, `[INTENT_DRIFT]`, `[SPEC_DISPUTE]` with meanings.
- MUST define lifecycle: `OPEN → SPEC_UPDATED → RESOLVED → PRUNED`.
- MUST reference `purlin:discovery` for the full recording protocol.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Three anchor prefixes defined with ownership

    Given references/knowledge_colocation.md exists
    When the anchor taxonomy section is parsed
    Then arch_*.md is Engineer-owned
    And design_*.md is PM-owned
    And policy_*.md is PM-owned

#### Scenario: Companion file conventions complete

    Given references/knowledge_colocation.md exists
    When the companion file section is parsed
    Then it states files are standalone
    And it states edits do not reset lifecycle
    And it references active_deviations.md for table format

#### Scenario: Discovery sidecar conventions complete

    Given references/knowledge_colocation.md exists
    When the sidecar section is parsed
    Then it states QA owns lifecycle
    And it states any mode can record OPEN entries
    And it defines all 4 discovery types

#### Scenario: Cross-cutting standards pattern has 3 tiers

    Given references/knowledge_colocation.md exists
    When the standards section is parsed
    Then it defines Anchor Node, Foundation Feature, and Consumer Features
    And each tier's prerequisite link requirements are stated

## Regression Guidance
- Verify anchor prefix ownership matches file_classification.md
- Verify discovery types listed here match what scan.py scans for
- Verify companion file status reset exemption is consistent with commit_conventions.md exemption tags
