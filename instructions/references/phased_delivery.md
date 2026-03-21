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

When `auto_start` is `true`, the Builder auto-advances to the next PENDING phase within the same session. This replaces the bash-based `--continuous` orchestrator with native multi-phase progression.

When a delivery plan exists at session start, the Builder resumes from the next PENDING phase. QA bugs recorded during prior phases are addressed first, before new phase work begins. If the IN_PROGRESS phase was interrupted mid-session, the Builder resumes that phase, skipping features already in TESTING state.

**`--continuous` deprecation:** The `--continuous` flag is deprecated. Use `auto_start: true` in agent config instead. See `features/subagent_parallel_builder.md` Section 2.9.

**Scope Reset on Plan Completion:** When the Builder completes the final phase and deletes the delivery plan, the Builder MUST reset the `change_scope` to `full` for every feature that participated in the plan and still has `builder: "TODO"` status. Targeted scopes are artifacts of the phased delivery -- once the plan is gone, any remaining unbuilt work must be visible under a full scope. This prevents scenarios from becoming invisible to future Builder sessions after the delivery plan context is deleted.

## 10.4 QA Interaction
The QA Agent MUST check for a delivery plan at `.purlin/delivery_plan.md` during startup. If the plan exists, QA classifies each TESTING feature as either "fully delivered" (appears only in COMPLETE phases) or "more work coming" (appears in a PENDING phase). QA MUST NOT mark a feature as `[Complete]` if it appears in any PENDING phase of the delivery plan, even if all currently-delivered scenarios pass. QA informs the user which features are phase-gated.

## 10.5 Phasing is Optional
Phased delivery is never automatic unless the user has opted into autonomous execution. The Builder proposes phasing based on scope assessment, and the user decides whether to accept phasing, modify the phase breakdown, or proceed with a single-session delivery. At any approval checkpoint, the user may collapse remaining phases, re-split, or abandon phasing entirely.

**Exceptions:**
*   **`auto_start: true`:** When the Builder's `auto_start` config flag is enabled and the scope assessment heuristics are met, the Builder creates the delivery plan automatically and begins Phase 1. The user has delegated approval by enabling `auto_start`.
*   **`--continuous` mode:** When the Builder is launched with `--continuous` mode and no delivery plan exists, the bootstrap session creates the plan autonomously. The user reviews and approves the plan at a checkpoint before continuous execution begins.

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

## 10.11 Continuous Phase Mode (DEPRECATED)

> **Deprecated.** The `--continuous` flag is deprecated. Use `auto_start: true` in agent config instead. The interactive Builder now supports multi-phase auto-progression with `builder-worker` sub-agents. See `features/subagent_parallel_builder.md`. The `--continuous` flag prints a deprecation warning and exits.

The following describes the legacy behavior for reference during the migration period:

The Builder launcher (`pl-run-builder.sh`) supported an opt-in `--continuous` flag that automated the multi-phase delivery cycle. When active, the launcher progressed through all delivery plan phases without human intervention, using an LLM evaluator to decide the correct action after each Builder exit.

### How It Worked

0. **Bootstrap (if needed):** If no delivery plan exists when `--continuous` is invoked, the launcher runs a one-time bootstrap Builder session. This session runs the standard scope assessment and either creates a delivery plan autonomously or completes the work directly if phasing is not warranted. The bootstrap uses a conservative sizing bias (more/smaller phases, maximize parallelization) to prevent context exhaustion. After plan creation, the user is prompted to approve before the loop begins. See `features/continuous_phase_builder.md` Section 2.15.

1. **Phase Analysis:** Before the first phase, the launcher runs `{tools_root}/delivery/phase_analyzer.py` to determine execution order and parallelization opportunities. The analyzer reads the delivery plan and dependency graph, topologically sorts phases by their inter-phase dependencies, and groups independent phases into parallel execution sets.

2. **Execution Loop:** The launcher iterates through execution groups sequentially. For single-phase groups, the Builder runs in `-p` mode (non-interactive). For multi-phase groups, each Builder runs in a separate git worktree (`-w` flag) and the worktree branches are merged back after all complete.

3. **LLM Evaluator:** After each Builder exit, the output is piped to a Haiku-based evaluator that returns a structured decision: `continue` (next phase), `approve` (Builder paused for approval, resume session), `retry` (context exhaustion, relaunch same phase), or `stop` (error or completion).

4. **System Prompt Overrides:** In continuous mode, two overrides are appended to the Builder's system prompt: (a) an auto-proceed override that instructs the Builder to never pause for approval, and (b) a server permission override that grants the Builder permission to start/stop server processes for local verification.

### Key Properties

- **Opt-in only.** Without `--continuous`, the launcher behaves identically to today. Continuous mode is never automatic.
- **Phase ordering correction.** The phase analyzer detects when the delivery plan has phases in the wrong dependency order and reorders them automatically.
- **Parallel execution.** Independent phases (no cross-phase feature dependencies) run concurrently in separate worktrees, reducing total build time.
- **Retry budget.** Maximum 2 consecutive retries per phase. If the retry limit is exceeded, the loop exits with an escalation message.
- **Merge conflict escalation.** If merging parallel worktree branches produces a conflict, the loop stops immediately and directs the user to resolve manually.
- **Evaluator fallback.** If the evaluator itself fails (Haiku unavailable), the launcher falls back to checking whether the delivery plan file changed since the last phase.
- **Auto-bootstrap with approval.** If no delivery plan exists, the launcher creates one via a bootstrap session, presents it for user approval, then enters the continuous loop. The bootstrap favors conservative phase sizing to keep each session within context budget.
- **Output visibility.** Sequential phases and bootstrap stream Builder output to the terminal in real time. Parallel phases show a periodic heartbeat with elapsed time and log growth. Full log files are always written for the evaluator.

### Logging

- Each phase's full output is written to `.purlin/runtime/continuous_build_phase_<N>.log`.
- At exit, a summary reports: phases completed, parallel groups used, any failures, retries consumed, and total wall-clock duration.

### Dynamic Plan Handling

- The delivery plan is a **live document**. The Builder may amend it during any phase (adding QA fix phases, splitting large phases, removing unnecessary phases).
- The orchestration loop re-runs the phase analyzer **before each execution group**, so plan amendments are automatically picked up without special "diff" logic.
- Phase numbers need not be contiguous. The analyzer operates on whatever PENDING phases exist at analysis time.
- **Parallel amendment protocol:** During parallel execution, Builders write structured amendment requests to `.purlin/runtime/plan_amendment_phase_<N>.json` instead of modifying the delivery plan directly. The orchestrator applies amendments centrally after worktree merges complete. This prevents Markdown merge conflicts on the delivery plan file.

## 10.12 Plan Validation

Every delivery plan MUST pass the phase analyzer (`{tools_root}/delivery/phase_analyzer.py`) before being committed. The analyzer validates that no dependency cycles exist between phases and that phase ordering respects the feature dependency graph.

**When the Builder creates a plan** (via `/pl-delivery-plan`): The Builder reads `dependency_graph.json` to inform phase assignment, then runs the analyzer after writing the plan file. If cycles are detected, the Builder fixes the plan before committing.

**When the bootstrap creates a plan** (via `--continuous`): The launcher runs the analyzer as a post-bootstrap validation. If cycles are detected, the launcher exits with the plan committed for manual editing (see `features/continuous_phase_builder.md` Section 2.15).

**Common cycle cause:** A feature placed in Phase N that depends on a feature in Phase M (where M > N). The fix is to move the dependent feature to Phase M or later.

## 10.13 Feature-Level B1 Parallelism

Within a single delivery phase, independent features can build in parallel using worktree-isolated agents. This complements the phase-level parallelism in Section 10.11 — both use the same analyzer and protocol structure.

### Eligibility

- The current phase has 2+ features.
- `phase_analyzer.py --intra-phase <N>` returns a `parallel: true` group with 2+ features.
- The user has not opted for sequential execution.

### Protocol

1. Run `phase_analyzer.py --intra-phase <current_phase>`.
2. For each `parallel: true` group, spawn one `builder-worker` sub-agent per feature (see `.claude/agents/builder-worker.md`). Each sub-agent runs in an isolated worktree.
3. Each sub-agent runs `/pl-build` Steps 0-2 for its assigned feature only. No Step 3 (verification), no Step 4 (status tags). The sub-agent definition enforces these constraints via its system prompt.
4. After all sub-agents in a group return, merge branches using the **Robust Merge Protocol** (see `/pl-build`): rebase-before-merge with safe-file auto-resolve. Unsafe conflicts fall back to sequential for the affected feature only.
5. Process `parallel: false` groups sequentially, using the standard per-feature loop (Steps 0-2).
6. After all groups complete, proceed to B2. B2 runs full verification (tests, web tests, Figma) on the merged code in the main session.

### MCP Note

Agent tool sub-agents do not have MCP connections. This is why verification is deferred to B2 — the main session retains MCP access for web tests and Figma checks. Continuous mode's parallel phases use separate `claude` processes which DO have MCP, but B2 still runs the same way, so behavior is consistent across both modes.

### Merge Conflict Strategy

Uses the **Robust Merge Protocol** defined in `/pl-build`: rebase-before-merge with safe-file auto-resolve. Safe files (`.purlin/delivery_plan.md`, `CRITIC_REPORT.md`, `.purlin/cache/*`) are auto-resolved by keeping main's version. Unsafe conflicts trigger sequential fallback for the affected feature only -- already-merged features are preserved.

### Sub-Agent Cross-Reference

The interactive Builder uses `builder-worker` sub-agents (`.claude/agents/builder-worker.md`) for feature-level parallelism within a phase. The `--continuous` bash orchestrator is deprecated (see Section 10.11). The phase analyzer and protocol are shared across both mechanisms during the migration period.

### Cross-References

- Feature spec: `features/continuous_phase_builder.md`
- Phase analyzer spec: `features/phase_analyzer.md`
- Builder launcher spec: `features/builder_agent_launcher.md`
