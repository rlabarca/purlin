# Phased Delivery Protocol

> This file is loaded on-demand by `/pl-delivery-plan`, `/pl-build`, and `/pl-verify`
> commands when a delivery plan exists or phased delivery is being considered.

## 10.1 Purpose
When the Architect introduces large-scale changes (multiple new feature files, major revisions across existing features), the Builder may need to split work across multiple sessions to ensure quality and enable incremental verification. The Phased Delivery Protocol provides a persistent coordination artifact that lets the Builder organize work into **testable blocks** -- groups of scenarios that logically belong together for verification -- and enable **parallel delivery** where independent blocks can be worked on by different agents simultaneously. The user orchestrates the cycle: Builder (Phase 1) -> QA (verify Phase 1) -> Builder (fix bugs + Phase 2) -> QA -> ... until complete.

## 10.2 The Delivery Plan Artifact
*   **Path:** `.purlin/delivery_plan.md`
*   **Created by:** Builder, when user approves phased delivery.
*   **Committed to git:** Yes -- lives outside `.purlin/cache/` (which is gitignored) because it is a coordination artifact read by all agents across sessions, not a regenerable cache file.
*   **Deleted by:** Builder, when the final phase completes.
*   **Format:** The plan contains a summary, numbered phases (each with status, feature list, completion commit, and QA bugs addressed), and a plan amendments section. Phase statuses are PENDING, IN_PROGRESS, or COMPLETE. Exactly one phase may be IN_PROGRESS at a time. COMPLETE phases are immutable historical record.
*   **Intra-Feature Phasing:** A feature MAY appear in multiple phases. Targeted delivery within a feature uses the existing `[Scope: targeted:...]` mechanism. No new scope types are needed.

## 10.3 Cross-Session Resumption
When `auto_start` is `false` (default), each phase MUST be a separate Builder session. The Builder halts after completing a phase and waits for the user to relaunch.

When `auto_start` is `true`, the Builder auto-advances to the next PENDING phase within the same session.

When execution groups are in use, groups are the session boundaries (not individual phases). With `auto_start: false`, the Builder halts at group boundaries. With `auto_start: true`, the Builder auto-advances to the next group. Multiple phases within a group are processed in a single session, with independent features built in parallel.

When a delivery plan exists at session start, the Builder resumes from the next PENDING phase. QA bugs recorded during prior phases are addressed first, before new phase work begins. If the IN_PROGRESS phase was interrupted mid-session, the Builder resumes that phase, skipping features already in TESTING state.

**Scope Reset on Plan Completion:** When the Builder completes the final phase and deletes the delivery plan, the Builder MUST reset the `change_scope` to `full` for every feature that participated in the plan and still has `builder: "TODO"` status. Targeted scopes are artifacts of the phased delivery -- once the plan is gone, any remaining unbuilt work must be visible under a full scope. This prevents scenarios from becoming invisible to future Builder sessions after the delivery plan context is deleted.

## 10.4 QA Interaction
The QA Agent MUST check for a delivery plan at `.purlin/delivery_plan.md` during startup. If the plan exists, QA classifies each TESTING feature as either "fully delivered" (appears only in COMPLETE phases) or "more work coming" (appears in a PENDING phase). QA MUST NOT mark a feature as `[Complete]` if it appears in any PENDING phase of the delivery plan, even if all currently-delivered scenarios pass. QA informs the user which features are phase-gated.

When execution groups complete, QA can verify all phases in the completed group simultaneously. If a group partially completes (one phase done, another stuck), QA can verify the completed phase immediately while the stuck phase continues in the next Builder session.

## 10.5 Phasing is Optional
Phased delivery is never automatic unless the user has opted into autonomous execution. The Builder proposes phasing based on scope assessment, and the user decides whether to accept phasing, modify the phase breakdown, or proceed with a single-session delivery. At any approval checkpoint, the user may collapse remaining phases, re-split, or abandon phasing entirely.

**Exceptions:**
*   **`auto_start: true`:** When the Builder's `auto_start` config flag is enabled and the scope assessment heuristics are met, the Builder creates the delivery plan automatically and begins Phase 1. The user has delegated approval by enabling `auto_start`.

## 10.6 Architect Awareness
If the Architect modifies feature specs while a delivery plan is active, the Builder detects the mismatch on resume and proposes a plan amendment. Minor changes (added scenarios, clarified requirements) are auto-updated. Major changes (new features, removed phases, restructured dependencies) require user approval before continuing.

## 10.7 CDD Dashboard Integration
When a delivery plan exists, the CDD Dashboard's ACTIVE section heading displays phase progress as an inline annotation: `ACTIVE (<count>) [<completed>/<total> DONE | <in_progress> RUNNING]`. The `/status.json` API and CLI tool include an optional `delivery_phase` field with aggregate status counts and a per-phase array. When all phases are COMPLETE/REMOVED or no delivery plan exists, the phase annotation and API field are omitted.

## 10.8 Phase Sizing Guidance

Phase sizing is driven by **testability**, **parallelism**, and **interaction density**, not by hard caps. The Builder uses judgment to create phases that:

*   **Group related scenarios** -- features or scenario subsets that logically belong together for verification. A phase should produce a testable state where QA can meaningfully verify the delivered work. Features that share data models, APIs, or UI components benefit from being in the same phase -- B2 catches their cross-feature regressions.
*   **Enable parallel delivery** -- when independent feature groups have no dependencies on each other, they can be placed in separate phases for concurrent agent work.
*   **Keep large features focused** -- a single feature with many unimplemented scenarios (5+) benefits from a dedicated phase to keep the Builder focused and the QA verification cycle tight.
*   **Interaction grouping** -- features that interact should be grouped together: features sharing data models or APIs in the same phase (B2 catches contract breaks), features sharing UI components or layout in the same phase (B2 web-verify catches visual regressions). Features with no interaction can be in separate phases (B2 will not find cross-phase regressions anyway).

There are no hard per-phase feature caps. The Builder balances phase size against session productivity and verification granularity.

## 10.9 Context Budget Awareness

The Builder SHOULD consider context consumption when sizing phases. Different work items consume context at different rates:

*   **Large feature specs** with many scenarios require significant context to read and internalize.
*   **Multi-file implementations** that touch many source files consume context for reading existing code, making changes, and verifying consistency.
*   **Extensive test suites** consume context for writing, running, and debugging tests.

When the cumulative scope of a phase (specs to read + files to modify + tests to run) is large, prefer splitting into smaller phases. The goal is to complete each phase with sufficient context remaining for quality verification.

This factor is **subordinate** to testability (Section 10.8) and dependency order. A phase must still produce a testable state and respect dependency constraints, even if that means a larger context footprint. Context budget is a tiebreaker when multiple valid phase breakdowns exist.

No hard token counting is required. This is qualitative judgment based on scope signals: number of features, spec length, estimated file count, and test complexity.

B2 (Test Sub-Phase) re-runs all tests and web tests for the phase. B3 (Fix Sub-Phase) may iterate multiple times. Budget approximately 20-30% additional context beyond B1 implementation for the B2/B3 cycle. When a phase contains features with known interaction complexity, budget more generously.

## 10.10 Phase Internal Structure (B1/B2/B3)

Each delivery phase has an internal three-step structure that separates implementation from verification.

### B1 (Build Sub-Phase)

Existing per-feature implementation loop (Steps 0-3 in BUILDER_BASE). Each feature is implemented and locally tested including web tests. No status tags yet. Visual design read priority: Token Map -> brief.json -> Figma (last resort) for implementation decisions. Web test verification (`/pl-web-test`) uses Figma MCP for three-source comparison when available, regardless of this priority. The Builder iterates per-feature until `/pl-web-test` passes. Fast iteration.

### B2 (Test Sub-Phase)

After B1 completes for all features in the phase, re-run the full test suite AND all applicable web tests for every feature in the phase. This catches cross-feature regressions within the phase. Record which features/tests failed and which passed.

**B2 Visual Design Verification:** During B2, the Builder's visual verification priority INVERTS from B1. Implementation is complete -- accuracy matters more than iteration speed. For features with a `## Visual Specification` section:

1. **Reference images** (in `features/design/`): During B1, these are audit references, not Builder inputs. During B2, they become verification inputs. The Builder takes a Playwright screenshot and compares it against the reference image. This is fast (local, multimodal) and catches obvious visual drift.
2. **Figma MCP** (if available): During B1, Figma is last resort. During B2, it is the authoritative design source. The Builder uses the same three-source triangulated verification that `/pl-web-test` already supports: Figma (via MCP) + Spec (Token Map + checklists) + App (Playwright computed styles).
3. **Token Map + checklists**: Always verified, both in B1 and B2.

This means `/pl-web-test` is invoked with its full capability during B2 -- including Figma comparison and reference image comparison -- not the lighter-weight version used during B1 Step 3. The speed cost (~5-10 seconds per screen for Figma MCP) is acceptable in a dedicated verification phase.

### B3 (Fix Sub-Phase) -- Analyze-First Protocol

When B2 finds failures, the Builder does NOT blindly attempt a fix. Instead:

1. **Diagnose:** For each failure, analyze the root cause:
   - Is the test itself wrong? (test bug, not a code bug)
   - Is the code wrong but fixable? (straightforward regression)
   - Is the approach wrong? (the implementation strategy for Feature B conflicts with Feature A)
   - Is the spec wrong or contradictory? (the requirements for two features are incompatible)
   - Is the visual output drifted? (visual comparison shows mismatch with design reference)

2. **Act based on diagnosis:**
   - **Test bug or straightforward regression:** Fix it. Loop back to B2.
   - **Approach conflict:** Record a `[DISCOVERY]` in the companion file with a detailed failure analysis (what broke, why, what the Builder tried). Use `[Ready for Verification]` and proceed. The Architect reviews the `[DISCOVERY]` and either updates the spec, provides approach guidance in the companion file, or acknowledges the Builder's fix in a subsequent session.
   - **Spec contradiction:** Record `[INFEASIBLE]` if the feature cannot be implemented as specced. Or `[DEVIATION]` if the Builder chose a reasonable alternative. Both route to Architect.
   - **Visual drift:** If the design reference and spec disagree, record `[DISCOVERY]` noting the discrepancy. If the code matches the spec but not the design, this routes to PM for design re-ingestion.

3. **Iteration guidance:** There is no hard cap on B2-B3 iterations for straightforward fixes. The Builder should keep iterating as long as it is making progress (each iteration resolves at least one failure). When the Builder is NOT making progress (same failures persist, or fixes introduce new failures), it MUST stop iterating and escalate via `[DISCOVERY]` with the full diagnosis.

4. **Status tags after B3:** Features with all-passing tests get `[Complete]` (if auto-only) or `[Ready for Verification]` (if manual scenarios exist). Features with unresolved `[DISCOVERY]` or `[INFEASIBLE]` tags stay in TODO -- no status tag. The Builder proceeds to the next feature or phase.

**Single-feature phases:** B2 is a confirmation re-run. B3 is unlikely since the Builder just fixed issues in B1 Step 3.

**Architect collaboration path:** When the Architect reviews a B3 `[DISCOVERY]`, they can:
- Update the spec to resolve the contradiction (triggers lifecycle reset, Builder re-implements)
- Add approach guidance to the companion file (Builder reads it next session)
- Acknowledge the Builder's workaround (unblocks `[Complete]`)

## 10.11 Continuous Phase Mode (REMOVED)

The `--continuous` flag has been removed from `pl-run-builder.sh`. Use `auto_start: true` in agent config instead. The interactive Builder supports multi-phase auto-progression with `builder-worker` sub-agents. See `features/subagent_parallel_builder.md`. Invoking `--continuous` prints a deprecation warning and exits.

## 10.12 Plan Validation

Every delivery plan MUST be validated before being committed. The Builder reads `.purlin/cache/dependency_graph.json` and checks that no dependency cycles exist between phases and that phase ordering respects the feature dependency graph.

**When the Builder creates a plan** (via `/pl-delivery-plan`): The Builder reads `dependency_graph.json` to inform phase assignment, then validates the plan after writing it. If cycles are detected, the Builder fixes the plan before committing.

**Common cycle cause:** A feature placed in Phase N that depends on a feature in Phase M (where M > N). The fix is to move the dependent feature to Phase M or later.

## 10.13 Execution Groups

Execution groups combine phasing and parallelization into a single scheduling model. Phases remain the authoring unit (how work is organized in the delivery plan). Execution groups are the scheduling unit (how phases are dispatched for building).

**Concept:** After computing transitive dependencies between phases, phases with no cross-dependencies are grouped together. All phases in a group execute in the same Builder session, with independent features across the group built in parallel via `builder-worker` sub-agents.

**Example:** A 5-phase plan where Phases 2 and 3 are independent of each other but both depend on Phase 1, and Phase 4 depends on both:
- Group 1: Phase 1 (sequential foundation)
- Group 2: Phases 2, 3 (parallel -- no cross-dependencies)
- Group 3: Phase 4 (depends on Group 2)

For the complete dispatch protocol, see `/pl-build` (Execution Group Dispatch section). For plan creation and validation, see `/pl-delivery-plan`.

### Cross-References

- Sub-agent spec: `features/subagent_parallel_builder.md`
- Builder launcher spec: `features/builder_agent_launcher.md`

## 10.14 Phase Deferral Protocol

A phase feature is **role-blocked** when the Builder cannot make progress because another role must act first. Specifically:

*   `architect: TODO` -- the spec was modified or has gaps; the Architect must review before the Builder can proceed.
*   `builder: BLOCKED` -- an OPEN SPEC_DISPUTE suspends work on this feature.
*   `builder: INFEASIBLE` -- the Builder halted work; the Architect must revise the spec.

When all remaining features in a phase are role-blocked:

1.  **Detect:** During the per-feature loop, the Builder checks each feature's CDD status before starting Step 0. If the feature is role-blocked, the Builder skips it with a log message: `"Skipping <feature> -- <role> <status> (role-blocked)"`.
2.  **Defer:** When all non-blocked features in the phase are complete and only role-blocked features remain, the Builder records the phase as COMPLETE with a `**Deferred:**` annotation listing the blocked features and their blocking reason.
3.  **Re-queue:** Deferred features are appended to the next suitable PENDING phase in the delivery plan (one that does not create a dependency cycle). If no suitable phase exists, the Builder creates a new final phase labeled `Deferred Cleanup`. The re-queued features are added to the target phase's `**Features:**` line.
4.  **Announce:** The Builder prints a clear deferral message:
    ```
    Phase N complete (with deferrals)
    Completed: feature_a.md, feature_b.md
    Deferred to Phase M: feature_c.md (architect TODO)
    ```
5.  **Advance:** The Builder advances to the next phase/group normally. The deferral does not block progression.

**Deferral in the delivery plan format:** When a phase completes with deferrals, the phase entry includes:
```
**Deferred:** feature_c.md (architect TODO) -> Phase M
```
This line is added after `**Completion Commit:**`. It is a historical record -- the feature has already been moved to Phase M's feature list.

**Re-activation:** When the blocking role resolves the issue (e.g., Architect fixes the spec), the feature returns to `builder: TODO` status. The Builder picks it up in the phase it was re-queued to, following the normal per-feature loop.

**Dashboard impact:** Because deferred phases are marked COMPLETE (not stuck IN_PROGRESS), the dashboard accurately reflects progress. The deferred features appear as Builder TODO items in their new phase, and the Critic routes the blocking issue to the responsible role.
