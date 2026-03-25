# Feature: Delivery Plan

> Label: "Agent Skills: Engineer: /pl-delivery-plan Delivery Plan"
> Category: "Agent Skills: Engineer"
> Prerequisite: features/policy_critic.md

[Complete]

## 1. Overview

Engineer mode's phased delivery skill that assesses implementation scope and proposes splitting work into numbered phases for large or complex feature sets. Provides scope assessment heuristics, per-phase sizing caps, dependency-aware phase ordering with execution group detection, and a canonical delivery plan format. Supports both plan creation and cross-session plan review/adjustment.

---

## 2. Requirements

### 2.1 Role Gating

- The command MUST only execute when invoked by Engineer mode role.
- Non-Engineer agents MUST receive a redirect message.

### 2.2 Existing Plan Review

- If `.purlin/delivery_plan.md` exists: display current phase, completed phases, remaining phases, and per-feature status. Offer to adjust the plan.

### 2.3 New Plan Creation

- Run `status.sh` to get current feature status.
- Read `dependency_graph.json` and build a prerequisite map.
- Resolve the context tier (see 2.4) and assess scope using tier-aware heuristics.

### 2.4 Phase Sizing (Context-Tier-Aware)

Phase sizing caps are derived from Engineer mode's context tier:

**Tier Resolution Chain:**
1. Read Engineer mode's configured model from the agent config (`agents.builder.model`).
2. Look up that model ID in the `models` array to get `context_window_tokens`.
3. If `context_window_tokens > 200000`, use **Extended** tier. Otherwise, use **Standard** tier.
4. If the agent config contains a `phase_sizing` override block, those values take precedence over tier defaults for any key present.

**Tier Defaults:**

| Parameter | Standard (<=200K) | Extended (>200K) |
|---|---|---|
| Max features per phase | 2 | 5 |
| Max HIGH-complexity per phase (combined) | 1 | 2 |
| HIGH solo-phase scenario threshold | 5 | 8 |
| Phasing recommendation: any mix | 3+ features | 7+ features |
| Phasing recommendation: HIGH | 2+ features | 4+ features |
| Intra-feature phasing | 5+ scenarios | 8+ scenarios |

**Per-Project Override:** An optional `phase_sizing` block in the agent config overrides individual tier defaults:
```json
"builder": {
    "model": "claude-opus-4-6[1m]",
    "phase_sizing": {
        "max_features_per_phase": 3,
        "high_solo_threshold": 6
    }
}
```
Only keys present in `phase_sizing` override the tier default; absent keys fall through to the tier table.

### 2.5 Phase Ordering

- Phases ordered by: dependency order (foundations first), logical cohesion, testability gates, balanced effort, interaction density, and parallelization opportunity.
- Validation gate: verify no dependency cycles between phases before committing.

### 2.6 Execution Groups

- Identify which phases can execute in parallel (no cross-phase dependencies).
- Report parallel build opportunities within phases (independent features).

### 2.7 Canonical Format

- Plan file uses standardized Markdown format with Created date, Total Phases, Summary, and per-phase entries with Features, Completion Commit, Deferred, and QA Bugs Addressed fields.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Role gate rejects non-Engineer invocation

    Given a PM agent session
    When the agent invokes /pl-delivery-plan
    Then the command responds with a redirect message

#### Scenario: Existing plan displays current state

    Given .purlin/delivery_plan.md exists with Phase 1 COMPLETE and Phase 2 IN_PROGRESS
    When /pl-delivery-plan is invoked
    Then Phase 1 status and completion commit are shown
    And Phase 2 features with their implementation status are listed

#### Scenario: Scope assessment recommends phasing for complex work (standard tier)

    Given Engineer mode's model resolves to context_window_tokens 200000
    And 3 features in TODO state
    When /pl-delivery-plan assesses scope
    Then it recommends phased delivery

#### Scenario: Dependency validation catches cycle

    Given a proposed plan where Phase 2 feature depends on Phase 3 feature
    When the validation gate runs
    Then the cycle is detected
    And the plan is corrected before committing

#### Scenario: Phase sizing cap enforced

    Given Engineer mode's model resolves to a context tier with max_features_per_phase of N
    And N+1 features assigned to a single phase
    When /pl-delivery-plan validates the plan
    Then the phase is split to respect the tier-derived max features per phase

#### Scenario: Extended context tier increases phase capacity

    Given Engineer mode's model is "claude-opus-4-6[1m]" with context_window_tokens 1000000
    And 5 features in TODO state with no HIGH-complexity features
    When /pl-delivery-plan creates a plan
    Then the plan uses the Extended tier defaults
    And all 5 features fit in a single phase

#### Scenario: Phase sizing override takes precedence

    Given Engineer mode's model resolves to the Extended tier
    And the agent config contains phase_sizing with max_features_per_phase of 3
    When /pl-delivery-plan creates a plan with 4 features
    Then the plan splits into phases of at most 3 features each
    And the override value takes precedence over the Extended tier default of 5

### QA Scenarios

None.
