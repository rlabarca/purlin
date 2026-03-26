# Feature: Git Timestamp Resilience

> Label: "Git Timestamp Resilience"
> Category: "Coordination & Lifecycle"

[TODO]

## 1. Overview

Git commit timestamps have one-second granularity. When a status commit and a spec-modifying commit share the same Unix second, strict greater-than comparisons in the Critic and CDD status engine produce incorrect results: valid status commits are rejected, scope assignments become non-deterministic, and false action items are generated. This feature specifies boundary-inclusive timestamp comparisons and deterministic tiebreakers to eliminate these correctness bugs.

---

## 2. Requirements

### 2.1 Boundary-Inclusive Lifecycle Comparisons

- `_has_testing_phase_commit()` in `critic.py` MUST use `>=` (greater-than-or-equal) when comparing a TESTING-phase commit timestamp against the lifecycle reset point. A TESTING-phase commit at the exact same second as the reset point is valid.
- `_has_verified_complete_commit()` in `critic.py` MUST use `>=` when comparing a Verified Complete commit timestamp against the reset point.
- The policy language in `policy_critic.md` Section 2.13 step 3 MUST read "at or after" instead of "after" to align with the implementation fix.

### 2.2 Deterministic Scope Assignment

- `build_status_commit_cache()` in `serve.py` MUST use `>=` when comparing timestamps for scope assignment.
- When two status commits for the same feature share an identical Unix timestamp, the commit with the lexicographically greater commit hash MUST win. This provides a stable, deterministic tiebreaker.
- The result of `build_status_commit_cache()` MUST be identical across repeated invocations given the same git state.

### 2.3 Conservative Fast-Path for Content Comparison

- `get_feature_status()` in `serve.py` MUST use strict less-than (`<`) for the fast-path comparison of file modification time vs. complete commit timestamp.
- When `file_mod_ts == complete_ts` (same second), the fast path MUST NOT be taken. Instead, the `spec_content_unchanged()` fallback MUST be invoked.
- When `file_mod_ts < complete_ts` (strictly earlier), the fast path returns the cached status without content verification.

### 2.4 Integration Test Fixture Tags

| Tag | State Description |
|-----|-------------------|
| `main/git_timestamp_resilience/same-second-commits` | Feature with spec-modifying commit and status commits at identical Unix timestamps |
| `main/git_timestamp_resilience/normal-ordering` | Feature with status commits strictly after spec-modifying commits (baseline) |

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Same-second TESTING commit is recognized

    Given a feature spec-modifying commit at Unix timestamp 1700000000
    And a TESTING-phase commit "[Ready for Verification features/foo.md]" at Unix timestamp 1700000000
    When the Critic evaluates _has_testing_phase_commit() for the feature
    Then the function returns True

#### Scenario: Same-second Verified Complete commit is recognized

    Given a feature spec-modifying commit at Unix timestamp 1700000000
    And a Complete commit "[Complete features/foo.md] [Verified]" at Unix timestamp 1700000000
    When the Critic evaluates _has_verified_complete_commit() for the feature
    Then the function returns True

#### Scenario: Earlier TESTING commit is rejected

    Given a feature spec-modifying commit at Unix timestamp 1700000000
    And a TESTING-phase commit "[Ready for Verification features/foo.md]" at Unix timestamp 1699999999
    When the Critic evaluates _has_testing_phase_commit() for the feature
    Then the function returns False

#### Scenario: Later TESTING commit is accepted

    Given a feature spec-modifying commit at Unix timestamp 1700000000
    And a TESTING-phase commit "[Ready for Verification features/foo.md]" at Unix timestamp 1700000001
    When the Critic evaluates _has_testing_phase_commit() for the feature
    Then the function returns True

#### Scenario: Same-second scope assignment is deterministic

    Given a Complete commit "[Complete features/foo.md] [Scope: full]" at Unix timestamp 1700000000
    And a TESTING commit "[Ready for Verification features/foo.md] [Scope: targeted:X]" at Unix timestamp 1700000000
    When build_status_commit_cache() is invoked 10 times
    Then the scope value for foo.md is identical across all 10 invocations

#### Scenario: Same-second mtime triggers content verification

    Given a Complete status commit for a feature at Unix timestamp 1700000000
    And the feature file's modification time is set to Unix timestamp 1700000000
    When get_feature_status() is called for the feature
    Then spec_content_unchanged() is invoked (not the fast path)

#### Scenario: Strictly-earlier mtime uses fast path

    Given a Complete status commit for a feature at Unix timestamp 1700000000
    And the feature file's modification time is set to Unix timestamp 1699999999
    When get_feature_status() is called for the feature
    Then the fast path returns the cached status
    And spec_content_unchanged() is not invoked

### Manual Scenarios (Human Verification Required)

None.
