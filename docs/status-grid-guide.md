# Reading the CDD Status Grid

## Overview

The CDD Dashboard displays a status grid that shows every feature in the
project alongside its current state for each role. At a glance, you can see
which features need Architect attention, which are ready for the Builder,
which are awaiting QA verification, and which have design work pending with
the PM.

This guide explains how to read the grid: what the sections mean, what each
column represents, and how to interpret the status values and color codes.

---

## Grid Layout

The status grid is divided into three sections:

### Active

Features where at least one role still has work to do. This is where you
spend most of your time. Features are sorted by urgency:

1. Red statuses first (FAIL, INFEASIBLE) -- release blockers.
2. Yellow/orange statuses next (TODO, DISPUTED) -- work needed.
3. Alphabetical within each urgency group.

Tombstoned features (deprecated, pending deletion by the Builder) always
appear in the Active section until the Builder completes the removal.

### Complete

Features where all roles are in terminal states. These are ready for
release. The section is capped at the 10 most recently completed features
to keep the dashboard focused.

A feature appears here when:
- Architect = DONE
- Builder = DONE
- QA = CLEAN or N/A
- PM = DONE or N/A

### Workspace

Collaboration metadata: the current branch, contributor table, and sync
status indicators (SAME, AHEAD, BEHIND, DIVERGED). This section is relevant
when working on collaboration branches.

---

## The Four Role Columns

Each feature row has four status columns. The values in each column reflect
[the Critic](critic-and-cdd-guide.md)'s analysis of that feature for that role.

### Architect Column

| Status | Color | Meaning |
|--------|-------|---------|
| **DONE** | Green | No Architect action items. The spec is complete and well-formed. |
| **TODO** | Yellow | Spec gaps exist, unacknowledged Builder decisions, or other Architect work is pending. |
| **??** | Gray | No `critic.json` exists for this feature yet (Critic has not run). |

The Architect column reflects the **Spec Gate**. When the Critic finds
missing sections, malformed scenarios, or undeclared prerequisites, this
column turns yellow.

### Builder Column

| Status | Color | Meaning |
|--------|-------|---------|
| **DONE** | Green | Tests pass, no gaps, feature is not in TODO state. |
| **TODO** | Yellow | Feature is in TODO lifecycle state or has other Builder action items. |
| **FAIL** | Red | `tests.json` exists with `status: "FAIL"`. Tests are broken. |
| **INFEASIBLE** | Red (critical) | Builder has declared the feature cannot be implemented as specified. Release is blocked. |
| **BLOCKED** | Red | An open SPEC_DISPUTE exists. The Builder cannot proceed until the dispute is resolved. |
| **??** | Gray | No `critic.json` exists for this feature yet. |

The Builder column reflects the **[Implementation Gate](critic-and-cdd-guide.md)** and the feature's
lifecycle state. The precedence order is:
INFEASIBLE > BLOCKED > FAIL > TODO > DONE.

### QA Column

| Status | Color | Meaning |
|--------|-------|---------|
| **CLEAN** | Green | Tests pass and no open discoveries. Verification is complete. |
| **AUTO** | Green | All QA scenarios are `@auto`-tagged. Automated verification covers everything. |
| **TODO** | Yellow | Manual scenarios need verification, or SPEC_UPDATED items need re-verification. |
| **FAIL** | Red | Open BUG entries exist in the discovery sidecar file. |
| **DISPUTED** | Red | Open SPEC_DISPUTE entries exist. The spec itself is contested. |
| **N/A** | Gray | No QA work needed. The feature has no manual scenarios; the Builder verified everything with unit tests. |
| **??** | Gray | No `critic.json` exists for this feature yet. |

The QA column reflects verification status. The precedence order is:
FAIL > DISPUTED > TODO > AUTO > CLEAN > N/A.

### PM Column

| Status | Color | Meaning |
|--------|-------|---------|
| **DONE** | Green | No design work pending. |
| **TODO** | Yellow | Visual spec gaps, stale design artifacts, or SPEC_DISPUTE entries on PM-owned features. |
| **N/A** | Gray | No visual specification, no Figma references, and not a PM-owned feature. |
| **??** | Gray | No `critic.json` exists for this feature yet. |

The PM column is relevant only for features with visual/UI components. Most
backend or infrastructure features will show N/A.

---

## Color Quick Reference

| Color | Statuses | Meaning |
|-------|----------|---------|
| **Green** | DONE, CLEAN, AUTO | Role's work is complete. |
| **Yellow** | TODO | Work is pending but not blocking. |
| **Red** | FAIL, INFEASIBLE, BLOCKED, DISPUTED | Something is broken or blocked. Needs attention. |
| **Gray** | N/A, ?? | Not applicable or not yet analyzed. |

---

## Feature Lifecycle States

Behind the status grid, each feature has a lifecycle state that influences
which role columns light up:

| Lifecycle State | How It Is Set | Effect on Grid |
|-----------------|---------------|----------------|
| **TODO** | Default state, or spec was modified after last status commit | Builder column shows TODO. Feature appears in Active section. |
| **TESTING** | Builder commits `[Ready for Verification]` status tag | QA column shows TODO (manual scenarios) or AUTO (all `@auto`). |
| **COMPLETE** | Builder or QA commits `[Complete]` status tag | All columns show terminal states. Feature moves to Complete section. |

A feature resets back to TODO whenever its spec file is edited. This is
intentional -- the CDD philosophy is that specs and code must stay in sync,
so any spec change triggers re-implementation and re-verification.

---

## Reading the Grid: Common Patterns

### Healthy Feature (Ready for Release)

```
Feature          Architect   Builder   QA      PM
─────────────────────────────────────────────────
Login Flow       DONE        DONE      CLEAN   N/A
```

All green or gray. Nothing to do.

### Feature Needs Implementation

```
Feature          Architect   Builder   QA      PM
─────────────────────────────────────────────────
Search API       DONE        TODO      N/A     N/A
```

Architect has finished the spec. Builder has not started or needs to
continue implementation.

### Feature Has Failing Tests

```
Feature          Architect   Builder   QA      PM
─────────────────────────────────────────────────
Payment Flow     DONE        FAIL      N/A     N/A
```

Red FAIL in the Builder column means `tests.json` reports failures. The
Builder needs to fix the tests before the feature can progress.

### Feature Blocked by Spec Dispute

```
Feature          Architect   Builder   QA      PM
─────────────────────────────────────────────────
Notification UI  TODO        BLOCKED   DISPUTED  TODO
```

A SPEC_DISPUTE is open. The Architect (or PM, if design-related) must
resolve the dispute before the Builder can resume. QA also shows DISPUTED
because verification is suspended.

### Feature Awaiting QA Verification

```
Feature          Architect   Builder   QA      PM
─────────────────────────────────────────────────
Dashboard View   DONE        DONE      TODO    DONE
```

The Builder is finished. QA has manual scenarios to verify.

### Feature with Open Bugs

```
Feature          Architect   Builder   QA      PM
─────────────────────────────────────────────────
Export CSV       DONE        DONE      FAIL    N/A
```

QA found bugs during verification. The Builder needs to fix them (bugs
route to the Builder as action items).

### Spec Needs Work

```
Feature          Architect   Builder   QA      PM
─────────────────────────────────────────────────
New Feature X    TODO        TODO      N/A     N/A
```

The Architect column shows TODO because the Spec Gate failed -- required
sections are missing, scenarios are malformed, or prerequisites are not
declared. Builder is also TODO because it cannot start until the spec is
ready.

---

## Tombstoned Features

When a feature is retired, its tombstone appears in the Active section with
hardcoded values:

```
Feature              Architect   Builder   QA      PM
──────────────────────────────────────────────────────
[Tombstone] Old API  DONE        TODO      N/A     N/A
```

The Builder sees TODO because it needs to delete the associated code. Once
that deletion is committed, the tombstone clears from the grid.

---

## Tips

- **Start with red.** Any red status is a blocker. Fix these first.
- **Check yellow next.** Yellow statuses represent pending work for a
  specific role.
- **Gray is fine.** N/A means no work is needed; ?? means the Critic has
  not analyzed the feature yet (run `/pl-status` to refresh).
- **Use `/pl-status` to refresh.** The grid reflects the last Critic run.
  If you have made changes since, run `/pl-status` to get current data.
- **Follow the lifecycle.** Features flow left to right: Architect writes
  the spec, Builder implements, QA verifies. The grid makes this pipeline
  visible.
