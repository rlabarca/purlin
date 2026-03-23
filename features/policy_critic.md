# Policy: Critic Coordination Engine

> Label: "Policy: Critic Coordination Engine"
> Category: "Coordination & Lifecycle"

## 1. Purpose
This policy defines the invariants and constraints governing the Critic -- the project coordination engine that validates specification-implementation quality AND generates role-specific action items for each agent. The Critic is the single source of truth for what each agent should work on next.

This policy is a prerequisite for `policy_release.md` and all release-related features. Changes here cascade to 19+ dependent features.

## 2. Invariants

### 2.1 Dual-Gate Principle
Every feature MUST be evaluable through two independent gates:

*   **Spec Gate (Pre-Implementation):** Validates that the feature specification itself is structurally complete, properly anchored to architectural policies, and contains well-formed Gherkin scenarios. This gate can run before any code exists.
*   **Implementation Gate (Post-Implementation):** Validates that the implementation aligns with the specification through structural completeness (tests exist and pass), policy adherence, builder decision audit, and (optionally) LLM-based logic drift detection.

Neither gate alone is sufficient. A feature that passes the Spec Gate but fails the Implementation Gate has a code problem. A feature that passes the Implementation Gate but fails the Spec Gate has a specification problem.

### 2.2 Structural Test Requirement
The Implementation Gate validates that tests exist and pass. The Builder writes tests at whatever granularity is natural for the feature -- there is no requirement for 1:1 mapping between Gherkin scenarios and test functions. QA provides independent behavioral verification through regression testing and manual scenarios.

*   `tests.json` with `status: "PASS"` and `total > 0` is the hard gate (see Section 2.15).
*   The Builder is free to organize tests by functional area, integration boundary, or any other structure that proves the implementation works.
*   Scenario-to-test traceability is not enforced. The traceability engine remains in the codebase but is not run by the Critic.

### 2.3 Builder Decision Transparency
The Builder MUST classify every non-trivial implementation decision using structured tags in the `## Implementation Notes` section:

| Tag | Severity | Meaning |
|-----|----------|---------|
| `[CLARIFICATION]` | INFO | Interpreted ambiguous spec language. The spec was unclear; Builder chose a reasonable interpretation. |
| `[AUTONOMOUS]` | WARN | Spec was silent on this topic. Builder made a judgment call to fill the gap. |
| `[DEVIATION]` | HIGH | Intentionally diverged from what the spec says. Requires Architect acknowledgment. |
| `[DISCOVERY]` | HIGH | Found an unstated requirement during implementation. Requires Architect acknowledgment. |
| `[INFEASIBLE]` | CRITICAL | Feature cannot be implemented as specified. Builder has halted work. Requires Architect to revise the spec. |
| `[SPEC_PROPOSAL]` | HIGH | Proposes a new or modified spec/anchor node for Architect review. |

**Constraint:** A feature with unacknowledged `[DEVIATION]`, `[DISCOVERY]`, or `[SPEC_PROPOSAL]` entries generates HIGH-priority Architect action items in the Critic report. A feature with `[INFEASIBLE]` generates a CRITICAL-priority Architect action item and the Builder skips the feature entirely.

**Acknowledgment Detection:** A bracket-tagged entry is considered acknowledged when its line contains `Acknowledged` (case-insensitive). Architect workflow: (1) update spec or confirm no change needed, (2) append `Acknowledged.` to the tag line in the companion file. Acknowledged entries are excluded from FAIL status and action item generation. Summary reports include both total and acknowledged counts for transparency. `[SPEC_PROPOSAL]` entries follow the same acknowledgment convention as `[DEVIATION]` and `[DISCOVERY]`.

**Scope:** The Builder Decision Audit MUST scan ALL files that contain a `## Implementation Notes` section — including anchor nodes (`arch_*.md`, `design_*.md`, `policy_*.md`). Builders may leave `[DISCOVERY]` or `[DEVIATION]` notes in anchor node Implementation Notes when they find anchor-level constraint gaps during implementation. These entries MUST be surfaced as HIGH-priority Architect action items just as they would be in regular feature files. Skipping anchor nodes in this scan is a Critic bug.

**Bracket-Tag Reservation:** The bracket-tag syntax (`[TAG]`) in Implementation Notes is reserved for Builder Decisions (active and acknowledged). The distinction between active and acknowledged is made by the acknowledgment marker, not by the tag format. Pruned User Testing records written by QA during the PRUNED lifecycle step use unbracketed type labels (e.g., `DISCOVERY —`, `BUG —`). The Critic's Builder Decision Audit MAY use simple regex matching for bracket tags without context-awareness — the formatting convention enforces the separation.

### 2.4 User Testing Feedback Loop
Any agent may record findings in discovery sidecar files (`features/<name>.discoveries.md`) when they encounter bugs or unexpected behavior. The QA Agent owns lifecycle management (verification, resolution, pruning). Discovery types:

| Type | Meaning |
|------|---------|
| `[BUG]` | Behavior contradicts an existing scenario. |
| `[DISCOVERY]` | Behavior exists but no scenario covers it. |
| `[INTENT_DRIFT]` | Behavior matches the spec literally but misses the actual intent. |
| `[SPEC_DISPUTE]` | User disagrees with a scenario's expected behavior. The spec itself is wrong or undesirable. |

**Constraint:** Discoveries follow a lifecycle: `OPEN -> SPEC_UPDATED -> RESOLVED -> PRUNED`. Discoveries are stored in sidecar files (`features/<name>.discoveries.md`), NOT in the feature file itself. This prevents discovery edits from triggering lifecycle resets. OPEN discoveries generate role-specific action items in the Critic report. Default routing by type: BUGs route to Builder; DISCOVERYs and INTENT_DRIFTs route to Architect. SPEC_DISPUTEs use Owner-based routing: SPEC_DISPUTEs on features with `> Owner: PM` or referencing Visual Specification screens route to PM; all other SPEC_DISPUTEs route to Architect. **Override:** when a SPEC_DISPUTE has `Action Required: PM` set explicitly (typically by Architect triage), the Critic routes it to PM regardless of Owner tag. Conversely, `Action Required: Architect` forces Architect routing regardless of Owner tag. This override follows the same pattern as BUG routing overrides. When a BUG discovery has an explicit `Action Required: <role>` field naming any role (Architect, QA, etc.), the Critic routes it to the specified role instead of the default Builder routing. This override is used for bugs in instruction-file-driven agent behavior (Action Required: Architect) or stale test scenario assertions that should be fixed by QA (Action Required: QA). SPEC_UPDATED discoveries generate QA re-verification items only when the feature is in TESTING lifecycle state (i.e., the Builder has committed). Builder signaling comes from the feature lifecycle: an Architect spec update resets the feature to TODO lifecycle, which gives the Builder a TODO from the lifecycle state, not from discovery routing. This ensures the CDD dashboard shows at most one role with actionable TODO per discovery step. A SPEC_DISPUTE **suspends** the disputed scenario -- QA skips it until the PM or Architect resolves the dispute.

**Status Detection Constraint:** The Critic MUST detect discovery statuses (OPEN, SPEC_UPDATED, RESOLVED) by parsing the structured `- **Status:** <VALUE>` field line of each entry in the sidecar file — NOT by searching for status keywords in free-text prose. A status keyword appearing in a resolution note, scenario description, or other body text MUST NOT be counted as an active status.

**RESOLVED Pruning Signal:** When a feature has RESOLVED entries that have not yet been pruned, the Critic MUST generate a LOW-priority QA action item: `"Prune N RESOLVED discovery(ies) in <feature>"`. This ensures lingering RESOLVED entries are surfaced in the QA action items rather than remaining invisible between Critic cycles.

### 2.5 Policy Adherence
Anchor node files (`arch_*.md`, `design_*.md`, `policy_*.md`) MAY define `FORBIDDEN:` patterns -- literal strings or regex patterns that MUST NOT appear in the implementation code of features anchored to that anchor node.

*   The Critic tool scans implementation files for FORBIDDEN pattern violations.
*   Any violation produces a FAIL on the Implementation Gate.

### 2.6 Agent Startup Integration
Every agent (Architect, Builder, QA, PM) MUST run the Critic at session start. The Critic report provides each agent with its role-specific action items, ensuring immediate alignment with project health and priorities.

### 2.7 Role-Specific Action Items
The Critic MUST generate imperative action items categorized by role (Architect, Builder, QA, PM). Action items are derived from existing analysis gates (spec gate, implementation gate, user testing audit) and are prioritized by severity. Each action item identifies the target feature and the specific gap to address.

### 2.8 Regression Scoping
The Builder declares the **impact scope** of each change at status-commit time using a `[Scope: ...]` trailer. The Critic reads this scope, cross-validates it against the dependency graph, and generates **scoped QA action items** instead of blanket "test everything" items.

**Scope Types:**

| Scope | Meaning | QA Action |
|-------|---------|-----------|
| `full` | Behavioral change, new scenarios, API change | Test all manual scenarios |
| `targeted:<exact names>` | Only specific scenarios/screens affected | Test only named items (see naming contract below) |
| `cosmetic` | Non-functional (formatting, logging, internal refactor) | Skip QA entirely |
| `dependency-only` | Change propagated by a prerequisite update | Test scenarios touching the changed dependency surface |

**Naming Contract for `targeted:` Scopes:**
*   Values MUST be a comma-separated list of exact verification item names from the feature spec. No free-form labels.
*   **Manual Scenarios:** Use the exact title from `#### Scenario: <Name>` (e.g., `targeted:Web Dashboard Auto-Refresh`).
*   **Visual Spec Screens:** Use the prefix `Visual:` followed by the exact screen name from `### Screen: <Name>` (e.g., `targeted:Visual:CDD Web Dashboard`).
*   **Mixed:** Comma-separate manual and visual targets (e.g., `targeted:Web Dashboard Auto-Refresh,Visual:CDD Web Dashboard`).
*   The Critic MUST validate that every name in a `targeted:` scope matches an existing `#### Scenario:` title or `### Screen:` title in the feature spec. Unresolvable names produce a WARNING in the Critic report.

**Cosmetic First-Pass Guard:** `cosmetic` scope MUST only suppress QA verification when the feature's previous on-disk `tests/<feature>/critic.json` shows `role_status.qa == "CLEAN"`. When no prior clean pass exists (`qa` was `TODO`, `N/A`, `FAIL`, or the file is absent), the Critic MUST escalate the declared scope to `full` and append a `cross_validation_warning`: `"Cosmetic scope declared but no prior clean QA pass exists for this feature. Escalating to full verification."` This warning is **informational only** and MUST NOT generate a Builder action item. It is preserved in `regression_scope.cross_validation_warnings` for audit purposes only.

**Constraints:**
*   Default when omitted: `full` (backward-compatible, safe).
*   The Critic MUST cross-validate scope claims: if a `cosmetic` scope commit modifies files referenced by manual scenarios, the Critic emits a WARNING in the report.
*   The Critic MUST compute a `regression_set` for each TESTING feature: the filtered list of manual scenarios (and visual checklist items) that QA should verify based on the declared scope.

### 2.9 Visual Specification Convention
Feature files MAY contain a `## Visual Specification` section for features with visual/UI components. This section provides checklist-based visual acceptance criteria with optional design asset references (Figma URLs, PDFs, images).

**Constraints:**
*   The section is **optional** -- only present when the feature has a visual/UI component.
*   The section is **spec-owned** (Architect-authored, or PM-authored when a PM agent is active), not QA-owned.
*   Visual specification items are **exempt from Gherkin traceability**. They do not require automated scenarios or test functions.
*   The Critic MUST detect `## Visual Specification` sections and count visual checklist items per feature.
*   The Critic MUST generate separate QA action items for visual verification, distinct from functional scenario verification.
*   Regression scoping applies to visual specifications: a `cosmetic` scope skips visual QA, a `targeted` scope skips visual unless explicitly targeted, and a `full` scope includes visual verification.
*   The Critic MUST validate that `- **Reference:**` local file paths in Visual Specification sections resolve to existing files on disk. Missing files produce MEDIUM-priority PM action items with category `missing_design_reference`.
*   The Critic MUST detect `- **Processed:**` dates in Visual Specification sections and compare them against local artifact file modification times. If the artifact file is newer than the processed date, the Token Map is flagged as STALE, producing LOW-priority PM action items with category `stale_token_map`.
*   The Critic MUST flag screens that have a `- **Reference:**` but no `- **Token Map:**` as HIGH-priority PM action items with category `unprocessed_artifact`. These represent design artifacts that have been stored but not yet had their tokens mapped to the project's token system.
*   The Critic MUST check for `brief.json` at `features/design/<feature_stem>/brief.json` for features with Figma references. If `figma_last_modified` in the brief is newer than the spec's `- **Processed:**` date, produce LOW-priority PM action items with category `stale_token_map`.
*   **Figma Dev Status Advisory Gate:** Features in Builder TODO state with `> Figma Status: Design` in their blockquote metadata generate a LOW-priority PM action item with category `figma_design_not_ready`: "Figma design not marked Ready for Dev". This is advisory, not blocking -- the Critic does not prevent the Builder from working on the feature.

### 2.10 Targeted Scope Completeness
When a feature has `change_scope: "targeted:..."` and `builder: "DONE"`, the Critic MUST compare the scenario names in the targeted scope list against all scenario headings (`#### Scenario:` titles) in the feature file. If scenarios exist in the feature spec that are NOT listed in the targeted scope, the Critic MUST generate a MEDIUM-priority Architect action item identifying the unscoped scenarios.

*   **Purpose:** Targeted scopes created during phased delivery may become stale after the delivery plan is completed. This audit catches cases where the Builder has marked work as done but the targeted scope does not cover all scenarios -- indicating either a stale scope or incomplete work.
*   **Routing:** Architect (scope decisions are an Architect/user concern). The Architect can then reset the scope to `full` or consciously re-scope.
*   **Visual items:** Visual spec items (`### Screen:` titles) that are not in the targeted scope are also flagged, using the same naming convention as Section 2.8 (`Visual:<screen name>`).
*   **Exemption:** Features with `change_scope: "full"`, `"cosmetic"`, or `"dependency-only"` are exempt from this check. Only `targeted:` scopes are audited.
*   **Suppression when builder is TODO:** When `builder: "TODO"`, the targeted scope completeness check is suppressed entirely. The Builder already has a HIGH-priority action item to implement the feature, which inherently covers all scenarios in the spec. Generating an additional Architect warning for unscoped scenarios is redundant noise.

### 2.11 Fixture Tag Validation
When a feature spec declares fixture tags (via a `### 2.x Web Test Fixture Tags` or `### 2.x Integration Test Fixture Tags` section, or via `> Test Fixtures:` metadata with Given steps referencing tags), the Critic MUST validate that the declared tags exist in the fixture repo. Missing tags produce a MEDIUM-priority Builder action item.

*   **Purpose:** Prevents features from being marked complete when their declared test infrastructure does not exist. Without this check, specs can declare fixture tags that remain aspirational indefinitely.
*   **Mechanism:** The Critic parses fixture tag sections from feature specs and cross-references against `fixture list` output. Tags that are declared but missing are flagged.
*   **Gate impact:** Missing fixture tags do not FAIL the Implementation Gate (they are MEDIUM, not CRITICAL). They generate Builder action items that block `builder: DONE` status until resolved.
*   **Repo Resolution (Convention Over Configuration):** The Critic resolves the fixture repo using a three-tier lookup: (1) per-feature `> Test Fixtures:` metadata, (2) project-level `fixture_repo_url` in `.purlin/config.json`, (3) convention path `.purlin/runtime/fixture-repo`. The first path that resolves to an accessible git repo wins. Relative paths are resolved against `PURLIN_PROJECT_ROOT`. Most projects use the convention path exclusively — no configuration needed.
*   **Fixture repo not found:** When a feature declares fixture tags but no fixture repo is accessible (none of the three resolution tiers point to a valid repo), the Critic MUST generate a MEDIUM-priority Builder action item with category `fixture_repo_unavailable`: `"Fixture repo not found for <name> — run the setup script to create it at .purlin/runtime/fixture-repo"`. This is a Builder item because creating fixture repos via setup scripts is an implementation task.

### 2.12 Diff-Aware Lifecycle Reset Detection
When a feature resets to TODO lifecycle state (spec modified after last status commit), the Critic MUST perform a **scenario diff** to determine what changed. The Critic compares the current set of automated scenario titles against the set that existed at the time of the last status commit (extracted from git history of the feature file).

*   **New scenarios:** Scenario titles present in the current spec but absent from the last-committed version. These represent NEW requirements that need NEW tests and NEW implementation code. Re-tagging without implementing them is incorrect.
*   **Modified scenarios:** Scenario titles that exist in both versions but whose Given/When/Then content has changed. These may require test updates.
*   **Removed scenarios:** Scenario titles present in the last-committed version but absent from the current spec. These may require test cleanup.
*   **Action item enrichment:** The lifecycle_reset Builder action item MUST include the scenario diff summary. Instead of the generic `"Review and implement spec changes for <feature>"`, the description MUST list new, modified, and removed scenarios explicitly: `"Implement spec changes for <feature>: N new scenario(s) [<titles>], M modified, K removed"`.
*   **Requirements section change detection:** When the scenario diff shows no changes (`has_diff: False`) but the feature was still reset to TODO (spec file was modified), the Critic MUST detect which Requirements subsections changed by comparing section headings and content between the current file and the last-status-commit version. The action item description MUST include the changed section numbers: `"Implement spec changes for <feature>: requirements sections modified [2.2, 2.5]"`. If the Visual Specification section changed, append `", visual spec updated"`. This ensures the Builder knows where to look when scenarios are unchanged but behavioral requirements have been updated.
*   **Priority:** HIGH (unchanged from current lifecycle_reset behavior).
*   **New scenario signal:** When new scenarios are detected, the action item description explicitly lists them so the Builder knows which behaviors need new test coverage. No keyword-matching or traceability cross-check is performed -- the Builder determines test organization.
*   **Metadata Exemption:** Blockquote metadata lines (`> Label:`, `> Category:`, `> Prerequisite:`, `> Owner:`, `> Web Test:`, `> Web Start:`, `> Test Fixtures:`, `> Figma Status:`) are stripped from the content hash used for lifecycle comparison. Edits to these lines do not trigger lifecycle resets. This follows the same pattern as the Discoveries section exemption -- non-behavioral coordination data does not invalidate implementation status.

### 2.13 CDD Decoupling
The Critic is an agent-facing coordination tool. CDD is a lightweight state display for human consumption. CDD shows what IS (per-role status). The Critic shows what SHOULD BE DONE (role-specific action items). CDD does NOT run the Critic. CDD reads the `role_status` object from on-disk `critic.json` files to display Architect, Builder, QA, and PM columns on the dashboard and in the `/status.json` API. CDD does NOT compute role status itself; it consumes the Critic's pre-computed output.

### 2.15 Structural Completeness Integrity
The `structural_completeness` check in the Implementation Gate validates that `tests/<feature>/tests.json` represents genuine test execution, not hand-written stubs. The following invariants MUST hold:

1.  **Minimum Test Count Rule:** A `tests.json` file with `status: "PASS"` MUST have `total > 0`. A PASS with zero tests is semantically invalid — it means no code was exercised. The Critic MUST treat `total: 0` (or missing `total` field) combined with `status: "PASS"` as a FAIL with detail `"PASS with zero tests is invalid"`.

2.  **Test File Existence Rule:** When `tests.json` reports `status: "PASS"`, at least one test file MUST be discoverable. Discovery uses a three-tier lookup (first match wins): (a) any file in `tests/<feature>/` whose name starts with `test` (excluding `.pyc`), (b) a path declared in a `test_file` (string) field within `tests.json`, (c) paths declared in a `test_files` (array of strings) field within `tests.json`. Declared paths are checked for existence on disk. A PASS with no discoverable test files is treated as FAIL with detail `"No test files found backing tests.json"`. Note: the discovery uses no hardcoded extension whitelist — consumer projects may use any test file format (`.py`, `.sh`, `.jsx`, `.ts`, `.go`, etc.).

3.  **Internal Consistency Rule:** If `tests.json` contains `failures` or `failed` fields with numeric values > 0, `status` MUST NOT be `"PASS"`. The Critic MUST treat this contradiction as FAIL with detail `"Internal inconsistency: status PASS with failures > 0"`.

4.  **Schema Minimum Fields:** `tests.json` MUST contain at minimum: `status` (string), `passed` (int), `failed` (int), `total` (int). A file missing any of these required fields is treated as FAIL with detail `"Missing required fields: <list>"`. The bare `{"status": "PASS"}` format is no longer valid.

**All-Manual Feature Exemption:** Features with zero automated scenarios are exempt from structural completeness checks entirely. When the Critic detects that a feature has no automated scenarios (only manual scenarios or no scenarios at all), `structural_completeness` MUST report PASS with detail `"N/A - no automated scenarios"`. No `tests.json` file is required for these features. This exemption prevents false FAILs on legitimately all-manual features (e.g., features that are purely process-driven or hardware-verified).

**Constraint:** These invariants apply equally to the `structural_completeness` check in `critic.json` and to the Builder's `DONE` status computation. A feature cannot be Builder `DONE` if its `tests.json` violates any of these rules. The all-manual exemption takes precedence — a feature with zero automated scenarios can be Builder `DONE` without `tests.json`.

## 3. Configuration

The following keys in `.purlin/config.json` govern Critic behavior:

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `critic_llm_model` | string | `claude-sonnet-4-20250514` | Model used for logic drift detection. |
| `critic_llm_enabled` | boolean | `false` | Whether the LLM-based logic drift engine is active. |
| `critic_gate_blocking` | boolean | `false` | **Deprecated (no-op).** Retained for backward compatibility. Status transitions are not gated by critic results. |

### 2.14 Verification Effort Classification
The Critic MUST compute a `verification_effort` block for each feature, classifying pending verification work into Builder-owned auto-verified categories and QA-owned manual categories. This block is included in the per-feature `critic.json` output alongside `role_status`.

**Taxonomy:**

| Category | Key | Owner | Condition |
|----------|-----|-------|-----------|
| TestOnly | `test_only` | **Builder** | Feature has only Unit Tests, tests pass, no QA scenarios. Visual spec items are Builder-verified (via `/pl-web-test` or manual inspection) and do not affect this classification |
| Skip | `skip` | **Builder** | Regression scope is `cosmetic` (not escalated) |
| Auto | `auto` | **QA** | QA Scenarios with `@auto` tag |
| Manual | `manual` | **QA** | QA Scenarios without `@auto` tag |

Builder-owned categories (TestOnly, Skip) are computed for status tracking but do NOT generate QA action items. Builder-owned items route to Builder action items. When the Builder marks `[Complete]` with zero QA scenarios, `qa: "N/A"`.

**`@auto` and `@manual` Tag Detection:** The Critic parses `@auto` and `@manual` as suffixes on `#### Scenario:` headings under `### QA Scenarios`. Three classification states:

*   `@auto` — Scenario has been automated by QA. Regression JSON exists. Harness runner executes it.
*   `@manual` — Scenario requires human judgment. QA classified it as non-automatable.
*   Untagged — Scenario has not yet been classified by QA. Treated as `manual` for effort computation (conservative), but QA will attempt automation on first encounter.

**Classification precedence for effort computation:** `@manual` > `@auto` > untagged (counts as manual). If both tags appear on the same scenario (error), `@manual` wins.

Derived fields: `summary` (human-readable string). Summary format: `"N manual"` when manual items exist, `"N auto"` when only auto items exist. When a feature is `[Complete]` via Builder (no `[Verified]`), summary = `"builder-verified"`.

**Backward compatibility:** The Critic parser MUST accept both `> AFT Web:` and `> Web Test:` metadata for web test detection during the transition period.

**Section Heading Migration:** The Critic MUST accept both old (`### Automated Scenarios`, `### Manual Scenarios (Human Verification Required)`) and new (`### Unit Tests`, `### QA Scenarios`) section headings. Both are parsed identically. Agents rename headings to the new format when touching a spec.

The block is only meaningful for TESTING features (qa: TODO or AUTO). Non-TESTING features report zeroed counts with `summary` of `"no QA items"` or `"awaiting builder"` as appropriate.

See `features/qa_verification_effort.md` for the full classification rules, output schema, and scenarios.

### 2.16 QA Verification Integrity

When a feature has manual scenarios, QA status MUST NOT reach CLEAN without evidence that QA verification occurred. The system relies on the TESTING lifecycle phase as the verification signal -- a feature must pass through TESTING before reaching COMPLETE for QA to be considered verified.

**The Invariant:** If a feature has one or more manual scenarios AND `lifecycle_state == 'complete'` AND no TESTING-phase commit (`[Ready for \w+ features/<name>.md]`) exists in the feature's git history **after the most recent lifecycle reset to TODO**, the Critic MUST set `qa_status = 'TODO'`. The feature bypassed QA verification.

Additionally, even when a valid TESTING-phase commit exists, the most recent post-reset `[Complete]` commit MUST contain a `[Verified]` tag. A `[Complete]` commit without `[Verified]` on a feature with manual scenarios indicates the Builder completed the feature without QA executing the verification workflow.

A lifecycle reset to TODO occurs when the feature spec is modified after the last `[Complete]` or `[Testing]` status commit. The most recent reset point is the timestamp of the commit that last modified the feature spec file and caused the lifecycle to return to TODO. A TESTING-phase commit that predates this reset is stale and MUST NOT satisfy the invariant.

**Abbreviated Format Support:** The Critic MUST recognize both canonical and abbreviated status commit formats when searching for TESTING-phase and `[Complete]` commits (consistent with `cdd_status_monitor.md` Section 2.1 Status Commit Discovery Patterns):
*   **Canonical:** `[Ready for \w+ features/<name>.md]`, `[Complete features/<name>.md]` — feature identified from the embedded path.
*   **Abbreviated:** `[Ready for Verification]`, `[Ready for Testing]`, `[Complete]` without an inline file path — feature resolved from the conventional commit scope (`<type>(<scope>):` → `features/<scope>.md`). Only applies when the resolved file exists on disk.
*   **`[Verified]` detection:** A `[Complete]` commit (canonical or abbreviated) contains `[Verified]` when the tag appears anywhere in the commit message. The detection is format-independent.

**Detection:** When computing `qa_status` and `lifecycle_state == 'complete'`, the Critic MUST:
1.  Parse the feature's scenarios and count manual scenarios.
2.  If manual scenarios > 0, determine the most recent lifecycle reset point: the timestamp of the latest spec-modifying commit that post-dates the previous `[Complete]` or `[Testing]` status commit. If no status commit exists, the reset point is epoch zero (all TESTING-phase commits qualify).
3.  Search git history for a TESTING-phase commit matching either the canonical pattern `[Ready for \w+ features/<name>.md]` or the abbreviated pattern (`[Ready for Verification]` / `[Ready for Testing]` with conventional commit scope resolving to `features/<name>.md`) whose timestamp is **at or after** the reset point determined in step 2.
4.  If no such post-reset TESTING-phase commit exists, set `qa_status = 'TODO'`.
5.  If a post-reset TESTING-phase commit IS found, additionally check that the most recent post-reset `[Complete]` commit for this feature (canonical or abbreviated) contains the `[Verified]` tag.
6.  If the `[Complete]` commit lacks `[Verified]`, set `qa_status = 'TODO'`.

**Action Item Generation:** When this invariant triggers, the Critic MUST generate a HIGH-priority QA action item with category `bypassed_qa_verification`. The message depends on the sub-case:
*   No TESTING commit: `"Feature <name> has N manual scenario(s) that bypassed QA verification -- no TESTING-phase commit found"`
*   Missing [Verified]: `"Feature <name> has N manual scenario(s) but [Complete] lacks [Verified] tag -- run /pl-complete to verify"`

The `[Verified]` tag is a boolean signal. Its presence in the most recent `[Complete]` commit message for a feature indicates QA verification occurred. The tag has no timestamp semantics -- only presence/absence matters.

**`[Verified]` Tag Contract:** The `[Verified]` tag is a bracketed trailer appended to the `[Complete]` status commit message, produced exclusively by `/pl-complete` (QA-only). Canonical format: `status(<scope>): [Complete features/<name>.md] [Verified]`. Abbreviated format: `status(<scope>): [Complete] [Verified]`. Both formats are valid; the Critic detects `[Verified]` by presence in the commit message, not by position relative to the file path. The Builder MUST NOT include `[Verified]` in `[Complete]` commits -- Builder completions apply only to features with zero manual scenarios.

**Verification Effort Consistency:** The `verification_effort` computation (Section 2.14) MUST also recognize this case. When a COMPLETE feature has `qa_status = 'TODO'` due to bypassed verification, `verification_effort` MUST compute the full classification (interactive/visual/hardware counts) rather than returning zeroed values. The lifecycle gating in `verification_effort` MUST treat "COMPLETE with bypassed QA" equivalently to TESTING for classification purposes.

**Precedence:** This check slots into the existing QA precedence chain as: `FAIL > DISPUTED > TODO (SPEC_UPDATED) > TODO (TESTING with manual) > TODO (bypassed verification: no TESTING commit) > TODO (bypassed verification: missing [Verified]) > AUTO > CLEAN > N/A`. The existing FAIL and DISPUTED conditions take priority -- a feature with OPEN BUGs or SPEC_DISPUTEs is already surfaced as FAIL/DISPUTED regardless of verification history.

**Rationale:** The workflow (HOW_WE_WORK_BASE Section 3, step 4) mandates that features with manual scenarios are completed by the QA Agent after clean verification, not by the Builder. When a Builder commits `[Complete]` on such a feature, the TESTING phase is skipped and QA verification never occurs. Without this invariant, the Critic silently marks QA as CLEAN based solely on passing automated tests, masking untested manual scenarios.

### 2.17 Regression Guidance Detection

Feature files MAY contain a `## Regression Guidance` section with bullet points describing behaviors that are regression-worthy. PM or Architect adds these hints during spec authoring to signal which behaviors deserve independent regression coverage by QA.

**Detection and Action Item Generation:**

*   The Critic MUST detect `## Regression Guidance` sections in feature files.
*   When a feature has a `## Regression Guidance` section AND `builder: "DONE"`, the Critic MUST generate **MEDIUM**-priority QA action items with category `regression_guidance_pending`: `"Regression guidance available for <name> -- review hints and create regression harness"`.
*   The Builder ignores this section entirely -- it is not a requirement, not an automated scenario, and does not affect the Implementation Gate.
*   Once QA creates regression coverage for the hinted behaviors (scripts in `tests/qa/`), QA can mark the item resolved by adding a `> Regression Coverage: Yes` metadata line to the feature file or by the natural lifecycle of QA verification.

**Exemptions:**

*   Features where `builder` status is `"TODO"` are exempt (implementation not yet complete -- regression hints are premature).
*   The section is optional. Features without it generate no action items.

## 4. Output Contract
The Critic tool MUST produce:

*   **Per-feature:** `tests/<feature_name>/critic.json` with `spec_gate`, `implementation_gate`, `user_testing`, `action_items`, `role_status`, and `verification_effort` sections.
*   **Aggregate:** `CRITIC_REPORT.md` at the project root summarizing all features.

