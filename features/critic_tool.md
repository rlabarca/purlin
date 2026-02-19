# Feature: Critic Quality Gate Tool

> Label: "Tool: Critic"
> Category: "Quality Assurance"
> Prerequisite: features/arch_critic_policy.md

## 1. Overview
The Critic tool is the automated enforcement engine for the Critic Quality Gate policy. It performs dual-gate validation (Spec Gate + Implementation Gate) on feature files, produces per-feature audit reports, and generates an aggregate `CRITIC_REPORT.md`.

## 2. Requirements

### 2.1 Spec Gate (Pre-Implementation Validation)
The Spec Gate validates that a feature specification is structurally complete and properly formed. It runs without requiring any implementation code.

| Check | PASS | WARN | FAIL |
|-------|------|------|------|
| Section completeness | All required sections present (Overview, Requirements, Scenarios) | Implementation Notes empty | Missing Overview, Requirements, or Scenarios |
| Scenario classification | Both Automated + Manual subsections present | Only one subsection | No scenarios at all |
| Policy anchoring | Has `> Prerequisite:` linking to `arch_*.md` | Has prerequisite but not to a policy file | No prerequisite (unless IS a policy file) |
| Prerequisite integrity | All referenced prerequisite files exist on disk | N/A | Referenced file missing |
| Gherkin quality | All scenarios have Given/When/Then | Some scenarios missing steps | N/A (degrades to WARN) |

### 2.2 Implementation Gate (Post-Implementation Validation)
The Implementation Gate validates that the implementation aligns with the specification. It requires implementation code and test results to exist.

| Check | PASS | WARN | FAIL |
|-------|------|------|------|
| Traceability | All automated scenarios have matching tests | >80% scenario coverage | <80% scenario coverage |
| Policy adherence | No FORBIDDEN pattern violations | N/A | Any FORBIDDEN violation detected |
| Structural completeness | `tests/<feature>/tests.json` exists with `"status": "PASS"` | Exists with `"status": "FAIL"` | Missing `tests.json` |
| Builder decisions | All entries are INFO/CLARIFICATION | Has AUTONOMOUS entries | Has DEVIATION or unresolved DISCOVERY |
| Logic drift (LLM) | All pairs ALIGNED | Some PARTIAL | Any DIVERGENT |

### 2.3 Traceability Engine
*   **Keyword Extraction:** Extract keywords from automated scenario titles by stripping articles (a, an, the), prepositions (in, on, at, to, for, of, by, with, from, via), and conjunctions (and, or, but).
*   **Matching Algorithm:** For each automated scenario, search test function names and test function bodies for matching keywords. A match requires 2 or more keywords present in the test.
*   **Manual Scenario Handling:** Manual scenarios are EXEMPT from traceability. If a manual scenario has matching automated tests, flag it as informational (not a failure).
*   **Traceability Overrides:** Feature files MAY include explicit `traceability_overrides` mappings in their Implementation Notes section to handle cases where keyword matching is insufficient. Format: `- traceability_override: "Scenario Title" -> test_function_name`.
*   **Test Discovery:** Tests are located at `tests/<feature_name>/` and within the tool directory specified by `tools_root` in config.

### 2.4 Logic Drift Engine (LLM-Based)
*   **Input:** Gherkin scenario text + mapped test function body (from traceability).
*   **Output:** Per scenario-test pair: `ALIGNED` | `PARTIAL` | `DIVERGENT`.
*   **Configuration:** Controlled by `critic_llm_model` (default `claude-sonnet-4-20250514`) and `critic_llm_enabled` (default `false`) in `.agentic_devops/config.json`.
*   **Caching:** Results are cached by `(scenario_hash, test_hash)` tuple in `tools/critic/.cache/`. Cache invalidates when either the scenario text or test body changes.
*   **Graceful Fallback:** If `critic_llm_enabled` is `false` or the API is unavailable, the logic drift check is skipped entirely with a WARN-level note in the output. The overall Implementation Gate does not FAIL due to LLM unavailability.

### 2.5 Policy Adherence Scanner
*   **FORBIDDEN Pattern Discovery:** Scan all `features/arch_*.md` files for lines starting with `FORBIDDEN:` followed by a pattern (literal string or regex).
*   **Violation Scanning:** For each feature anchored to a policy with FORBIDDEN patterns, scan the feature's implementation files for matches.
*   **Implementation File Discovery:** Implementation files are located based on the feature's tool directory (derived from the feature file's label or explicit mapping).

### 2.6 User Testing Audit
*   **Discovery Scanning:** Parse the `## User Testing Discoveries` section of each feature file.
*   **Status Tracking:** Count entries by type (BUG, DISCOVERY, INTENT_DRIFT) and status (OPEN, SPEC_UPDATED, RESOLVED).
*   **Clean Status:** A feature with no OPEN or SPEC_UPDATED entries has `user_testing.status: "CLEAN"`. Otherwise `"HAS_OPEN_ITEMS"`.

### 2.7 Per-Feature Output
For each feature file, produce `tests/<feature_name>/critic.json`:
```json
{
    "generated_at": "<ISO 8601 timestamp>",
    "feature_file": "features/<name>.md",
    "spec_gate": {
        "status": "PASS | WARN | FAIL",
        "checks": {
            "section_completeness": {"status": "...", "detail": "..."},
            "scenario_classification": {"status": "...", "detail": "..."},
            "policy_anchoring": {"status": "...", "detail": "..."},
            "prerequisite_integrity": {"status": "...", "detail": "..."},
            "gherkin_quality": {"status": "...", "detail": "..."}
        }
    },
    "implementation_gate": {
        "status": "PASS | WARN | FAIL",
        "checks": {
            "traceability": {"status": "...", "coverage": 0.0, "detail": "..."},
            "policy_adherence": {"status": "...", "violations": [], "detail": "..."},
            "structural_completeness": {"status": "...", "detail": "..."},
            "builder_decisions": {"status": "...", "summary": {}, "detail": "..."},
            "logic_drift": {"status": "...", "pairs": [], "detail": "..."}
        }
    },
    "user_testing": {
        "status": "CLEAN | HAS_OPEN_ITEMS",
        "bugs": 0,
        "discoveries": 0,
        "intent_drifts": 0
    }
}
```

### 2.8 Aggregate Report
The tool MUST generate `CRITIC_REPORT.md` at the project root containing:
*   Summary table: feature name, spec gate status, implementation gate status, user testing status.
*   Builder decision audit: all AUTONOMOUS/DEVIATION/DISCOVERY entries across features.
*   Policy violations: all FORBIDDEN pattern matches.
*   Traceability gaps: scenarios without matching tests.
*   Open user testing items: all OPEN discoveries across features.

### 2.9 CDD Integration
*   **CDD Reads Critic Output:** The CDD Monitor reads `tests/<feature_name>/critic.json` alongside `tests/<feature_name>/tests.json`.
*   **New Fields in Status JSON:** Per-feature entries gain a `critic_status` field (`PASS`, `WARN`, `FAIL`, or omitted if no `critic.json` exists). The top-level status JSON gains a `critic_status` field aggregating all per-feature critic statuses (same aggregation logic as `test_status`).
*   **Dashboard Badge:** The web dashboard displays a `[CRITIC: PASS|WARN]` badge per feature.
*   **Optional Blocking:** When `critic_gate_blocking` is `true` in config, a feature with `critic_status: FAIL` cannot transition to COMPLETE via the normal status tag protocol. The CDD server enforces this by rejecting the transition (feature remains in its current state).

## 3. Scenarios

### Automated Scenarios

#### Scenario: Spec Gate Section Completeness Check
    Given a feature file exists with all required sections (Overview, Requirements, Scenarios)
    When the Critic tool runs the Spec Gate
    Then section_completeness reports PASS
    And the overall spec_gate status is not worse than WARN

#### Scenario: Spec Gate Missing Section
    Given a feature file is missing the Requirements section
    When the Critic tool runs the Spec Gate
    Then section_completeness reports FAIL
    And the overall spec_gate status is FAIL

#### Scenario: Spec Gate Policy Anchoring
    Given a feature file has a Prerequisite link to arch_critic_policy.md
    When the Critic tool runs the Spec Gate
    Then policy_anchoring reports PASS

#### Scenario: Spec Gate No Prerequisite on Non-Policy
    Given a non-policy feature file has no Prerequisite link
    When the Critic tool runs the Spec Gate
    Then policy_anchoring reports FAIL

#### Scenario: Spec Gate Policy File Is Exempt
    Given a feature file is itself an architectural policy (arch_*.md)
    When the Critic tool runs the Spec Gate
    Then policy_anchoring reports PASS regardless of Prerequisite links

#### Scenario: Implementation Gate Traceability Match
    Given a feature has automated scenarios with keywords "Bootstrap" and "Consumer" and "Project"
    And a test function named test_bootstrap_consumer_project exists
    When the Critic tool runs the Implementation Gate traceability check
    Then the scenario is matched to the test function
    And traceability reports PASS

#### Scenario: Implementation Gate Traceability Gap
    Given a feature has an automated scenario with no matching test functions
    When the Critic tool runs the Implementation Gate traceability check
    Then the scenario is flagged as unmatched
    And traceability reports WARN or FAIL based on coverage threshold

#### Scenario: Implementation Gate Builder Decision Audit
    Given a feature has Implementation Notes with [AUTONOMOUS] and [CLARIFICATION] tags
    When the Critic tool runs the builder decision check
    Then builder_decisions reports WARN due to the AUTONOMOUS entry

#### Scenario: Implementation Gate Policy Violation
    Given an architectural policy defines FORBIDDEN: hardcoded_port
    And a feature anchored to that policy has "hardcoded_port" in its implementation
    When the Critic tool runs the policy adherence check
    Then policy_adherence reports FAIL with the violation details

#### Scenario: User Testing Discovery Audit
    Given a feature file has a User Testing Discoveries section with 1 BUG (OPEN) and 1 DISCOVERY (SPEC_UPDATED)
    When the Critic tool runs the user testing audit
    Then user_testing.status is HAS_OPEN_ITEMS
    And user_testing.bugs is 1
    And user_testing.discoveries is 1

#### Scenario: Clean User Testing
    Given a feature file has an empty User Testing Discoveries section
    When the Critic tool runs the user testing audit
    Then user_testing.status is CLEAN

#### Scenario: Aggregate Report Generation
    Given the Critic tool has run on multiple feature files
    When the aggregate report is generated
    Then CRITIC_REPORT.md is created at the project root
    And it contains a summary table with all features

#### Scenario: Per-Feature Critic JSON Output
    Given the Critic tool completes analysis of a feature
    When the output is written
    Then tests/<feature_name>/critic.json is created
    And it contains valid JSON with spec_gate, implementation_gate, and user_testing sections

#### Scenario: Logic Drift Engine Disabled
    Given critic_llm_enabled is false in config
    When the Critic tool runs the Implementation Gate
    Then logic_drift is skipped with a WARN note
    And the overall implementation_gate status is not affected by the skip

#### Scenario: CDD Reads Critic Status
    Given tests/<feature_name>/critic.json exists with spec_gate.status PASS
    When the CDD server processes status for that feature
    Then the feature entry includes critic_status PASS

### Manual Scenarios (Human Verification Required)

#### Scenario: CDD Dashboard Critic Badge
    Given the CDD server is running
    And critic.json files exist for features
    When the User opens the web dashboard
    Then each feature entry shows a CRITIC badge with PASS or WARN

#### Scenario: Critic Report Readability
    Given CRITIC_REPORT.md has been generated
    When the User opens it
    Then it contains a clear summary table, builder decision audit, and traceability gaps

## 4. Implementation Notes
*   **Tool Location:** `tools/critic/` directory containing `critic.py` (main engine), `traceability.py`, `policy_check.py`, `logic_drift.py`, `test_critic.py`, and `run.sh` (executable convenience wrapper).
*   **Test Output:** Test results go to `tests/critic_tool/tests.json`.
*   **LLM Cache:** Stored in `tools/critic/.cache/` as JSON files keyed by hash pairs. This directory should be gitignored.
*   **No External Dependencies:** The deterministic components (Spec Gate, traceability, policy check) MUST NOT require any external packages beyond Python 3.9+ standard library. The LLM component requires the `anthropic` Python package only when enabled.

## User Testing Discoveries
