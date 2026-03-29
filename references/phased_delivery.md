# Pipeline Delivery Protocol

> This file is loaded on-demand by `purlin:delivery-plan`, `purlin:build`, and `purlin:verify`
> commands when a work plan exists or pipeline delivery is being considered.

## 10.1 Purpose
When the scope of work spans multiple features or roles, the Pipeline Delivery Protocol coordinates work across PM, Engineer, and QA modes simultaneously. Instead of a waterfall (PM all specs → Engineer all builds → QA all verification), features progress through a **pipeline** where each feature independently advances through PM → Engineer → QA stages. Independent features at different pipeline stages run in parallel via cross-mode sub-agents in isolated worktrees.

The protocol provides a **work plan** artifact that tracks per-feature pipeline status, defines **verification groups** for cross-feature regression testing, and enables **autonomous multi-feature delivery** where the agent orchestrates all three modes without user intervention.

## 10.2 The Work Plan Artifact
*   **Path:** `.purlin/work_plan.md`
*   **Created by:** Engineer mode via `purlin:delivery-plan`, when scope warrants coordinated delivery.
*   **Committed to git:** Yes -- lives outside `.purlin/cache/` (which is gitignored) because it is a coordination artifact read by all modes across sessions.
*   **Deleted by:** Engineer mode, when all features reach QA COMPLETE (or are deferred/blocked).
*   **Format:** The plan contains a summary, a pipeline status table (per-feature with PM/Engineer/QA stage), verification groups, and a plan amendments section. Features track their current pipeline stage: `pending`, `pm`, `engineer`, `qa`, `complete`. Each mode column tracks: PENDING, IN_PROGRESS, COMPLETE, BLOCKED, or SKIPPED. The work plan is a flat, priority-ordered list -- there are no numbered phases.
*   **Intra-Feature Scoping:** A feature MAY use targeted delivery via the existing `[Scope: targeted:...]` mechanism.

## 10.3 Cross-Session Resumption
When `auto_start` is `false` (default), the orchestrator pauses at **verification checkpoints** (after B2 completes for a verification group) for user review.

When `auto_start` is `true`, the orchestrator works through the entire feature list across all modes without pausing. It only stops for major plan amendments (new features added, dependencies restructured) or unresolvable blockers.

When a work plan exists at session start, the orchestrator reads the pipeline status table and resumes dispatching from the current state. Features already at a later stage are not re-processed. QA bugs recorded against completed features are addressed before advancing those features.

**Scope Reset on Plan Completion:** When all features reach their terminal state and the work plan is deleted, the orchestrator MUST reset `change_scope` to `full` for any feature still in `engineer: "TODO"` status. This prevents scenarios from becoming invisible after the work plan context is deleted.

## 10.4 QA Interaction
QA mode MUST check for a work plan at `.purlin/work_plan.md` during startup. If the plan exists, QA classifies each TESTING feature by its pipeline status: "fully delivered" (Engineer column is COMPLETE and no targeted scope remains) or "more work coming" (Engineer column is IN_PROGRESS or feature has targeted scope). QA MUST NOT mark a feature as `[Complete]` if the Engineer column shows incomplete work, even if all currently-delivered scenarios pass.

In the pipeline model, QA can verify features as soon as their Engineer stage completes -- it does not wait for all features to finish building. The orchestrator dispatches `qa-worker` sub-agents for features ready for verification while other features are still in earlier pipeline stages.

## 10.5 Pipeline Delivery is Optional
Pipeline delivery is never automatic unless the user has opted into autonomous execution. The orchestrator proposes a work plan based on scope assessment, and the user decides whether to accept it, modify the feature list, or proceed with single-feature sequential delivery. At any verification checkpoint, the user may adjust the plan.

**Exceptions:**
*   **`auto_start: true`:** When `auto_start` is enabled, the orchestrator MUST NOT prompt for plan approval at any point. The user has delegated all execution decisions. Specifically:
    - If scope assessment recommends a work plan: create it automatically and begin dispatching immediately. Do NOT present options or approval questions.
    - Verification checkpoints: continue dispatching without pausing. Do NOT halt for user review.
    - Plan amendments for minor changes: auto-update without prompting.
    - The ONLY exception requiring user input under `auto_start: true` is plan amendments for major changes (new features added, dependencies restructured) -- these require confirmation because they change the scope the user originally delegated.

## 10.6 PM Awareness
If PM modifies feature specs while a work plan is active, the orchestrator detects the mismatch on resume and proposes a plan amendment. Minor changes (added scenarios, clarified requirements) are auto-updated. Major changes (new features, restructured dependencies) require user approval before continuing. In pipeline mode, PM spec work for later features may be concurrent with Engineer builds for earlier features -- the orchestrator ensures a feature does not enter Engineer stage until its PM stage is COMPLETE.

## 10.7 Work Plan Structure

The work plan is a flat, priority-ordered list of features with per-feature pipeline status. There are no numbered phases or sizing caps. Features are ordered by dependency (foundations first) and dispatched to their next pipeline stage as capacity allows.

### 10.7.1 Pipeline Stages

Each feature progresses through stages independently:

| Stage | Description | Sub-Agent | Mode |
|-------|-------------|-----------|------|
| `pending` | Not yet started | -- | -- |
| `pm` | Spec being written or refined | `pm-worker` | PM |
| `engineer` | Implementation in progress | `engineer-worker` | Engineer |
| `qa` | Verification in progress | `qa-worker` | QA |
| `complete` | All stages done | -- | -- |

A feature advances to the next stage only when its current stage completes. Dependencies are respected: if feature B depends on feature A, B cannot enter `engineer` until A's `engineer` stage completes.

### 10.7.2 Verification Groups

Features that share interaction surface (data models, APIs, UI components) are grouped into **verification groups** for cross-feature regression testing (B2). The orchestrator defines these groups when creating the work plan, based on interaction density analysis from `dependency_graph.json`.

B2 runs when **all features in a verification group** complete their Engineer stage. Features with no shared interaction surface form singleton verification groups (B2 is a confirmation re-run for them).

Example verification groups:
```
Group "auth": auth_flow, session_management  (share auth data model)
Group "ui-nav": sidebar, navigation          (share layout components)
Group "solo": settings                       (no shared surface)
```

### 10.7.3 Canonical Work Plan Format

```markdown
# Work Plan
**Created:** <date>
**Features:** <count>

## Pipeline Status

| Feature | Stage | PM | Engineer | QA | V-Group | Notes |
|---------|-------|----|----------|----|---------|-------|
| auth_flow | engineer | COMPLETE | IN_PROGRESS | PENDING | auth | |
| session_mgmt | pm | IN_PROGRESS | PENDING | PENDING | auth | |
| settings | engineer | SKIPPED | IN_PROGRESS | PENDING | solo | existing spec |
| sidebar | pending | PENDING | PENDING | PENDING | ui-nav | depends: auth_flow |

## Verification Groups
- **auth:** auth_flow, session_mgmt — shared auth data model
- **ui-nav:** sidebar, navigation — shared layout components
- **solo:** settings — no shared interaction surface

## Amendments
<chronological log of plan changes>
```

**Stage column** tracks the feature's current active stage. **Mode columns** (PM, Engineer, QA) track per-mode completion. **V-Group** assigns the feature to a verification group for B2.

### 10.7.4 Concurrency Limits

The orchestrator dispatches features to sub-agents in worktrees with a configurable concurrency limit:

*   **Default:** 3 concurrent worktrees.
*   **Override:** Optional `max_concurrent_worktrees` in agent config.
*   Each worktree is a full repo clone -- beyond 4, diminishing returns from disk/git overhead and merge complexity.
*   At most 1 active worktree per feature at a time.

The orchestrator fills available slots by priority order: features earlier in the dependency-ordered list are dispatched first.

## 10.8 Context Budget Awareness

The orchestrator delegates all heavy work (reading specs, writing code, running tests) to sub-agents in worktrees. The orchestrator itself only reads summaries, dispatches work, and tracks pipeline state. This keeps orchestrator context consumption low.

Sub-agents each have their own context window. No cross-sub-agent context budget coordination is needed -- each sub-agent works on a single feature independently.

The PreCompact hook saves enriched pipeline state (mode, work plan status, active worktrees, recent commits) so the orchestrator can recover after compaction without a full scan. The orchestrator works until context naturally fills, checkpoints via PreCompact, resumes via `purlin:resume`, and continues dispatching.

## 10.9 Verification Group Internal Structure (B1/B2/B3)

Each verification group has an internal three-step structure that separates implementation from cross-feature regression testing. B1 runs per-feature (potentially in parallel across features). B2 and B3 run per-verification-group after all member features complete B1.

### B1 (Build Sub-Phase)

Per-feature implementation loop (Steps 0-3 of the Engineer build protocol). Each feature is implemented and locally tested including web tests. No status tags yet. In pipeline mode, B1 for each feature runs in an `engineer-worker` sub-agent in an isolated worktree. Visual design read priority: Token Map -> brief.json -> Figma (last resort) for implementation decisions. Web test verification (`purlin:web-test`) uses Figma MCP for three-source comparison when available, regardless of this priority. The Engineer iterates per-feature until `purlin:web-test` passes. Fast iteration.

### B2 (Test Sub-Phase)

After B1 completes for **all features in a verification group**, re-run the full test suite AND all applicable web tests for every feature in the group. This catches cross-feature regressions. Record which features/tests failed and which passed. B2 runs in the main session (not in a worktree) because it needs access to all merged code.

**B2 Visual Design Verification:** During B2, the Engineer's visual verification priority INVERTS from B1. Implementation is complete -- accuracy matters more than iteration speed. For features with a `## Visual Specification` section:

1. **Reference images** (in `features/_design/`): During B1, these are audit references, not Engineer inputs. During B2, they become verification inputs. The Engineer takes a Playwright screenshot and compares it against the reference image. This is fast (local, multimodal) and catches obvious visual drift.
2. **Figma MCP** (if available): During B1, Figma is last resort. During B2, it is the authoritative design source. The Engineer uses the same three-source triangulated verification that `purlin:web-test` already supports: Figma (via MCP) + Spec (Token Map + checklists) + App (Playwright computed styles).
3. **Token Map + checklists**: Always verified, both in B1 and B2.

This means `purlin:web-test` is invoked with its full capability during B2 -- including Figma comparison and reference image comparison -- not the lighter-weight version used during B1 Step 3. The speed cost (~5-10 seconds per screen for Figma MCP) is acceptable in a dedicated verification step.

**Singleton verification groups:** When a verification group contains a single feature, B2 is a confirmation re-run. B3 is unlikely since the Engineer just fixed issues in B1 Step 3.

### B3 (Fix Sub-Phase) -- Analyze-First Protocol

When B2 finds failures, the Engineer does NOT blindly attempt a fix. Instead:

1. **Diagnose:** For each failure, analyze the root cause:
   - Is the test itself wrong? (test bug, not a code bug)
   - Is the code wrong but fixable? (straightforward regression)
   - Is the approach wrong? (the implementation strategy for Feature B conflicts with Feature A)
   - Is the spec wrong or contradictory? (the requirements for two features are incompatible)
   - Is the visual output drifted? (visual comparison shows mismatch with design reference)

2. **Act based on diagnosis:**
   - **Test bug or straightforward regression:** Fix it. Loop back to B2.
   - **Approach conflict:** Record a `[DISCOVERY]` in the companion file with a detailed failure analysis (what broke, why, what the Engineer tried). Use `[Ready for Verification]` and proceed. PM reviews the `[DISCOVERY]` and either updates the spec, provides approach guidance in the companion file, or acknowledges the Engineer's fix in a subsequent session.
   - **Spec contradiction:** Record `[INFEASIBLE]` if the feature cannot be implemented as specced. Or `[DEVIATION]` if the Engineer chose a reasonable alternative. Both route to PM.
   - **Visual drift:** If the design reference and spec disagree, record `[DISCOVERY]` noting the discrepancy. If the code matches the spec but not the design, this routes to PM for design re-ingestion.

3. **Iteration guidance:** There is no hard cap on B2-B3 iterations for straightforward fixes. The Engineer should keep iterating as long as it is making progress (each iteration resolves at least one failure). When the Engineer is NOT making progress (same failures persist, or fixes introduce new failures), it MUST stop iterating and escalate via `[DISCOVERY]` with the full diagnosis.

4. **Status tags after B3:** Features with all-passing tests get `[Complete]` (if auto-only) or `[Ready for Verification]` (if manual scenarios exist). Features with unresolved `[DISCOVERY]` or `[INFEASIBLE]` tags stay in TODO -- no status tag. The orchestrator advances those features to the QA stage (or marks them blocked).

**PM collaboration path:** When PM reviews a B3 `[DISCOVERY]`, they can:
- Update the spec to resolve the contradiction (triggers lifecycle reset, Engineer re-implements)
- Add approach guidance to the companion file (Engineer reads it next session)
- Acknowledge the Engineer's workaround (unblocks `[Complete]`)

## 10.10 Continuous Phase Mode (REMOVED)

The `--continuous` flag has been removed from the Engineer launcher. Use `auto_start: true` in agent config instead. The unified Purlin agent supports pipeline delivery with cross-mode sub-agents. See `features/install_update/subagent_parallel_builder.md`.

## 10.11 Plan Validation

Every work plan MUST be validated before being committed. The orchestrator reads `.purlin/cache/dependency_graph.json` and checks that no dependency cycles exist in the feature ordering and that the dependency graph is respected.

**When the orchestrator creates a plan** (via `purlin:delivery-plan`): It reads `dependency_graph.json` to inform feature ordering, assigns verification groups based on interaction density, then validates the plan. If cycles are detected, the plan is corrected before committing.

## 10.12 Pipeline Dispatch

The pipeline dispatch model replaces the previous execution group model. Instead of grouping features into phases and then grouping phases into execution groups, the orchestrator dispatches features directly to their next pipeline stage.

**Orchestrator loop:**
1. Read work plan + scan state.
2. For each feature in priority order, determine next action based on current stage and dependencies.
3. Dispatch to available worktree slots (respecting concurrency limit from Section 10.7.4).
4. Wait for any sub-agent to complete. Merge the completed worktree branch.
5. Update work plan (advance feature to next stage).
6. When all features in a verification group complete Engineer stage → run B2/B3 in main session.
7. Dispatch `qa-worker` sub-agents for features that pass B2.
8. Continue until all features reach `complete` or are blocked.

**Cross-mode parallelism:** The orchestrator can dispatch sub-agents in different modes simultaneously. A `pm-worker` writing a spec for feature C, an `engineer-worker` building feature B, and a `qa-worker` verifying feature A can all run concurrently in separate worktrees. This is safe because PM writes specs, Engineer writes code, and QA writes discoveries -- disjoint file sets that do not create merge conflicts.

**Fallback to sequential:** When the feature count is small (1-2 features) or all features have tight dependencies, the orchestrator works directly in the main session, switching modes as needed via `purlin:mode`. The pipeline model is an optimization, not a requirement.

### Cross-References

- Sub-agent spec: `features/install_update/subagent_parallel_builder.md`
- Agent launcher spec: `features/framework_core/purlin_agent_launcher.md`

## 10.13 Blocked Feature Protocol

A feature is **role-blocked** when the orchestrator cannot advance it because another role must act first. Specifically:

*   `pm: TODO` -- the spec was modified or has gaps; PM must review before Engineer can proceed.
*   `engineer: BLOCKED` -- an OPEN SPEC_DISPUTE suspends work on this feature.
*   `engineer: INFEASIBLE` -- the Engineer halted work; PM must revise the spec.

In the pipeline model, blocked features do not block other features. The orchestrator:

1.  **Detects** the block when attempting to dispatch: checks scan status before advancing to the next stage. If blocked, logs: `"Skipping <feature> -- <role> <status> (role-blocked)"`.
2.  **Marks** the feature's current mode column as BLOCKED in the work plan.
3.  **Continues** dispatching other features. Blocked features do not consume worktree slots.
4.  **Announces** the block: `"feature_c.md blocked: pm TODO -- skipping, will retry when unblocked"`.
5.  **Re-checks** on each dispatch loop iteration. When the blocking role resolves the issue (e.g., PM fixes the spec), the feature returns to actionable status and the orchestrator dispatches it normally.

**Cross-mode pipeline advantage:** In the pipeline model, if feature C is blocked on PM, the orchestrator can dispatch a `pm-worker` to resolve the issue concurrently with Engineer work on other features. This is a significant speedup over the waterfall model where PM and Engineer work sequentially.
