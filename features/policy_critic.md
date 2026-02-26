# Policy: Critic Coordination Engine

> Label: "Policy: Critic Coordination Engine"
> Category: "Coordination & Lifecycle"

## 1. Purpose
This policy defines the invariants and constraints governing the Critic -- the project coordination engine that validates specification-implementation quality AND generates role-specific action items for each agent. The Critic is the single source of truth for what each agent should work on next.

## 2. Invariants

### 2.1 Dual-Gate Principle
Every feature MUST be evaluable through two independent gates:

*   **Spec Gate (Pre-Implementation):** Validates that the feature specification itself is structurally complete, properly anchored to architectural policies, and contains well-formed Gherkin scenarios. This gate can run before any code exists.
*   **Implementation Gate (Post-Implementation):** Validates that the implementation aligns with the specification through traceability checks, policy adherence, builder decision audit, and (optionally) LLM-based logic drift detection.

Neither gate alone is sufficient. A feature that passes the Spec Gate but fails the Implementation Gate has a code problem. A feature that passes the Implementation Gate but fails the Spec Gate has a specification problem.

### 2.2 Traceability Mandate
Every automated Gherkin scenario in a feature file MUST be traceable to at least one automated test function. Traceability is established through keyword matching between scenario titles and test function names/bodies.

*   The traceability engine uses a keyword extraction and matching approach (2+ keyword threshold).
*   Manual scenarios are EXEMPT from traceability but are flagged if automated tests exist for them.
*   Explicit `traceability_overrides` in Implementation Notes allow manual mapping when keyword matching is insufficient.

### 2.3 Builder Decision Transparency
The Builder MUST classify every non-trivial implementation decision using structured tags in the `## Implementation Notes` section:

| Tag | Severity | Meaning |
|-----|----------|---------|
| `[CLARIFICATION]` | INFO | Interpreted ambiguous spec language. The spec was unclear; Builder chose a reasonable interpretation. |
| `[AUTONOMOUS]` | WARN | Spec was silent on this topic. Builder made a judgment call to fill the gap. |
| `[DEVIATION]` | HIGH | Intentionally diverged from what the spec says. Requires Architect acknowledgment. |
| `[DISCOVERY]` | HIGH | Found an unstated requirement during implementation. Requires Architect acknowledgment. |
| `[INFEASIBLE]` | CRITICAL | Feature cannot be implemented as specified. Builder has halted work. Requires Architect to revise the spec. |

**Constraint:** A feature with unacknowledged `[DEVIATION]` or `[DISCOVERY]` entries generates HIGH-priority Architect action items in the Critic report. A feature with `[INFEASIBLE]` generates a CRITICAL-priority Architect action item and the Builder skips the feature entirely.

**Scope:** The Builder Decision Audit MUST scan ALL files that contain a `## Implementation Notes` section — including anchor nodes (`arch_*.md`, `design_*.md`, `policy_*.md`). Builders may leave `[DISCOVERY]` or `[DEVIATION]` notes in anchor node Implementation Notes when they find anchor-level constraint gaps during implementation. These entries MUST be surfaced as HIGH-priority Architect action items just as they would be in regular feature files. Skipping anchor nodes in this scan is a Critic bug.

**Bracket-Tag Reservation:** The bracket-tag syntax (`[TAG]`) in Implementation Notes is reserved exclusively for active Builder Decisions. Pruned User Testing records written by QA during the PRUNED lifecycle step use unbracketed type labels (e.g., `DISCOVERY —`, `BUG —`). The Critic's Builder Decision Audit MAY use simple regex matching for bracket tags without context-awareness — the formatting convention enforces the separation.

### 2.4 User Testing Feedback Loop
Any agent may record findings in the `## User Testing Discoveries` section when they encounter bugs or unexpected behavior. The QA Agent owns lifecycle management (verification, resolution, pruning). Discovery types:

| Type | Meaning |
|------|---------|
| `[BUG]` | Behavior contradicts an existing scenario. |
| `[DISCOVERY]` | Behavior exists but no scenario covers it. |
| `[INTENT_DRIFT]` | Behavior matches the spec literally but misses the actual intent. |
| `[SPEC_DISPUTE]` | User disagrees with a scenario's expected behavior. The spec itself is wrong or undesirable. |

**Constraint:** Discoveries follow a lifecycle: `OPEN -> SPEC_UPDATED -> RESOLVED -> PRUNED`. OPEN discoveries generate role-specific action items in the Critic report. Default routing by type: BUGs route to Builder; DISCOVERYs, INTENT_DRIFTs, and SPEC_DISPUTEs route to Architect. **Override:** when a BUG discovery has `Action Required: Architect` set explicitly in its entry, the Critic routes it to the Architect instead. This override is used for bugs in instruction-file-driven agent behavior (startup protocol ordering, role compliance) that cannot be fixed in Builder-owned code. SPEC_UPDATED discoveries generate QA re-verification items only when the feature is in TESTING lifecycle state (i.e., the Builder has committed). Builder signaling comes from the feature lifecycle: an Architect spec update resets the feature to TODO lifecycle, which gives the Builder a TODO from the lifecycle state, not from discovery routing. This ensures the CDD dashboard shows at most one role with actionable TODO per discovery step. A SPEC_DISPUTE **suspends** the disputed scenario -- QA skips it until the Architect resolves the dispute.

**Status Detection Constraint:** The Critic MUST detect discovery statuses (OPEN, SPEC_UPDATED, RESOLVED) by parsing the structured `- **Status:** <VALUE>` field line of each entry — NOT by searching for status keywords in free-text prose. A status keyword appearing in a resolution note, scenario description, or other body text MUST NOT be counted as an active status.

**RESOLVED Pruning Signal:** When a feature has RESOLVED entries that have not yet been pruned, the Critic MUST generate a LOW-priority QA action item: `"Prune N RESOLVED discovery(ies) in <feature>"`. This ensures lingering RESOLVED entries are surfaced in the QA action items rather than remaining invisible between Critic cycles.

### 2.5 Policy Adherence
Anchor node files (`arch_*.md`, `design_*.md`, `policy_*.md`) MAY define `FORBIDDEN:` patterns -- literal strings or regex patterns that MUST NOT appear in the implementation code of features anchored to that anchor node.

*   The Critic tool scans implementation files for FORBIDDEN pattern violations.
*   Any violation produces a FAIL on the Implementation Gate.

### 2.6 Agent Startup Integration
Every agent (Architect, Builder, QA) MUST run the Critic at session start. The Critic report provides each agent with its role-specific action items, ensuring immediate alignment with project health and priorities.

### 2.7 Role-Specific Action Items
The Critic MUST generate imperative action items categorized by role (Architect, Builder, QA). Action items are derived from existing analysis gates (spec gate, implementation gate, user testing audit) and are prioritized by severity. Each action item identifies the target feature and the specific gap to address.

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
*   The section is **Architect-owned** (like the rest of the spec), not QA-owned.
*   Visual specification items are **exempt from Gherkin traceability**. They do not require automated scenarios or test functions.
*   The Critic MUST detect `## Visual Specification` sections and count visual checklist items per feature.
*   The Critic MUST generate separate QA action items for visual verification, distinct from functional scenario verification.
*   Regression scoping applies to visual specifications: a `cosmetic` scope skips visual QA, a `targeted` scope skips visual unless explicitly targeted, and a `full` scope includes visual verification.
*   The Critic MUST validate that `- **Reference:**` local file paths in Visual Specification sections resolve to existing files on disk. Missing files produce MEDIUM-priority Architect action items with category `missing_design_reference`.
*   The Critic MUST detect `- **Processed:**` dates in Visual Specification sections and compare them against local artifact file modification times. If the artifact file is newer than the processed date, the description is flagged as STALE, producing LOW-priority Architect action items with category `stale_design_description`.
*   The Critic MUST flag screens that have a `- **Reference:**` but no `- **Description:**` as HIGH-priority Architect action items with category `unprocessed_artifact`. These represent design artifacts that have been stored but not yet converted to structured markdown.

### 2.10 Targeted Scope Completeness
When a feature has `change_scope: "targeted:..."` and `builder: "TODO"`, the Critic MUST compare the scenario names in the targeted scope list against all scenario headings (`#### Scenario:` titles) in the feature file. If scenarios exist in the feature spec that are NOT listed in the targeted scope, and the feature has `builder: "TODO"`, the Critic MUST generate a MEDIUM-priority Architect action item identifying the unscoped scenarios.

*   **Purpose:** Targeted scopes created during phased delivery may become stale after the delivery plan is completed. This audit ensures unbuilt scenarios are never invisible.
*   **Routing:** Architect (scope decisions are an Architect/user concern). The Architect can then reset the scope to `full` or consciously re-scope.
*   **Visual items:** Visual spec items (`### Screen:` titles) that are not in the targeted scope are also flagged, using the same naming convention as Section 2.8 (`Visual:<screen name>`).
*   **Exemption:** Features with `change_scope: "full"`, `"cosmetic"`, or `"dependency-only"` are exempt from this check. Only `targeted:` scopes are audited.

### 2.11 CDD Decoupling
The Critic is an agent-facing coordination tool. CDD is a lightweight state display for human consumption. CDD shows what IS (per-role status). The Critic shows what SHOULD BE DONE (role-specific action items). CDD does NOT run the Critic. CDD reads the `role_status` object from on-disk `critic.json` files to display Architect, Builder, and QA columns on the dashboard and in the `/status.json` API. CDD does NOT compute role status itself; it consumes the Critic's pre-computed output.

## 3. Configuration

The following keys in `.purlin/config.json` govern Critic behavior:

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `critic_llm_model` | string | `claude-sonnet-4-20250514` | Model used for logic drift detection. |
| `critic_llm_enabled` | boolean | `false` | Whether the LLM-based logic drift engine is active. |
| `critic_gate_blocking` | boolean | `false` | **Deprecated (no-op).** Retained for backward compatibility. Status transitions are not gated by critic results. |

## 4. Output Contract
The Critic tool MUST produce:

*   **Per-feature:** `tests/<feature_name>/critic.json` with `spec_gate`, `implementation_gate`, `user_testing`, `action_items`, and `role_status` sections.
*   **Aggregate:** `CRITIC_REPORT.md` at the project root summarizing all features.

