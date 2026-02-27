**Purlin command owner: Builder**

If you are not operating as the Purlin Builder, respond: "This is a Builder command. Ask your Builder agent to run /pl-delivery-plan instead." and stop.

---

Read `instructions/references/phased_delivery.md` for the full phased delivery protocol.

If a delivery plan already exists at `.purlin/cache/delivery_plan.md`:

- Read the plan and display the current phase, completed phases, and remaining phases.
- List features in the current phase with their implementation status (TODO / TESTING / COMPLETE).
- Offer to adjust the plan: collapse remaining phases, re-split, or add new features discovered since the plan was created.

If no delivery plan exists:

- Run `tools/cdd/status.sh` to get current feature status.
- Assess scope using the heuristics below.
- Propose a phase breakdown grouped by dependency order, logical cohesion, and testability gates.
- After user confirmation, create the delivery plan at `.purlin/cache/delivery_plan.md` using the canonical format below and commit it.

**Scope Assessment Heuristics:**
*   3+ HIGH-complexity features (new implementations or major revisions) -> recommend phasing. A feature is HIGH-complexity if it meets any of: requires new infrastructure or foundational code (new modules, services, or data models), involves 5+ new or significantly rewritten functions, touches 3+ files beyond test files, or has material behavioral uncertainty (spec is new or recently revised).
*   5+ features of any complexity mix -> recommend phasing.
*   Single feature with 8+ scenarios needing implementation -> consider intra-feature phasing.
*   Builder judgment as a final factor (context exhaustion risk for the session).

If phasing is warranted, present the user with two options:
1.  **All-in-one:** Implement everything in a single session (standard workflow).
2.  **Phased delivery:** Split work into N phases, each producing a testable state. Present the proposed phase breakdown with features grouped by: (a) dependency order (foundations first), (b) logical cohesion (same subsystem together), (c) testability gate (every phase must produce verifiable output), (d) roughly balanced effort.

If the user approves phasing, create the delivery plan using the canonical format below, commit it (`git commit -m "chore: create delivery plan (N phases)"`), set Phase 1 to IN_PROGRESS, and proceed.

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
*   Exactly one phase is IN_PROGRESS at a time. All others are PENDING or COMPLETE.
*   When a phase completes, set its status to COMPLETE and record the git commit hash in "Completion Commit".
*   "QA Bugs Addressed" lists bug IDs or one-line descriptions of bugs fixed from prior phases before starting this phase.
*   COMPLETE phases are immutable. Do not edit them after recording the commit hash.
*   When the final phase completes, delete the file and commit: `git commit -m "chore: remove delivery plan (all phases complete)"`.
