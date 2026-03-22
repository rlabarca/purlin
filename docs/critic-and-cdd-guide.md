# The Critic and CDD

## Overview

Purlin has two complementary coordination systems: the **Critic** and the
**CDD (Continuous Design-Driven) Monitor**. They serve different audiences
and answer different questions:

| System | Audience | Question It Answers |
|--------|----------|---------------------|
| **Critic** | AI agents | "What should I do next?" |
| **CDD Monitor** | Humans (dashboard) | "What is the current state of the project?" |

The Critic analyzes every feature in the project and generates prioritized,
role-specific action items. The CDD Monitor reads the Critic's output and
presents it as a visual dashboard. Neither system replaces the other -- they
work together to keep agents productive and humans informed.

---

## What the Critic Does

The Critic is the project coordination engine. It validates the quality of
every feature file and its implementation, then produces structured action
items for each role (Architect, Builder, QA, PM).

The Critic runs automatically whenever an agent calls `status.sh` -- you
never need to invoke it manually. Its output is written to two places:

- **Per-feature:** `tests/<feature>/critic.json`
- **Aggregate:** `CRITIC_REPORT.md` at the project root

### The Dual-Gate Model

Every feature is validated through two independent gates:

#### Spec Gate (Pre-Implementation)

The Spec Gate checks whether the feature specification is complete and
well-formed. It runs regardless of lifecycle status and catches problems
before any code is written.

What it checks:

- Required sections are present (Overview, Requirements, Scenarios).
- Gherkin scenarios are well-formed (Given/When/Then structure).
- Prerequisite anchor nodes are declared via `> Prerequisite:` metadata.
- Fixture tags reference fixtures that actually exist.

A Spec Gate failure generates an Architect action item -- the spec needs
work before the Builder can implement it.

#### Implementation Gate (Post-Implementation)

The Implementation Gate checks whether the code correctly implements the
spec. It only matters after the Builder has started work.

What it checks:

- `tests.json` exists with `status: "PASS"` and `total > 0`.
- At least one test file exists for the feature.
- Implementation does not violate FORBIDDEN patterns from anchor nodes.
- Builder decisions (deviations, discoveries) are acknowledged by the
  Architect.

An Implementation Gate failure generates a Builder action item -- the code
or tests need fixes.

### Supplementary Audits

Beyond the two gates, the Critic runs additional checks on every pass:

| Audit | What It Checks |
|-------|----------------|
| **User Testing** | Counts open BUG, DISCOVERY, INTENT_DRIFT, and SPEC_DISPUTE entries in discovery sidecar files |
| **Builder Decision** | Scans companion files for unacknowledged `[DEVIATION]`, `[DISCOVERY]`, and `[SPEC_PROPOSAL]` tags |
| **Visual Specification** | Detects `## Visual Specification` sections and flags missing design references |
| **Untracked File** | Checks git status for orphaned files in Architect-owned directories |
| **Regression Scoping** | Validates `[Scope: ...]` trailers on status commits and routes QA effort accordingly |

---

## Role-Specific Action Items

The Critic does not produce a generic to-do list. It routes every finding to
the role responsible for fixing it.

### Priority Levels

| Priority | Meaning | Example |
|----------|---------|---------|
| **CRITICAL** | Release is blocked until resolved | `[INFEASIBLE]` escalation from Builder |
| **HIGH** | Gate failure or open bug | Spec Gate FAIL, open `[BUG]`, unacknowledged `[DEVIATION]` |
| **MEDIUM** | Quality gap or warning | Traceability gap, untracked files |
| **LOW** | Informational | Advisory warnings |

### What Each Role Sees

**Architect** receives:
- Spec gaps (Spec Gate failures)
- INFEASIBLE escalations from the Builder
- Unacknowledged Builder decisions
- Untracked files in Architect-owned directories
- SPEC_DISPUTE entries on Architect-owned features

**Builder** receives:
- Features in TODO lifecycle state (ready to implement)
- Failing automated tests
- Traceability gaps (scenarios without matching tests)
- Open BUG entries from QA discoveries

**QA** receives:
- Features in TESTING lifecycle state (ready to verify)
- SPEC_UPDATED discoveries awaiting re-verification
- Visual verification passes for UI features
- Regression guidance based on Builder's scope declarations

**PM** receives:
- SPEC_DISPUTE entries on PM-owned features or Visual Specification screens
- Stale, missing, or unprocessed design artifacts
- Figma design status advisories

---

## How the Critic Relates to CDD

The two systems are deliberately decoupled:

```
                    writes              reads
  Critic ---------> critic.json ---------> CDD Dashboard
  (agent CLI)       (per-feature)          (human web UI)
```

1. **The Critic runs via CLI.** Agents invoke it through
   `tools/cdd/status.sh`, which calls `tools/critic/run.sh` as a
   prerequisite. It writes `critic.json` files to disk.

2. **CDD reads from disk.** The CDD Dashboard reads the pre-computed
   `role_status` values from those `critic.json` files. CDD never runs
   the Critic itself.

3. **CDD displays what IS.** The dashboard shows the current state of every
   feature across all four role columns (Architect, Builder, QA, PM).

4. **The Critic shows what SHOULD BE DONE.** The `CRITIC_REPORT.md` file
   lists prioritized action items grouped by role.

This separation means the dashboard is always fast (it just reads JSON) and
the Critic can be as thorough as needed without slowing down the UI.

### The Refresh Cycle

Every agent session begins with `status.sh`, which:

1. Runs the Critic to regenerate all `critic.json` files.
2. Aggregates results into `CRITIC_REPORT.md`.
3. Outputs JSON status for the agent to parse.

After an agent commits changes to specs or anchor nodes, running `status.sh`
again refreshes the dashboard and action items for the next agent.

---

## Builder Decision Tags

When the Builder makes implementation choices, it classifies them using
structured tags in companion files (`features/<name>.impl.md`). The Critic
scans these and routes unacknowledged entries to the Architect.

| Tag | Severity | Meaning |
|-----|----------|---------|
| `[CLARIFICATION]` | INFO | Interpreted ambiguous spec language |
| `[AUTONOMOUS]` | WARN | Spec was silent; Builder used judgment |
| `[DEVIATION]` | HIGH | Intentionally diverged from spec |
| `[DISCOVERY]` | HIGH | Found an unstated requirement |
| `[INFEASIBLE]` | CRITICAL | Cannot implement as specified; Builder halts |
| `[SPEC_PROPOSAL]` | HIGH | Proposes a new or modified spec/anchor node |

An entry is considered acknowledged when its line contains the word
"Acknowledged" (case-insensitive). Until then, the Critic keeps flagging it
as a HIGH-priority Architect action item.

---

## User Testing Discoveries

Any agent can record a discovery in a sidecar file
(`features/<name>.discoveries.md`). The Critic counts open entries and
routes them to the responsible role.

| Type | Meaning |
|------|---------|
| `[BUG]` | Behavior contradicts an existing scenario |
| `[DISCOVERY]` | Behavior exists but no scenario covers it |
| `[INTENT_DRIFT]` | Behavior matches the spec literally but misses the actual intent |
| `[SPEC_DISPUTE]` | The user disagrees with a scenario's expected behavior |

Discoveries follow a lifecycle: `OPEN` -> `SPEC_UPDATED` -> `RESOLVED` ->
`PRUNED`. The QA Agent owns lifecycle management (verification, resolution
confirmation, and pruning).

---

## Regression Scoping

When the Builder commits a status tag (`[Ready for Verification]`), it
declares an impact scope that tells QA how much re-testing is needed:

| Scope | Meaning | QA Action |
|-------|---------|-----------|
| `full` | Behavioral change, new scenarios, or API change | Test all manual scenarios |
| `targeted:<names>` | Only specific scenarios affected | Test only the named items |
| `cosmetic` | Non-functional change (formatting, logging) | Skip QA if a prior clean pass exists |
| `dependency-only` | Change propagated by a prerequisite update | Test scenarios touching the changed dependency |

The Critic validates the scope declaration and surfaces regression guidance
as QA action items.

---

## Quick Reference

| What You Want | How To Get It |
|---------------|---------------|
| Run the Critic and refresh status | `tools/cdd/status.sh` (or `/pl-status` in an agent session) |
| View aggregate action items | Read `CRITIC_REPORT.md` at the project root |
| View per-feature Critic results | Read `tests/<feature>/critic.json` |
| See the CDD Dashboard | Start it with `/pl-cdd` and open the printed URL |
| Understand a role's next steps | Check that role's section in `CRITIC_REPORT.md` |
