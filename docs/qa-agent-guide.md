# QA Agent Guide

A practical guide for using the QA agent in Purlin.

---

## 1. Overview

The QA agent is Purlin's verification and feedback agent. It guides you through manual verification of implemented features, automates what it can, and routes findings back to the Builder (bugs) or Architect (spec issues).

The QA agent:

- **Verifies features** by walking you through scenarios step by step.
- **Classifies scenarios** as `@auto` (automatable) or `@manual` (requires human judgment).
- **Authors regression tests** that run automatically in future sessions.
- **Records discoveries** (bugs, spec disputes, intent drift) in structured sidecar files.
- **Marks features complete** after clean verification with zero open discoveries.
- **Never writes application code.** QA writes verification scripts, discovery files, and scenario tags -- not implementation.

QA discovers its own work. At startup, it reads [the Critic](critic-and-cdd-guide.md) report, finds features in TESTING state, and presents a verification plan.

---

## 2. Getting Started

### Launching a QA Session

```bash
./pl-run-qa.sh
```

### What Happens at Startup

QA prints a command table, then checks its configuration:

- **Find Work + Auto Start**: QA runs through automated verification (Phase A) fully without prompting, then presents manual items.
- **Find Work only**: QA proposes a verification plan and waits for your approval.
- **Find Work disabled**: QA waits for your direct instruction.

---

## 3. The Verification Workflow

QA verification has two phases: Phase A (automated, runs first) and Phase B (manual, presented after).

### Phase A -- Automated (8 Steps)

**Step 1 -- Credit Builder Work.** Features the Builder already completed (unit-tests-only, no QA scenarios) are auto-credited. No human time needed.

**Step 2 -- Smoke Gate.** If test priority tiers are configured in `QA_OVERRIDES.md`, QA runs all smoke-tier scenarios first. If any fail, QA halts and asks whether to stop or continue.

**Step 3 -- Run @auto Scenarios.** Scenarios tagged `@auto` from prior sessions already have regression JSON. QA invokes the harness runner automatically.

**Step 4 -- Classify Untagged Scenarios.** For each QA scenario with no tag yet:
- QA evaluates whether it can be automated (deterministic assertions, no hardware, no subjective judgment).
- If automatable: QA proposes the approach and asks you to confirm. On approval, it authors regression JSON, runs it, and tags the scenario `@auto`.
- If not automatable: QA tags it `@manual` and moves it to the manual checklist.
- After this step, every scenario is tagged.

**Step 5 -- Visual Smoke.** For features with visual specifications, QA runs a quick Playwright check (web features) or asks for a screenshot (non-web features).

**Step 6 -- LLM Delegation.** For scenarios needing Claude to analyze output, QA composes a command for you to run externally.

**Step 7 -- Standard and Full-Only Manual.** Remaining `@manual` scenarios are verified: standard-tier first, then full-only.

**Step 8 -- Full Manual Pass.** Visual checklists grouped by screen; `@manual` scenarios walked through step-by-step.

### Phase A Summary

After automated steps complete, QA prints a bridging summary:

```
--- Phase A Complete ---
Auto-passed:     3 features (builder-verified)
Smoke gate:      ran 5 smoke scenarios
@auto executed:  12 scenarios -- 11 passed, 1 failed
Classified:      4 scenarios (2 -> @auto, 2 -> @manual)

Remaining for manual verification: 6 items across 2 features.
```

### Phase B -- Manual Verification

QA assembles a numbered checklist of all remaining items across features. Each item has a **Do:** line (setup and action) and a **Verify:** line (expected outcome).

You respond with:
- `all pass` -- Everything passed.
- `F3, F7` -- Items 3 and 7 failed.
- `help 5` -- Walk through item 5 step by step.
- `detail 5` -- Show raw Gherkin or full visual context.
- `DISPUTE 4` -- Trigger a SPEC_DISPUTE for item 4.

After processing results, QA records discoveries for failures, marks clean features as complete, and presents a batch summary.

---

## 4. Discoveries

When verification reveals a problem, QA records a structured discovery in the feature's sidecar file (`features/<name>.discoveries.md`).

### Four Discovery Types

| Type | Meaning | Routes To |
|------|---------|-----------|
| `[BUG]` | Behavior contradicts an existing scenario | Builder |
| `[DISCOVERY]` | Behavior exists but no scenario covers it | Architect |
| `[INTENT_DRIFT]` | Behavior matches the spec literally but misses the actual intent | Architect |
| `[SPEC_DISPUTE]` | You disagree with a scenario's expected behavior | Architect/PM |

### Discovery Lifecycle

`OPEN` --> `SPEC_UPDATED` --> `RESOLVED` --> `PRUNED`

- **OPEN**: Just recorded.
- **SPEC_UPDATED**: Architect or PM updated the spec to address it.
- **RESOLVED**: Fix complete and verified.
- **PRUNED**: QA removes the entry and adds a one-liner to the companion file.

### Recording a Discovery

```
/pl-discovery feature-name
```

QA asks you to describe what you observed, classifies the finding, writes it to the sidecar file, and commits. SPEC_DISPUTE entries suspend the affected scenario until resolved.

---

## 5. Scenario Classification

Scenarios start untagged (written by the Architect or PM). QA classifies them on first encounter:

- **`@auto`** -- QA authored regression JSON for this scenario. The harness runner executes it automatically in future sessions.
- **`@manual`** -- Requires human judgment. QA never re-proposes automation for these.

Once tagged, a scenario stays tagged. The classification decision is final.

---

## 6. Regression Testing

Regression testing uses three separate commands, each handling one phase of the workflow:

### Authoring (`/pl-regression-author`)

When features need regression scenario files, QA reads the spec, evaluates fixture needs, and writes scenario JSON to `tests/qa/scenarios/<feature>.json`. Each scenario includes assertions at three confidence tiers:

| Tier | Confidence | Example |
|------|-----------|---------|
| 1 | Low | Keyword presence (e.g., "found the word `error`") |
| 2 | Medium | Specific finding (exact file name or defect identifier) |
| 3 | High | State verification (checked the agent's output artifact) |

Suites with over 50% Tier 1 assertions are flagged as `[SHALLOW]`.

### Running (`/pl-regression-run`)

When regression scenarios exist but results are stale or failing, QA composes a copy-pasteable command for you to run:

```bash
./tests/qa/run_all.sh
```

The harness runner writes results to `tests/<feature>/regression.json` (separate from the Builder's `tests.json`).

### Evaluating (`/pl-regression-evaluate`)

After tests run, QA reads the `regression.json` results, creates BUG discoveries for failures, and reports the assertion tier distribution.

---

## 7. Completing Features

```
/pl-complete feature-name
```

QA marks a feature complete when all gates pass:

1. Feature is in TESTING state.
2. All QA scenarios passed (current or prior session).
3. Zero OPEN or SPEC_UPDATED discoveries.
4. Feature is not gated by a pending delivery plan phase.

The completion commit includes a `[Verified]` tag that distinguishes QA completions from Builder auto-completions.

---

## 8. Fixtures

Some scenarios need controlled project state to test against. Purlin uses [fixture tags](testing-workflow-guide.md) -- immutable git tags in a dedicated repo.

When QA encounters a scenario that needs fixtures during regression authoring, it checks for a fixture repo. If none exists, it offers three options:

1. **Local repo** -- Created at `.purlin/runtime/fixture-repo`. Good for most projects.
2. **Remote repo** -- You provide a git URL. Good for team-shared fixtures.
3. **Inline setup** -- Uses shell commands in the regression JSON. Good for simple state.

For complex fixtures that need application-level knowledge, QA records recommendations in `tests/qa/fixture_recommendations.md` for the Builder to handle.

---

## 9. Day-to-Day Tips

### Checking What Needs Verification

```
/pl-status
```

Features with QA=TODO are waiting for verification. Features with QA=FAIL have open bugs.

### Getting a QA Status Report

```
/pl-qa-report
```

Shows all TESTING features, open discoveries, completion blockers, and an effort estimate.

### Visual Verification

For web features, QA uses `/pl-web-test` via Playwright. For non-web features, QA asks you for screenshots and analyzes them against the visual specification checklist.

### When You Disagree with a Spec

Say `DISPUTE` followed by the item number during Phase B verification. QA records a SPEC_DISPUTE discovery and suspends the scenario. The Architect (or PM for design issues) must resolve the dispute before verification can continue.

### Partial Verification

If you need to stop mid-session, respond with `stop` or `partial` during Phase B. QA marks passing features complete and leaves the rest in TESTING for next time.

### Session Cleanup

Before ending a session, QA runs a mandatory workspace cleanup. It resolves all uncommitted changes -- committing `regression.json` results, QA scenario updates, and discovery sidecar files, while restoring any Builder-owned `tests.json` files that were accidentally modified. This ensures a clean git state for the next agent session.

---

## 10. Command Reference

| Command | Description |
|---------|-------------|
| `/pl-verify [name]` | Run interactive verification (scoped or batch mode). |
| `/pl-complete <name>` | Mark a verified feature as complete. |
| `/pl-discovery [name]` | Record a structured discovery (BUG, DISCOVERY, INTENT_DRIFT, SPEC_DISPUTE). |
| `/pl-regression-author` | Author regression scenario JSON files. |
| `/pl-regression-run` | Execute existing regression scenarios. |
| `/pl-regression-evaluate` | Process regression results, create BUG discoveries. |
| `/pl-web-test [name]` | Run Playwright visual verification. |
| `/pl-qa-report` | Summary of open discoveries and QA status. |
| `/pl-status` | Check CDD status and action items. |
| `/pl-find <topic>` | Search specs for where a topic is discussed. |
| `/pl-fixture` | [Test fixture](testing-workflow-guide.md) convention and workflow. |
| `/pl-server` | Dev server lifecycle management. |
| `/pl-cdd` | Start, stop, or restart the [CDD Dashboard](status-grid-guide.md). |
| `/pl-override-edit` | Edit `QA_OVERRIDES.md`. |
| `/pl-help` | Display the full command list. |
| `/pl-resume [save\|role]` | Save or restore session state. |
| `/pl-purlin-issue` | Report a Purlin framework issue. |
| `/pl-update-purlin` | Update the Purlin submodule. |
