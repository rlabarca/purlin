# Feature: Critic Quality Gate Tool

> Label: "Tool: Critic"
> Category: "Coordination & Lifecycle"
> Prerequisite: features/policy_critic.md

## 1. Overview
The Critic tool is the project coordination engine. It performs dual-gate validation (Spec Gate + Implementation Gate) on feature files, audits user testing status, generates role-specific action items for each agent, and produces per-feature reports and an aggregate `CRITIC_REPORT.md`. Every agent runs the Critic at session start to determine their priorities.

## 2. Requirements

### 2.1 Spec Gate (Pre-Implementation Validation)
The Spec Gate validates that a feature specification is structurally complete and properly formed. It runs without requiring any implementation code.

Anchor node files (`arch_*.md`, `design_*.md`, `policy_*.md`) receive a REDUCED Spec Gate evaluation. They are checked only for section presence of Purpose and Invariants (not Overview/Requirements/Scenarios). Scenario classification and Gherkin quality checks are skipped (reported as PASS with "N/A - anchor node"). Anchor nodes also skip the Implementation Gate entirely — their `implementation_gate.status` is reported as "PASS" with detail "N/A - anchor node exempt".

| Check | PASS | WARN | FAIL |
|-------|------|------|------|
| Section completeness | All required sections present (Overview, Requirements, Scenarios) | Implementation Notes empty | Missing Overview, Requirements, or Scenarios |
| Scenario classification | Both subsections present (with content or explicit "None" declaration) | Only one subsection with no explicit opt-out for the other | No scenarios at all |
| Policy anchoring | Has `> Prerequisite:` linking to an anchor node (`arch_*.md`, `design_*.md`, `policy_*.md`); OR has prerequisite to non-anchor-node file (feature is grounded) | No prerequisite (unless IS an anchor node) | Referenced prerequisite file missing on disk |
| Prerequisite integrity | All referenced prerequisite files exist on disk | N/A | Referenced file missing |
| Gherkin quality | All scenarios have Given/When/Then | Some scenarios missing steps | N/A (degrades to WARN) |

### 2.2 Implementation Gate (Post-Implementation Validation)
The Implementation Gate validates that the implementation aligns with the specification. It requires implementation code and test results to exist.

> Anchor node files (`arch_*.md`, `design_*.md`, `policy_*.md`) are exempt from the Implementation Gate. All checks report PASS with "N/A - anchor node exempt".

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
*   **Configuration:** Controlled by `critic_llm_model` (default `claude-sonnet-4-20250514`) and `critic_llm_enabled` (default `false`) in `.purlin/config.json`.
*   **Caching:** Results are cached by `(scenario_hash, test_hash)` tuple in `tools/critic/.cache/`. Cache invalidates when either the scenario text or test body changes.
*   **Graceful Fallback:** If `critic_llm_enabled` is `false` or the API is unavailable, the logic drift check is skipped entirely with a WARN-level note in the output. The overall Implementation Gate does not FAIL due to LLM unavailability.

### 2.5 Policy Adherence Scanner
*   **FORBIDDEN Pattern Discovery:** Scan all anchor node files (`features/arch_*.md`, `features/design_*.md`, `features/policy_*.md`) for lines starting with `FORBIDDEN:` followed by a pattern (literal string or regex).
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
The Critic is agent-facing; CDD is human-facing. The CDD **web server** does NOT auto-run the Critic on requests -- it reads from pre-computed `critic.json` files only. The `tools/cdd/status.sh` CLI tool, however, DOES auto-run the Critic before outputting status (see `cdd_status_monitor.md` Section 2.6), ensuring agents always receive fresh data from a single invocation.

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
| **Architect** | Untracked files detected (Section 2.12) | "Triage untracked file: tests/critic_tool/critic.json" |
| **Builder** | Feature in TODO lifecycle state (spec modified after last status commit) | "Review and implement spec changes for critic_tool" |
| **Builder** | Structural completeness FAIL (missing/failing tests) | "Fix failing tests for submodule_bootstrap" |
| **Builder** | Traceability gaps (unmatched scenarios) | "Write tests for: Zero-Queue Verification" |
| **Builder** | OPEN BUGs in User Testing | "Fix bug in critic_tool: [bug title]" |
| **Builder** | Cross-validation warnings in regression scope (invalid targeted scope names) | "Fix scope declaration for critic_tool: Targeted scope name 'Bad Name' does not match any #### Scenario: title" |
| **QA** | Features in TESTING status with manual scenarios (from CDD feature_status.json) | "Verify cdd_status_monitor: 3 manual scenario(s)" |
| **QA** | SPEC_UPDATED discoveries (feature in TESTING lifecycle) | "Re-verify critic_tool: [item title]" |

**QA Action Item Filtering:** QA verification items (from TESTING status) are only generated when the feature has at least one manual scenario. Features with 0 manual scenarios do not generate QA verification action items.

**SPEC_UPDATED Lifecycle Routing:** SPEC_UPDATED discoveries do NOT generate Builder action items. Builder signaling comes from the feature lifecycle: when the Architect updates a spec to address a discovery, the feature resets to TODO lifecycle, which gives the Builder a TODO via the lifecycle-based action item ("Review and implement spec changes"). After the Builder commits (feature enters TESTING), the SPEC_UPDATED discovery generates a QA re-verification item. The `Action Required` field on discoveries is informational only and does not drive Critic routing. This ensures at most one role has actionable work at a time per discovery, making the CDD dashboard unambiguous about which agent to run next.

**QA Re-verification Filtering:** QA re-verification items (from SPEC_UPDATED discoveries) are only generated when the feature is in TESTING lifecycle state. This prevents QA=TODO while the Builder is still implementing (feature in TODO lifecycle).

**Priority Levels:**
*   **CRITICAL** -- `[INFEASIBLE]` tags (feature halted, Architect must revise spec).
*   **HIGH** -- Gate FAIL, OPEN BUGs, OPEN SPEC_DISPUTEs, unacknowledged DEVIATIONs/DISCOVERYs.
*   **HIGH** -- Feature in TODO lifecycle state (spec modified, implementation review needed).
*   **MEDIUM** -- Traceability gaps, SPEC_UPDATED items awaiting QA re-verification, invalid targeted scope names.
*   **LOW** -- Gate WARNs, informational items.

**CDD Feature Status Dependency:** Builder and QA action items that depend on CDD feature status (TODO or TESTING state) require `.purlin/cache/feature_status.json` to exist on disk. The `tools/cdd/status.sh` CLI tool triggers a Critic run before outputting status (see `cdd_status_monitor.md` Section 2.6). The Critic's own `run.sh` wrapper still invokes `tools/cdd/status.sh` internally to refresh `feature_status.json` before launching `critic.py`; the `CRITIC_RUNNING` guard prevents that inner call from triggering a second Critic run. If the CDD tool is unavailable or fails, the Critic proceeds with whatever cached data exists; if no file is found, lifecycle-dependent items are skipped with a note in the report.

### 2.11 Role Status Computation
The Critic MUST compute a `role_status` object for each feature, summarizing whether each agent role has outstanding work. This is the primary input for CDD's role-based dashboard.

**Architect Status:**
*   `TODO`: Any HIGH or CRITICAL priority Architect action items exist (Spec Gate FAIL, open SPEC_DISPUTE, INFEASIBLE tag, open DISCOVERY/INTENT_DRIFT, unacknowledged DEVIATION).
*   `DONE`: No HIGH or CRITICAL Architect action items.

**Builder Status:**
*   `DONE`: structural_completeness PASS (tests.json exists with PASS), no open BUGs, no FAIL-level traceability issues, AND feature is NOT in TODO lifecycle state.
*   `TODO`: Feature is in TODO lifecycle state (spec modified after last status commit, implementation review needed), OR has other Builder action items to address (traceability gaps, open BUGs, etc.).
*   `FAIL`: tests.json exists with status FAIL.
*   `INFEASIBLE`: `[INFEASIBLE]` tag present in Implementation Notes (Builder halted, escalated to Architect).
*   `BLOCKED`: Active SPEC_DISPUTE exists for this feature (scenarios suspended, Builder cannot implement).

**Builder Precedence (highest wins):** INFEASIBLE > BLOCKED > FAIL > TODO > DONE.

**Builder Lifecycle State Dependency:** Builder status computation requires `.purlin/cache/feature_status.json` to determine the feature's lifecycle state. If the feature is in TODO lifecycle state, Builder is TODO regardless of traceability or test status -- the spec has changed and the implementation must be reviewed. If `feature_status.json` is unavailable, lifecycle-based TODO detection is skipped with a note in the report.

**QA Status:**
*   `FAIL`: Has OPEN BUGs in User Testing Discoveries. (Lifecycle-independent.)
*   `DISPUTED`: Has OPEN SPEC_DISPUTEs in User Testing Discoveries (no BUGs). (Lifecycle-independent.)
*   `TODO`: Any of: (a) Feature in TESTING lifecycle state with at least one manual scenario to verify; (b) Has SPEC_UPDATED items AND feature is in TESTING lifecycle state (Builder has committed, QA can now re-verify). No OPEN BUGs or SPEC_DISPUTEs.
*   `CLEAN`: `tests/<feature>/tests.json` exists with `status: "PASS"`, AND no FAIL/DISPUTED/TODO conditions matched. Lifecycle-independent. OPEN discoveries routing to other roles (Architect-routed DISCOVERYs, INTENT_DRIFTs) do NOT block CLEAN -- QA has no actionable work for items awaiting Architect or Builder.
*   `N/A`: No FAIL/DISPUTED/TODO/CLEAN conditions matched. Catch-all for features with no `tests.json` on disk, or `tests.json` with FAIL status and no QA-specific concerns.

**QA Precedence (highest wins):** FAIL > DISPUTED > TODO > CLEAN > N/A.

**QA Actionability Principle:** QA=TODO only when QA has work to do RIGHT NOW. OPEN items routing to Architect (DISCOVERYs, INTENT_DRIFTs) and SPEC_UPDATED items waiting for Builder (feature in TODO lifecycle) are not QA-actionable. This ensures the CDD dashboard shows at most one role with actionable TODO per discovery lifecycle step, making it unambiguous which agent to run next.

**Lifecycle State Dependency:** QA TODO conditions (a) and (b) both use `.purlin/cache/feature_status.json` to determine the feature's lifecycle state (TESTING). If unavailable, TESTING-based TODO detection is skipped for both conditions. FAIL, DISPUTED, CLEAN, and N/A are lifecycle-independent.

### 2.12 Regression Scope Computation
The Critic MUST compute a regression set for each TESTING feature based on the Builder's declared change scope. The scope is extracted from the most recent status commit message for the feature.

*   **Scope Extraction:** Parse `[Scope: <type>]` from the status commit message. If absent, default to `full`.
*   **Regression Set Computation (`compute_regression_set`):**
    *   `full` (or missing) -- All manual scenarios AND all visual checklist items.
    *   `targeted:<exact names>` (per `policy_critic.md` Section 2.8 naming contract) -- Only the named scenarios. Visual verification is skipped unless a visual screen name is explicitly listed.
    *   `cosmetic` -- Empty set (QA skip). No scenarios or visual items queued. **First-Pass Guard:** The Critic MUST read the previous on-disk `tests/<feature_name>/critic.json` before applying cosmetic suppression. If `role_status.qa != "CLEAN"` (or the file does not exist), escalate declared scope to `full` and append a `cross_validation_warning`: `"Cosmetic scope declared but no prior clean QA pass exists for this feature. Escalating to full verification."`
    *   `dependency-only` -- Scenarios referencing the changed prerequisite's surface area. Determined by cross-referencing the feature's prerequisite links with the dependency graph.
*   **Cross-Validation:** If the declared scope is `cosmetic` but the status commit modifies files that are referenced by manual scenarios (detected via git diff of the commit), the Critic MUST emit a WARNING in the report and in the feature's `critic.json`.
*   **Scope Name Validation Action Items:** Cross-validation warnings from `targeted:` scope name validation (names not matching any `#### Scenario:` or `### Screen:` title per `policy_critic.md` Section 2.8 naming contract) MUST be surfaced as MEDIUM-priority Builder action items with category `scope_validation`. These appear in both the per-feature `critic.json` action items and the aggregate `CRITIC_REPORT.md` under the Builder section. **First-pass guard escalation warnings and cosmetic cross-file validation warnings are informational only and MUST NOT generate Builder action items.** The guard conditions these items exclusively on the original declared scope being `targeted:` — if `regression_scope.declared` does not start with `targeted:`, no `scope_validation` Builder items are generated regardless of the content of `cross_validation_warnings`.
*   **Scoped QA Action Items:** The Critic MUST modify QA action item generation to use the regression set:
    *   `full` -- `"Verify X: N manual scenario(s), M visual item(s)"`
    *   `targeted` -- `"Verify X: 2 targeted scenario(s) [Scenario A, Scenario B]"`
    *   `cosmetic` -- `"QA skip (cosmetic change) -- 0 scenarios queued"`
    *   `dependency-only` -- `"Verify X: N scenario(s) touching changed dependency surface"`
*   **Per-Feature Output:** Include a `regression_scope` block in `tests/<feature_name>/critic.json`:
    ```json
    "regression_scope": {
        "declared": "full | targeted:... | cosmetic | dependency-only",
        "scenarios": ["Scenario A", "Scenario B"],
        "visual_items": 0,
        "cross_validation_warnings": []
    }
    ```

### 2.13 Visual Specification Detection
The Critic MUST detect and report `## Visual Specification` sections in feature files.

*   **Detection (`has_visual_spec`):** Check for the presence of a `## Visual Specification` heading in the feature file content.
*   **Item Counting:** Count checklist items (lines matching `- [ ]` or `- [x]`) within the visual specification section. Count `### Screen:` subsections.
*   **QA Action Items:** Generate separate QA action items for visual verification: `"Visual verify X: N checklist item(s) across M screen(s)"`. These are distinct from functional scenario verification items.
*   **Per-Feature Output:** Include a `visual_spec` block in `tests/<feature_name>/critic.json`:
    ```json
    "visual_spec": {
        "present": true,
        "screens": 2,
        "items": 8
    }
    ```
    When no visual spec exists: `"visual_spec": {"present": false, "screens": 0, "items": 0}`.
*   **Traceability Exemption:** Visual checklist items are NOT subject to Gherkin traceability checks. They do not generate traceability gaps.
*   **Scope Interaction:** Visual verification items are included in regression scope computation. A `cosmetic` scope skips visual items. A `targeted` scope skips visual unless explicitly targeted. A `full` scope includes all visual items.

### 2.14 Untracked File Audit
The Critic MUST detect untracked files in the working directory and generate Architect action items for triage.

*   **Detection:** Run `git status --porcelain` and collect all untracked entries (lines starting with `??`).
*   **Filtering:** Exclude files and directories already covered by `.gitignore` patterns (git handles this automatically). Also exclude the `.purlin/` directory and any files inside `.claude/`.
*   **Action Item Generation:** For each untracked file (or untracked directory, reported as a single entry), generate an Architect action item:
    *   Priority: **MEDIUM**.
    *   Category: `untracked_file`.
    *   Description: `"Triage untracked file: <path> (commit, gitignore, or delegate to Builder)"`.
*   **Aggregate Report:** Untracked files are listed in a dedicated `### Untracked Files` subsection of the Architect action items in `CRITIC_REPORT.md`.
*   **No Per-Feature Association:** Untracked file items are project-level, not tied to a specific feature. They appear in the aggregate report only (not in per-feature `critic.json` files).

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
    Given a feature file has a Prerequisite link to policy_critic.md
    When the Critic tool runs the Spec Gate
    Then policy_anchoring reports PASS

#### Scenario: Spec Gate Non-Anchor-Node Prerequisite
    Given a feature file has a Prerequisite link to another feature file (not an anchor node)
    When the Critic tool runs the Spec Gate
    Then policy_anchoring reports PASS

#### Scenario: Spec Gate No Prerequisite on Non-Policy
    Given a non-policy feature file has no Prerequisite link
    When the Critic tool runs the Spec Gate
    Then policy_anchoring reports WARN

#### Scenario: Scenario Classification Explicit None for Manual
    Given a feature file has Automated Scenarios with content
    And the Manual Scenarios subsection explicitly declares "None"
    When the Critic tool runs the Spec Gate
    Then scenario_classification reports PASS

#### Scenario: Spec Gate Anchor Node Is Exempt
    Given a feature file is itself an anchor node (arch_*.md, design_*.md, or policy_*.md)
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

#### Scenario: Builder Action Items from Lifecycle Reset
    Given a feature was previously in TESTING or COMPLETE lifecycle state
    And the feature spec is modified (file edit after status commit)
    And the feature lifecycle resets to TODO per feature_status.json
    When the Critic tool generates action items
    Then a Builder action item is created with priority HIGH
    And the description says "Review and implement spec changes for <feature_name>"
    And role_status.builder is TODO

#### Scenario: SPEC_UPDATED Discovery Does Not Generate Builder Action Items
    Given a feature has a SPEC_UPDATED discovery in User Testing Discoveries
    And the discovery has "Action Required: Builder"
    When the Critic tool generates action items
    Then no Builder action item is created from the SPEC_UPDATED discovery
    And Builder signaling comes from the feature lifecycle state (TODO or DONE) not from discovery routing

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

#### Scenario: Aggregate Report Structural Completeness
    Given the Critic tool has run on multiple feature files
    When CRITIC_REPORT.md is generated
    Then it contains a "Summary" section with a table having Feature, Spec Gate, Implementation Gate, and User Testing columns
    And it contains an "Action Items by Role" section with Architect, Builder, and QA subsections
    And it contains a "Builder Decision Audit" section
    And it contains a "Policy Violations" section
    And it contains a "Traceability Gaps" section
    And it contains an "Open User Testing Items" section

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
    And tests/<feature>/tests.json exists with status PASS
    When the Critic tool computes role_status
    Then role_status.qa is CLEAN

#### Scenario: Role Status QA TODO for TESTING Feature
    Given a feature has user_testing.status CLEAN
    And the feature is in TESTING lifecycle state per feature_status.json
    And the feature has at least one manual scenario
    When the Critic tool computes role_status
    Then role_status.qa is TODO
    And role_status.qa is NOT CLEAN

#### Scenario: Role Status QA FAIL
    Given a feature has OPEN BUGs in User Testing Discoveries
    When the Critic tool computes role_status
    Then role_status.qa is FAIL

#### Scenario: Role Status QA DISPUTED
    Given a feature has OPEN SPEC_DISPUTEs but no OPEN BUGs
    When the Critic tool computes role_status
    Then role_status.qa is DISPUTED

#### Scenario: Role Status QA N/A
    Given no tests/<feature>/tests.json exists on disk
    And the feature has no open user testing items
    When the Critic tool computes role_status
    Then role_status.qa is N/A

#### Scenario: Role Status QA DISPUTED in Non-TESTING Lifecycle
    Given a feature has OPEN SPEC_DISPUTEs but no OPEN BUGs
    And the feature is in TODO lifecycle state per feature_status.json
    When the Critic tool computes role_status
    Then role_status.qa is DISPUTED
    And DISPUTED takes precedence over N/A

#### Scenario: Role Status QA TODO for SPEC_UPDATED Items in TESTING
    Given a feature has SPEC_UPDATED items in User Testing Discoveries
    And the feature has no OPEN BUGs or SPEC_DISPUTEs
    And the feature is in TESTING lifecycle state
    When the Critic tool computes role_status
    Then role_status.qa is TODO

#### Scenario: Role Status QA CLEAN Despite OPEN Discoveries Routing to Architect
    Given a feature has OPEN discoveries in User Testing Discoveries routing to Architect
    And the feature has no OPEN BUGs or SPEC_DISPUTEs
    And tests/<feature>/tests.json exists with status PASS
    When the Critic tool computes role_status
    Then role_status.qa is CLEAN
    And role_status.architect is TODO

#### Scenario: Role Status QA CLEAN for SPEC_UPDATED in TODO Lifecycle
    Given a feature has SPEC_UPDATED items in User Testing Discoveries
    And the feature is in TODO lifecycle state (Builder has not yet committed)
    And tests/<feature>/tests.json exists with status PASS
    When the Critic tool computes role_status
    Then role_status.qa is CLEAN
    And role_status.builder is TODO

#### Scenario: Role Status QA CLEAN for Feature with Passing Tests and No Manual Scenarios
    Given a feature is in TESTING lifecycle state
    And the feature has 0 manual scenarios
    And user_testing.status is CLEAN
    And tests/<feature>/tests.json exists with status PASS
    When the Critic tool computes role_status
    Then role_status.qa is CLEAN

#### Scenario: Role Status in Critic JSON Output
    Given the Critic tool completes analysis of a feature
    When the per-feature critic.json is written
    Then it contains a role_status object with architect, builder, and qa fields
    And the values conform to the defined status enums

#### Scenario: Untracked File Detection
    Given untracked files exist in the working directory (not covered by .gitignore)
    When the Critic tool runs the untracked file audit
    Then an Architect action item is created for each untracked file or directory
    And each item has priority MEDIUM and category untracked_file

#### Scenario: Untracked Files in Aggregate Report
    Given the Critic tool detects untracked files
    When CRITIC_REPORT.md is generated
    Then the Architect action items section includes an "Untracked Files" subsection
    And each untracked path is listed with a triage instruction

#### Scenario: Regression Scope Full Default
    Given a feature is in TESTING state
    And the most recent status commit has no [Scope: ...] trailer
    When the Critic computes the regression set
    Then the regression_scope.declared is "full"
    And the regression set includes all manual scenarios
    And the regression set includes all visual checklist items

#### Scenario: Regression Scope Targeted
    Given a feature is in TESTING state
    And the most recent status commit contains [Scope: targeted:Web Dashboard Display,Role Columns on Dashboard]
    When the Critic computes the regression set
    Then the regression_scope.declared is "targeted:Web Dashboard Display,Role Columns on Dashboard"
    And the regression_scope.scenarios contains exactly "Web Dashboard Display" and "Role Columns on Dashboard"
    And visual verification is skipped

#### Scenario: Regression Scope Cosmetic
    Given a feature is in TESTING state
    And the most recent status commit contains [Scope: cosmetic]
    And the feature's previous tests/<feature>/critic.json shows role_status.qa set to "CLEAN"
    When the Critic computes the regression set
    Then the regression_scope.declared is "cosmetic"
    And the regression set is empty (0 scenarios, 0 visual items)
    And the QA action item reads "QA skip (cosmetic change)"

#### Scenario: Cosmetic Scope Does Not Skip First-Time Verification
    Given a feature is in TESTING state
    And the most recent status commit contains [Scope: cosmetic]
    And the feature's previous tests/<feature>/critic.json has role_status.qa set to "TODO"
    When the Critic computes the regression set
    Then the regression_scope.declared is "full"
    And the regression_scope.cross_validation_warnings contains a message about no prior clean pass
    And the QA action item describes full verification, not a skip

#### Scenario: Regression Scope Dependency Only
    Given a feature is in TESTING state
    And the most recent status commit contains [Scope: dependency-only]
    And the feature has a prerequisite to policy_critic.md
    When the Critic computes the regression set
    Then the regression_scope.declared is "dependency-only"
    And the regression set includes only scenarios referencing the prerequisite surface

#### Scenario: Regression Scope Cross-Validation Warning
    Given a feature is in TESTING state
    And the most recent status commit contains [Scope: cosmetic]
    And the status commit modifies files referenced by manual scenarios
    When the Critic computes the regression set
    Then a cross-validation WARNING is emitted
    And the warning appears in regression_scope.cross_validation_warnings
    And the warning appears in CRITIC_REPORT.md

#### Scenario: Regression Scope in Critic JSON Output
    Given the Critic tool completes analysis of a TESTING feature
    When the per-feature critic.json is written
    Then it contains a regression_scope object with declared, scenarios, visual_items, and cross_validation_warnings fields

#### Scenario: Visual Specification Detected
    Given a feature file contains a "## Visual Specification" section
    And the section has 2 screens with 8 total checklist items
    When the Critic tool runs analysis
    Then visual_spec.present is true
    And visual_spec.screens is 2
    And visual_spec.items is 8

#### Scenario: Visual Specification Not Present
    Given a feature file does not contain a "## Visual Specification" section
    When the Critic tool runs analysis
    Then visual_spec.present is false
    And visual_spec.screens is 0
    And visual_spec.items is 0

#### Scenario: Visual Specification QA Action Item
    Given a feature is in TESTING state with a visual specification (3 screens, 12 items)
    And the regression scope is full
    When the Critic generates QA action items
    Then a separate visual QA action item is created: "Visual verify X: 12 checklist item(s) across 3 screen(s)"
    And the visual item is distinct from the functional scenario verification item

#### Scenario: Visual Specification Exempt from Traceability
    Given a feature file contains a "## Visual Specification" section with checklist items
    When the Critic tool runs the Implementation Gate traceability check
    Then visual checklist items are not counted as unmatched scenarios
    And visual items do not affect the traceability coverage percentage

#### Scenario: Scoped QA Action Item for Targeted Scope
    Given a feature is in TESTING state with 5 manual scenarios
    And the regression scope is targeted:Scenario A,Scenario B
    When the Critic generates QA action items
    Then the QA action item reads "Verify X: 2 targeted scenario(s) [Scenario A, Scenario B]"
    And scenarios not in the target list are not included in the action item

#### Scenario: Builder Action Items from Invalid Targeted Scope Names
    Given a feature is in TESTING state
    And the most recent status commit contains [Scope: targeted:Nonexistent Scenario]
    And "Nonexistent Scenario" does not match any #### Scenario: title in the feature spec
    When the Critic generates action items
    Then a Builder action item is created with priority MEDIUM and category scope_validation
    And the description includes the invalid scope name
    And the action item appears in CRITIC_REPORT.md under the Builder section

#### Scenario: Spec Gate Anchor Node Reduced Evaluation
    Given a feature file is an anchor node (arch_*.md, design_*.md, or policy_*.md)
    When the Critic tool runs the Spec Gate
    Then section_completeness checks for Purpose and Invariants instead of Overview/Requirements/Scenarios
    And scenario_classification and gherkin_quality report PASS with "N/A - anchor node"

#### Scenario: Implementation Gate Anchor Node Exempt
    Given a feature file is an anchor node (arch_*.md, design_*.md, or policy_*.md)
    When the Critic tool runs the Implementation Gate
    Then all checks report PASS with "N/A - anchor node exempt"
    And the overall implementation_gate status is PASS

### Manual Scenarios (Human Verification Required)

#### Scenario: CDD Dashboard Role Columns
    Given the CDD server is running
    And critic.json files exist for features with role_status computed
    When the User opens the web dashboard
    Then each feature entry shows Architect, Builder, and QA columns with role status badges
    And features without critic.json show "??" in all role columns

## 4. Implementation Notes
See [critic_tool.impl.md](critic_tool.impl.md) for implementation knowledge, builder decisions, and tribal knowledge.

## User Testing Discoveries

### [BUG] logic_drift.py writes LLM verdict cache inside tools/

- **Status:** OPEN
- **Discovered by:** Architect (Submodule Safety Audit, 2026-02-22)
- **File:** `tools/critic/logic_drift.py:22`
- **Description:** `CACHE_DIR` is set to `os.path.join(os.path.dirname(os.path.abspath(__file__)), '.cache')`, which resolves to `tools/critic/.cache/`. The `_write_cache()` function creates this directory and writes per-pair verdict JSON files into it. This violates submodule safety contract §2.12 (artifact write locations). In a submodule deployment `tools/` is a read-only framework directory; writes will pollute the tracked submodule or fail with permission errors.
- **Required fix:** Detect `PROJECT_ROOT` using the standard §2.11 pattern and set `CACHE_DIR` to `os.path.join(PROJECT_ROOT, '.purlin', 'cache', 'logic_drift_cache')`.
- **Severity:** CRITICAL (blocks submodule deployment when LLM drift checking is enabled)
