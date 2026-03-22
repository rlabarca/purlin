**Purlin command owner: Builder**

If you are not operating as the Purlin Builder, respond: "This is a Builder command. Ask your Builder agent to run /pl-delivery-plan instead." and stop.

---

## Path Resolution

Read `.purlin/config.json` and extract `tools_root` (default: `"tools"`). Resolve project root via `PURLIN_PROJECT_ROOT` env var or by climbing from CWD until `.purlin/` is found. Set `TOOLS_ROOT = <project_root>/<tools_root>`.

---

If a delivery plan already exists at `.purlin/delivery_plan.md`:

- Read the plan and display the current phase, completed phases, and remaining phases.
- List features in the current phase with their implementation status (TODO / TESTING / COMPLETE).
- Offer to adjust the plan: collapse remaining phases, re-split, or add new features discovered since the plan was created.

If no delivery plan exists:

- Run `${TOOLS_ROOT}/cdd/status.sh` to get current feature status.
- Read `.purlin/cache/dependency_graph.json` and build a map of each feature's prerequisite features (direct and transitive). This gives you concrete data for phase assignment instead of relying on judgment alone.
- After proposing phases, read `.purlin/cache/dependency_graph.json` and check pairwise feature independence within each proposed phase. Report in the plan presentation which phases have parallel build opportunities (independent features that can build concurrently) and which are fully sequential. Also compute execution groups: identify which phases can execute in parallel (no cross-phase dependencies) and present them to the user (e.g., "Phases 2 and 3 will execute in parallel (Group 2). Phase 4 depends on Group 2.").
- Assess scope using the heuristics below.
- Propose a phase breakdown grouped by dependency order, logical cohesion, and testability gates.
- After user confirmation, create the delivery plan at `.purlin/delivery_plan.md` using the canonical format below.
- **Validation gate:** After writing `delivery_plan.md` but BEFORE committing, read `.purlin/cache/dependency_graph.json` and verify that no dependency cycles exist between phases. For each pair of phases, check if any feature in Phase A depends (transitively) on any feature in Phase B -- if so, Phase A must come after Phase B. If cycles or ordering violations are found, fix the plan (typically by moving the dependent feature to a later phase). Only commit after validation passes.

**Scope Assessment Heuristics:**
*   2+ HIGH-complexity features (new implementations or major revisions) -> recommend phasing. A feature is HIGH-complexity if it meets any of: requires new infrastructure or foundational code (new modules, services, or data models), involves 5+ new or significantly rewritten functions, touches 3+ files beyond test files, or has material behavioral uncertainty (spec is new or recently revised).
*   3+ features of any complexity mix -> recommend phasing.
*   Single feature with 5+ unimplemented scenarios -> consider intra-feature phasing.
*   **Context budget awareness:** When assessing phase sizing, estimate the context budget for each phase. A phase that would require reading many large feature specs, implementing across many files, and running extensive tests is more likely to exhaust context. Prefer smaller phases when the cumulative scope (spec reading + implementation + testing) is large. This is a soft signal, not a hard cap -- testability and dependency order take priority. See `instructions/references/phased_delivery.md` Section 10.9.

**Per-Phase Sizing Caps:**
*   Max **2 features per phase** regardless of complexity.
*   Max **1 HIGH-complexity feature per phase** if the phase contains any other feature.
*   A single HIGH-complexity feature with 5+ scenarios gets its own dedicated phase.
*   See `instructions/references/phased_delivery.md` Section 10.8 for the normative rules.

If phasing is warranted, present the user with two options:
1.  **All-in-one:** Implement everything in a single session (standard workflow).
2.  **Phased delivery:** Split work into N phases, each producing a testable state. Present the proposed phase breakdown with features grouped by: (a) dependency order (foundations first), (b) logical cohesion (same subsystem together), (c) testability gate (every phase must produce verifiable output), (d) roughly balanced effort, (e) interaction density -- features that share data, APIs, or components benefit from being in the same phase where B2 catches their cross-feature regressions, (f) dependency correctness -- a feature MUST be placed in a phase equal to or later than every phase containing any of its prerequisite features (direct or transitive per `dependency_graph.json`). Violating this creates a cycle that blocks `--continuous` execution. When a feature depends on features in multiple phases, it goes in or after the latest of those phases, (g) parallelization opportunity -- features with no mutual dependencies can be parallelized at two levels: separate phases that form execution groups (phase-level, independent phases execute in parallel as a group) or same phase with parallel dispatch (feature-level, independent features within a phase build concurrently via `builder-worker` sub-agents). Prefer separate phases when features have no B2 interaction need. Prefer same phase when features share data models or APIs that benefit from B2 cross-feature regression testing -- they still build in parallel via the execution group dispatch in `/pl-build`.

If the user approves phasing, create the delivery plan using the canonical format below, run the validation gate (see above), then commit it (`git commit -m "chore: create delivery plan (N phases)"`), set Phase 1 to IN_PROGRESS, and proceed.

**Phase Internal Structure (B1/B2/B3):**
*   **B1 (Build):** Existing per-feature loop (Steps 0-3 from `/pl-build`). Each feature implemented and locally tested including web tests.
*   **B2 (Test):** After B1 completes for all phase features, re-run full test suite AND all web tests for every feature. Catches cross-feature regressions.
*   **B3 (Fix):** Analyze-first protocol. Diagnose each failure (test bug? regression? approach conflict? spec contradiction?), then: fix straightforward issues and re-test, or escalate via `[DISCOVERY]`/`[INFEASIBLE]`.
*   Status tags only after B2 passes or B3 escalations are recorded.

**Cross-Session Rule:** Each phase is a separate Builder session. STOP after completing a phase. Do not auto-advance.

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
**QA Bugs Addressed:** --

## Phase 2 -- <Short Label> [PENDING]
**Features:** <feature-name-3.md>
**Completion Commit:** --
**QA Bugs Addressed:** --

## Plan Amendments
_None._
```

**Rules:**
*   One or more phases may be IN_PROGRESS simultaneously when they belong to the same execution group. All other phases are PENDING or COMPLETE.
*   When a phase completes, set its status to COMPLETE and record the git commit hash in "Completion Commit".
*   "QA Bugs Addressed" lists bug IDs or one-line descriptions of bugs fixed from prior phases before starting this phase.
*   COMPLETE phases are immutable. Do not edit them after recording the commit hash.
*   When the final phase completes, delete the file and commit: `git commit -m "chore: remove delivery plan (all phases complete)"`.
