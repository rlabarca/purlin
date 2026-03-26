**Purlin mode: Engineer**

Purlin agent: This skill activates Engineer mode. If another mode is active, confirm switch first.

---

## Path Resolution

> See `instructions/references/path_resolution.md`. Produces `TOOLS_ROOT`.
> **Commit format:** See `instructions/references/commit_conventions.md`.
> **Companion files:** See `instructions/references/active_deviations.md` for deviation format and PM review protocol.

---

If a delivery plan already exists at `.purlin/delivery_plan.md`:

- Read the plan and display the current phase, completed phases, and remaining phases.
- List features in the current phase with their implementation status (TODO / TESTING / COMPLETE).
- Offer to adjust the plan: collapse remaining phases, re-split, or add new features discovered since the plan was created.

If no delivery plan exists:

- Run `${TOOLS_ROOT}/cdd/scan.sh` to get current feature status.
- Read `.purlin/cache/dependency_graph.json` and build a map of each feature's prerequisite features (direct and transitive). This gives you concrete data for phase assignment instead of relying on judgment alone.
- After proposing phases, read `.purlin/cache/dependency_graph.json` and check pairwise feature independence within each proposed phase. Report in the plan presentation which phases have parallel build opportunities (independent features that can build concurrently) and which are fully sequential. Also compute execution groups: identify which phases can execute in parallel (no cross-phase dependencies) and present them to the user (e.g., "Phases 2 and 3 will execute in parallel (Group 2). Phase 4 depends on Group 2.").
- Assess scope using the heuristics below.
- Propose a phase breakdown grouped by dependency order, logical cohesion, and testability gates.
- After user confirmation, create the delivery plan at `.purlin/delivery_plan.md` using the canonical format below.
- **Validation gate:** After writing `delivery_plan.md` but BEFORE committing, read `.purlin/cache/dependency_graph.json` and verify that no dependency cycles exist between phases. For each pair of phases, check if any feature in Phase A depends (transitively) on any feature in Phase B -- if so, Phase A must come after Phase B. If cycles or ordering violations are found, fix the plan (typically by moving the dependent feature to a later phase). Only commit after validation passes.

**Context Tier Resolution:**

Before assessing scope, resolve Engineer mode's context tier:
1. Read Engineer mode's configured model from agent config (`agents.builder.model`).
2. Look up that model ID in the config `models` array to get `context_window_tokens`.
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

**Scope Assessment Heuristics (tier-aware):**
*   **Standard tier:** 2+ HIGH-complexity features or 3+ features of any mix -> recommend phasing. Single feature with 5+ unimplemented scenarios -> consider intra-feature phasing.
*   **Extended tier:** 4+ HIGH-complexity features or 7+ features of any mix -> recommend phasing. Single feature with 8+ unimplemented scenarios -> consider intra-feature phasing.
*   A feature is HIGH-complexity if it meets any of: requires new infrastructure or foundational code (new modules, services, or data models), involves 5+ new or significantly rewritten functions, touches 3+ files beyond test files, or has material behavioral uncertainty (spec is new or recently revised).
*   **Context budget awareness:** When assessing phase sizing, estimate the context budget for each phase. A phase that would require reading many large feature specs, implementing across many files, and running extensive tests is more likely to exhaust context. Prefer smaller phases when the cumulative scope (spec reading + implementation + testing) is large. This is a soft signal, not a hard cap -- testability and dependency order take priority. See `instructions/references/phased_delivery.md` Section 10.9.

**Per-Phase Sizing Caps (tier-derived):**
*   Max features per phase: **2** (Standard) or **5** (Extended). Override via `phase_sizing.max_features_per_phase`.
*   Max HIGH-complexity features per phase: **1** (Standard) or **2** (Extended). Override via `phase_sizing.max_high_per_phase`.
*   A single HIGH-complexity feature with **5+** (Standard) or **8+** (Extended) scenarios gets its own dedicated phase. Override via `phase_sizing.high_solo_threshold`.
*   See `instructions/references/phased_delivery.md` Section 10.8 for the normative rules.

If phasing is warranted, present the user with two options:
1.  **All-in-one:** Implement everything in a single session (standard workflow).
2.  **Phased delivery:** Split work into N phases, each producing a testable state. Present the proposed phase breakdown with features grouped by: (a) dependency order (foundations first), (b) logical cohesion (same subsystem together), (c) testability gate (every phase must produce verifiable output), (d) roughly balanced effort, (e) interaction density -- features that share data, APIs, or components benefit from being in the same phase where B2 catches their cross-feature regressions, (f) dependency correctness -- a feature MUST be placed in a phase equal to or later than every phase containing any of its prerequisite features (direct or transitive per `dependency_graph.json`). Violating this creates a cycle that blocks `--continuous` execution. When a feature depends on features in multiple phases, it goes in or after the latest of those phases, (g) parallelization opportunity -- features with no mutual dependencies can be parallelized at two levels: separate phases that form execution groups (phase-level, independent phases execute in parallel as a group) or same phase with parallel dispatch (feature-level, independent features within a phase build concurrently via `engineer-worker` sub-agents). Prefer separate phases when features have no B2 interaction need. Prefer same phase when features share data models or APIs that benefit from B2 cross-feature regression testing -- they still build in parallel via the execution group dispatch in `/pl-build`.

If the user approves phasing, create the delivery plan using the canonical format below, run the validation gate (see above), then commit it (`git commit -m "chore: create delivery plan (N phases)"`), set Phase 1 to IN_PROGRESS, and proceed.

**Phase Internal Structure (B1/B2/B3):**
*   **B1 (Build):** Existing per-feature loop (Steps 0-3 from `/pl-build`). Each feature implemented and locally tested including web tests.
*   **B2 (Test):** After B1 completes for all phase features, re-run full test suite AND all web tests for every feature. Catches cross-feature regressions.
*   **B3 (Fix):** Analyze-first protocol. Diagnose each failure (test bug? regression? approach conflict? spec contradiction?), then: fix straightforward issues and re-test, or escalate via `[DISCOVERY]`/`[INFEASIBLE]`.
*   Status tags only after B2 passes or B3 escalations are recorded.

**Cross-Session Rule:** Each phase is a separate Engineer session. STOP after completing a phase. Do not auto-advance.

**Canonical `delivery_plan.md` format:**

```markdown
# Delivery Plan

**Created:** <YYYY-MM-DD>
**Total Phases:** <N>

## Summary
<One or two sentences describing the overall scope and why phasing was chosen.>

## Phase 1 -- <Short Label> [IN_PROGRESS]
**Features:** <feature-name-1.md>, <feature-name-2.md>
**Completion Commit:** --
**Deferred:** --
**QA Bugs Addressed:** --

## Phase 2 -- <Short Label> [PENDING]
**Features:** <feature-name-3.md>
**Completion Commit:** --
**Deferred:** --
**QA Bugs Addressed:** --

## Plan Amendments
_None._
```

**Rules:**
*   One or more phases may be IN_PROGRESS simultaneously when they belong to the same execution group. All other phases are PENDING or COMPLETE.
*   When a phase completes, set its status to COMPLETE and record the git commit hash in "Completion Commit".
*   "QA Bugs Addressed" lists bug IDs or one-line descriptions of bugs fixed from prior phases before starting this phase.
*   COMPLETE phases are immutable. Do not edit them after recording the commit hash.
*   When a phase completes with deferred features, record them in the `**Deferred:**` field (e.g., `feature_c.md (architect TODO) -> Phase M`). The deferred features must also be added to the target phase's `**Features:**` line. See `instructions/references/phased_delivery.md` Section 10.14.
*   When the final phase completes, delete the file and commit: `git commit -m "chore: remove delivery plan (all phases complete)"`.
