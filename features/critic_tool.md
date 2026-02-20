# Feature: Critic Quality Gate Tool

> Label: "Tool: Critic"
> Category: "Quality Assurance"
> Prerequisite: features/arch_critic_policy.md

## 1. Overview
The Critic tool is the project coordination engine. It performs dual-gate validation (Spec Gate + Implementation Gate) on feature files, audits user testing status, generates role-specific action items for each agent, and produces per-feature reports and an aggregate `CRITIC_REPORT.md`. Every agent runs the Critic at session start to determine their priorities.

## 2. Requirements

### 2.1 Spec Gate (Pre-Implementation Validation)
The Spec Gate validates that a feature specification is structurally complete and properly formed. It runs without requiring any implementation code.

Architectural policy files (`arch_*.md`) receive a REDUCED Spec Gate evaluation. They are checked only for section presence of Purpose and Invariants (not Overview/Requirements/Scenarios). Scenario classification and Gherkin quality checks are skipped (reported as PASS with "N/A - policy file"). Policy files also skip the Implementation Gate entirely — their `implementation_gate.status` is reported as "PASS" with detail "N/A - policy file exempt".

| Check | PASS | WARN | FAIL |
|-------|------|------|------|
| Section completeness | All required sections present (Overview, Requirements, Scenarios) | Implementation Notes empty | Missing Overview, Requirements, or Scenarios |
| Scenario classification | Both Automated + Manual subsections present | Only one subsection | No scenarios at all |
| Policy anchoring | Has `> Prerequisite:` linking to `arch_*.md` | Has prerequisite but not to a policy file; OR no prerequisite (unless IS a policy file) | Referenced prerequisite file missing on disk |
| Prerequisite integrity | All referenced prerequisite files exist on disk | N/A | Referenced file missing |
| Gherkin quality | All scenarios have Given/When/Then | Some scenarios missing steps | N/A (degrades to WARN) |

### 2.2 Implementation Gate (Post-Implementation Validation)
The Implementation Gate validates that the implementation aligns with the specification. It requires implementation code and test results to exist.

> Policy files (`arch_*.md`) are exempt from the Implementation Gate. All checks report PASS with "N/A - policy file exempt".

| Check | PASS | WARN | FAIL |
|-------|------|------|------|
| Traceability | All automated scenarios have matching tests | >80% scenario coverage | <80% scenario coverage |
| Policy adherence | No FORBIDDEN pattern violations | N/A | Any FORBIDDEN violation detected |
| Structural completeness | `tests/<feature>/tests.json` exists with `"status": "PASS"` | Exists with `"status": "FAIL"` | Missing `tests.json` |
| Builder decisions | All entries are INFO/CLARIFICATION | Has AUTONOMOUS entries | Has DEVIATION, unresolved DISCOVERY, or INFEASIBLE |
| Logic drift (LLM) | All pairs ALIGNED | Some PARTIAL | Any DIVERGENT |

### 2.3 Traceability Engine
*   **Keyword Extraction:** Extract keywords from automated scenario titles by stripping articles (a, an, the), prepositions (in, on, at, to, for, of, by, with, from, via), and conjunctions (and, or, but).
*   **Matching Algorithm:** For each automated scenario, search test entries (function names + bodies for Python, scenario markers + surrounding context for Bash) for matching keywords. A match requires 2 or more keywords present in the test entry.
*   **Manual Scenario Handling:** Manual scenarios are EXEMPT from traceability. If a manual scenario has matching automated tests, flag it as informational (not a failure).
*   **Traceability Overrides:** Feature files MAY include explicit `traceability_overrides` mappings in their Implementation Notes section to handle cases where keyword matching is insufficient. Format: `- traceability_override: "Scenario Title" -> test_function_name`.
*   **Test Discovery:** Tests are located at `tests/<feature_name>/` and within the tool directory specified by `tools_root` in config. The engine discovers both `test_*.py` (Python) and `test_*.sh` (Bash) test files.
*   **Bash Test File Support:** Bash test files (`test_*.sh`) use `[Scenario]` markers to delineate test entries. The engine parses lines matching `echo "[Scenario] <title>"` as scenario entry points. Each `[Scenario]` marker and its surrounding context (up to the next marker or end of file) form a test entry for keyword matching.

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
*   **Status Tracking:** Count entries by type (BUG, DISCOVERY, INTENT_DRIFT, SPEC_DISPUTE) and status (OPEN, SPEC_UPDATED, RESOLVED).
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
        "intent_drifts": 0,
        "spec_disputes": 0
    },
    "action_items": {
        "architect": [{"priority": "HIGH | MEDIUM | LOW", "category": "<source_category>", "feature": "<feature_name>", "description": "<imperative action>"}],
        "builder": [],
        "qa": []
    },
    "role_status": {
        "architect": "DONE | TODO",
        "builder": "DONE | TODO | FAIL | INFEASIBLE | BLOCKED",
        "qa": "CLEAN | TODO | FAIL | DISPUTED | N/A"
    }
}
```

### 2.8 Aggregate Report
The tool MUST generate `CRITIC_REPORT.md` at the project root containing:
*   Summary table: feature name, spec gate status, implementation gate status, user testing status.
*   **Action Items by Role:** A section with `### Architect`, `### Builder`, `### QA` subsections. Each subsection lists action items sorted by priority (HIGH first), aggregated across all features. This is the primary coordination output.
*   Builder decision audit: all AUTONOMOUS/DEVIATION/DISCOVERY entries across features.
*   Policy violations: all FORBIDDEN pattern matches.
*   Traceability gaps: scenarios without matching tests.
*   Open user testing items: all OPEN discoveries across features.

### 2.9 CDD Integration (Decoupled)
The Critic is agent-facing; CDD is human-facing. CDD does NOT run the Critic.

*   **Role Status Contract:** CDD reads the `role_status` object from on-disk `tests/<feature_name>/critic.json` files to display Architect, Builder, and QA columns on the dashboard and in the `/status.json` API. CDD does NOT read or display spec_gate or implementation_gate status directly.
*   **No Blocking:** The `critic_gate_blocking` config key is deprecated (no-op). CDD does not gate status transitions based on Critic results.
*   **No Legacy Fields:** The CDD `/status.json` endpoint does NOT include `critic_status`, `test_status`, or `qa_status` fields. Per-feature entries expose `architect`, `builder`, and `qa` fields read from `role_status` when a `critic.json` file exists on disk.

### 2.10 Role-Specific Action Item Generation
The Critic MUST generate imperative action items for each role based on the analysis results. Action items are derived as follows:

| Role | Source | Example Item |
|------|--------|-------------|
| **Architect** | Spec Gate FAIL (missing sections, broken prereqs) | "Fix spec gap: section_completeness -- missing Requirements" |
| **Architect** | OPEN DISCOVERY/INTENT_DRIFT in User Testing | "Update spec for cdd_status_monitor: [discovery title]" |
| **Architect** | OPEN SPEC_DISPUTE in User Testing | "Review disputed scenario in critic_tool: [dispute title]" |
| **Architect** | `[INFEASIBLE]` tag in Implementation Notes | "Revise infeasible spec for submodule_sync: [rationale]" |
| **Architect** | Unacknowledged `[DEVIATION]`/`[DISCOVERY]` tags | "Acknowledge Builder decision in critic_tool: [tag title]" |
| **Architect** | Spec Gate WARN (no manual scenarios, empty impl notes) | "Improve spec: scenario_classification -- only Automated" |
| **Builder** | Structural completeness FAIL (missing/failing tests) | "Fix failing tests for submodule_bootstrap" |
| **Builder** | Traceability gaps (unmatched scenarios) | "Write tests for: Zero-Queue Verification" |
| **Builder** | OPEN BUGs in User Testing | "Fix bug in critic_tool: [bug title]" |
| **QA** | Features in TESTING status (from CDD feature_status.json) | "Verify cdd_status_monitor: 3 manual scenarios" |
| **QA** | SPEC_UPDATED discoveries | "Re-verify critic_tool: [item title]" |

**Priority Levels:**
*   **CRITICAL** -- `[INFEASIBLE]` tags (feature halted, Architect must revise spec).
*   **HIGH** -- Gate FAIL, OPEN BUGs, OPEN SPEC_DISPUTEs, unacknowledged DEVIATIONs/DISCOVERYs.
*   **MEDIUM** -- Traceability gaps, SPEC_UPDATED items awaiting re-verification.
*   **LOW** -- Gate WARNs, informational items.

**CDD Feature Status Dependency:** QA action items that depend on CDD feature status (TESTING state) require `tools/cdd/feature_status.json` to exist on disk. If unavailable, the Critic skips status-dependent QA items with a note in the report.

### 2.11 Role Status Computation
The Critic MUST compute a `role_status` object for each feature, summarizing whether each agent role has outstanding work. This is the primary input for CDD's role-based dashboard.

**Architect Status:**
*   `TODO`: Any HIGH or CRITICAL priority Architect action items exist (Spec Gate FAIL, open SPEC_DISPUTE, INFEASIBLE tag, open DISCOVERY/INTENT_DRIFT, unacknowledged DEVIATION).
*   `DONE`: No HIGH or CRITICAL Architect action items.

**Builder Status:**
*   `DONE`: structural_completeness PASS (tests.json exists with PASS), no open BUGs, no FAIL-level traceability issues.
*   `TODO`: Has Builder action items to address (needs implementation, traceability gaps, etc.).
*   `FAIL`: tests.json exists with status FAIL.
*   `INFEASIBLE`: `[INFEASIBLE]` tag present in Implementation Notes (Builder halted, escalated to Architect).
*   `BLOCKED`: Active SPEC_DISPUTE exists for this feature (scenarios suspended, Builder cannot implement).

**Builder Precedence (highest wins):** INFEASIBLE > BLOCKED > FAIL > TODO > DONE.

**QA Status:**
*   `CLEAN`: user_testing.status is CLEAN and feature has been verified (is or was in TESTING/COMPLETE lifecycle state).
*   `TODO`: Feature in TESTING lifecycle state with SPEC_UPDATED items awaiting re-verification, or no verification done yet.
*   `FAIL`: Has OPEN BUGs in User Testing Discoveries.
*   `DISPUTED`: Has OPEN SPEC_DISPUTEs in User Testing Discoveries (no BUGs).
*   `N/A`: Feature not yet in TESTING or COMPLETE lifecycle state (not ready for QA).

**QA Precedence (highest wins):** FAIL > DISPUTED > TODO > CLEAN > N/A.

**Lifecycle State Dependency:** QA status computation requires `tools/cdd/feature_status.json` to determine the feature's lifecycle state (TODO/TESTING/COMPLETE). If unavailable, QA status defaults to `N/A` with a note in the report.

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

#### Scenario: Bash Test File Discovery
    Given a feature has test files at tests/<feature_name>/
    And both test_feature.py and test_feature.sh exist
    When the Critic tool discovers test files
    Then both Python and Bash test files are included in the test file list

#### Scenario: Bash Scenario Keyword Matching
    Given a Bash test file contains echo "[Scenario] Bootstrap Consumer Project"
    And a feature has an automated scenario titled "Bootstrap Consumer Project Setup"
    When the Critic tool runs the traceability check
    Then the scenario is matched to the Bash test entry via keyword matching

#### Scenario: Architect Action Items from Spec Gaps
    Given a feature has spec_gate.status FAIL due to missing Requirements section
    When the Critic tool generates action items
    Then an Architect action item is created with priority HIGH
    And the description identifies the specific spec gap

#### Scenario: Builder Action Items from Traceability Gaps
    Given a feature has an automated scenario with no matching test
    When the Critic tool generates action items
    Then a Builder action item is created with priority MEDIUM
    And the description identifies the unmatched scenario title

#### Scenario: QA Action Items from TESTING Status
    Given a feature is in TESTING state per CDD feature_status.json
    And the feature has 3 manual scenarios
    When the Critic tool generates action items
    Then a QA action item is created identifying the feature and scenario count

#### Scenario: Action Items in Critic JSON Output
    Given the Critic tool completes analysis of a feature with spec gaps and traceability gaps
    When the per-feature critic.json is written
    Then it contains an action_items object with architect, builder, and qa arrays

#### Scenario: Action Items in Aggregate Report
    Given the Critic tool has run on multiple features with various gaps
    When CRITIC_REPORT.md is generated
    Then it contains an "Action Items by Role" section
    And each role subsection lists items sorted by priority

#### Scenario: Architect Action Items from Spec Dispute
    Given a feature has an OPEN SPEC_DISPUTE in User Testing Discoveries
    When the Critic tool generates action items
    Then an Architect action item is created with priority HIGH
    And the description references the disputed scenario and the user's rationale

#### Scenario: Architect Action Items from Infeasible Feature
    Given a feature has an [INFEASIBLE] tag in Implementation Notes
    When the Critic tool generates action items
    Then an Architect action item is created with priority CRITICAL
    And the description references the infeasibility rationale

#### Scenario: Spec Dispute Counted in User Testing Audit
    Given a feature file has a User Testing Discoveries section with 1 SPEC_DISPUTE (OPEN)
    When the Critic tool runs the user testing audit
    Then user_testing.status is HAS_OPEN_ITEMS
    And user_testing.spec_disputes is 1

#### Scenario: Role Status Architect TODO
    Given a feature has a Spec Gate FAIL (missing Requirements section)
    When the Critic tool computes role_status
    Then role_status.architect is TODO

#### Scenario: Role Status Architect DONE
    Given a feature has no HIGH or CRITICAL Architect action items
    When the Critic tool computes role_status
    Then role_status.architect is DONE

#### Scenario: Role Status Builder DONE
    Given a feature has structural_completeness PASS and no open BUGs
    When the Critic tool computes role_status
    Then role_status.builder is DONE

#### Scenario: Role Status Builder FAIL
    Given a feature has tests.json with status FAIL
    When the Critic tool computes role_status
    Then role_status.builder is FAIL

#### Scenario: Role Status Builder INFEASIBLE
    Given a feature has an [INFEASIBLE] tag in Implementation Notes
    And tests.json exists with status FAIL
    When the Critic tool computes role_status
    Then role_status.builder is INFEASIBLE
    And INFEASIBLE takes precedence over FAIL

#### Scenario: Role Status Builder BLOCKED
    Given a feature has an OPEN SPEC_DISPUTE in User Testing Discoveries
    And no [INFEASIBLE] tag exists
    When the Critic tool computes role_status
    Then role_status.builder is BLOCKED

#### Scenario: Role Status QA CLEAN
    Given a feature has user_testing.status CLEAN
    And the feature is in COMPLETE lifecycle state per feature_status.json
    When the Critic tool computes role_status
    Then role_status.qa is CLEAN

#### Scenario: Role Status QA FAIL
    Given a feature has OPEN BUGs in User Testing Discoveries
    When the Critic tool computes role_status
    Then role_status.qa is FAIL

#### Scenario: Role Status QA DISPUTED
    Given a feature has OPEN SPEC_DISPUTEs but no OPEN BUGs
    When the Critic tool computes role_status
    Then role_status.qa is DISPUTED

#### Scenario: Role Status QA N/A
    Given a feature is in TODO lifecycle state (not yet in TESTING or COMPLETE)
    When the Critic tool computes role_status
    Then role_status.qa is N/A

#### Scenario: Role Status in Critic JSON Output
    Given the Critic tool completes analysis of a feature
    When the per-feature critic.json is written
    Then it contains a role_status object with architect, builder, and qa fields
    And the values conform to the defined status enums

#### Scenario: Spec Gate Policy File Reduced Evaluation
    Given a feature file is an architectural policy (arch_*.md)
    When the Critic tool runs the Spec Gate
    Then section_completeness checks for Purpose and Invariants instead of Overview/Requirements/Scenarios
    And scenario_classification and gherkin_quality report PASS with "N/A - policy file"

#### Scenario: Implementation Gate Policy File Exempt
    Given a feature file is an architectural policy (arch_*.md)
    When the Critic tool runs the Implementation Gate
    Then all checks report PASS with "N/A - policy file exempt"
    And the overall implementation_gate status is PASS

### Manual Scenarios (Human Verification Required)

#### Scenario: CDD Dashboard Role Columns
    Given the CDD server is running
    And critic.json files exist for features with role_status computed
    When the User opens the web dashboard
    Then each feature entry shows Architect, Builder, and QA columns with role status badges
    And features without critic.json show "--" in all role columns

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
