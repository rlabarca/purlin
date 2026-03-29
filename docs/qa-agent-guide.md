# QA Mode Guide

How to use QA mode to verify features, run regression tests, and build smoke test coverage.

---

## What QA Mode Does

QA mode verifies that implemented features match their specs. It automates what it can, walks you through what it can't, and routes findings back to the right mode for resolution.

QA mode:

- Verifies features by walking through scenarios step by step.
- Classifies scenarios as `@auto` (automatable) or `@manual` (needs human judgment).
- Builds and runs regression test suites.
- Manages smoke tests — the critical-path checks that run first every time.
- Records discoveries (bugs, spec disputes, intent drift) in structured sidecar files.
- Marks features complete when all checks pass.
- Never writes application code. QA writes test scripts, discovery files, and scenario tags.

### Entering QA Mode

From any session:

```
purlin:mode qa
```

Or run a QA skill directly — `purlin:verify`, `purlin:regression`, and `purlin:discovery` all activate QA mode automatically.

At startup, QA mode finds features in TESTING state and presents a verification plan.

---

## The Verification Workflow

Verification has two phases: automated first, then manual.

### Choosing a Strategy

At the start of verification, the agent presents a strategy menu:

- **Targeted** — Verify specific features you name.
- **Full** — Verify everything in TESTING state.
- **Regression-only** — Re-run regression suites without full verification.

### Phase A — Automated

The agent works through these steps without needing you:

1. **Credit Engineer work.** Features that only have unit tests (no QA scenarios) are auto-credited as complete.

2. **Smoke gate.** If you've defined smoke-tier features (see [Smoke Testing](#smoke-testing) below), those scenarios run first. If any fail, the agent halts and asks whether to stop or continue.

3. **Run `@auto` scenarios.** Scenarios tagged `@auto` from prior sessions already have regression tests. The agent runs them automatically. Suites with valid passing results that haven't gone stale are skipped.

4. **Classify untagged scenarios.** For each new scenario PM mode wrote:
   - If it can be automated (deterministic assertions, no subjective judgment), the agent proposes an approach and asks you to confirm.
   - If it can't, the agent tags it `@manual` and moves it to the manual checklist.
   - After this step, every scenario is tagged.

5. **Auto-fix loop.** When automated scenarios fail, the agent can fix them without leaving QA mode. An internal mode switch gives Engineer write access to fix the failing code, then QA re-verifies. This repeats until clean or a retry limit is reached.

6. **Visual smoke check.** For features with visual specs, runs a quick Playwright check.

**Phase A Checkpoint:** Before any manual work, the agent finalizes and commits status tags for every feature that passed automated verification.

### Phase B — Manual

The agent assembles a numbered checklist of remaining items. Each item has a **Do:** line (what to set up and perform) and a **Verify:** line (what should happen).

You respond with:

- `all pass` — Everything passed.
- `F3, F7` — Items 3 and 7 failed.
- `help 5` — Walk through item 5 in detail.
- `DISPUTE 4` — You disagree with item 4's expected behavior.

After processing, the agent records discoveries for failures, marks clean features as complete, and presents a summary.

---

## Discoveries

When verification finds a problem, QA mode records a structured discovery in the feature's sidecar file (`features/<name>.discoveries.md`).

### Four Types

| Type | Meaning | Routed To |
|------|---------|-----------|
| `[BUG]` | Behavior contradicts an existing scenario. | Engineer mode |
| `[DISCOVERY]` | Behavior exists but no scenario covers it. | PM mode |
| `[INTENT_DRIFT]` | Matches the spec literally but misses the intent. | PM mode |
| `[SPEC_DISPUTE]` | You disagree with the scenario's expected behavior. | PM mode |

### Lifecycle

`OPEN` → `SPEC_UPDATED` → `RESOLVED` → `PRUNED`

- **OPEN** — Just recorded.
- **SPEC_UPDATED** — PM updated the spec to address it.
- **RESOLVED** — Fix verified.
- **PRUNED** — Entry removed after resolution.

Record a discovery at any time:

```
purlin:discovery feature-name
```

---

## Regression Testing

Regression tests catch things that used to work but broke after a change. QA mode manages the full lifecycle.

### How It Works

**1. Author scenarios** — QA mode reads the feature spec and writes regression test files (`tests/qa/scenarios/<feature>.json`). Each test has assertions ranked by confidence:

| Tier | What It Checks |
|------|----------------|
| Tier 1 | Keyword presence (low confidence). |
| Tier 2 | Specific values — file names, identifiers (medium). |
| Tier 3 | State verification — checked the actual output (high). |

Suites with too many Tier 1 assertions are flagged as shallow.

**2. Run the suite** — The agent composes a command for you to run in a separate terminal:

```bash
./tests/qa/run_all.sh
```

Results land in `tests/<feature>/regression.json`.

**3. Evaluate results** — QA mode reads the results, creates `[BUG]` discoveries for failures, and reports the assertion quality distribution.

### Commands

| Command | What It Does |
|---------|--------------|
| `purlin:regression author` | Write regression test files from specs. |
| `purlin:regression run` | Generate the command to run the suite. |
| `purlin:regression evaluate` | Process results and create discoveries for failures. |

### Staleness

A regression result goes stale when: the feature's source code changed since the result was written, the test infrastructure changed, or the prior run failed. Stale features are prioritized for re-testing and can't be marked complete.

---

## Smoke Testing

Smoke tests are your critical-path checks — the features that, if broken, mean the app is unusable. They run first in every QA verification pass and block everything else if they fail.

### Setting Up Smoke Tests

Promote a feature to the smoke tier:

```
purlin:smoke feature-name
```

This adds the feature to the test priority table and optionally creates a simplified smoke regression (1-3 scenarios, under 30 seconds).

### How Smoke Tests Fit into Verification

During Phase A, Step 2, QA mode runs all smoke-tier scenarios before anything else. If a smoke test fails:

- QA halts and reports the failure.
- You decide whether to stop (fix first) or continue with the rest.

This catches critical breakage early, before you spend time verifying less important features.

### Guidelines

- Every project should have 5-15 smoke features.
- Smoke tests should cover the features your users would notice first if broken.
- QA mode decides what qualifies as smoke — it's a test design decision.

---

## Completing Features

```
purlin:complete feature-name
```

QA mode marks a feature complete when all gates pass:

1. Feature is in TESTING state.
2. All QA scenarios passed.
3. Zero open discoveries.
4. Not blocked by a pending delivery plan phase.

The completion commit includes a `[Verified]` tag.

---

## Day-to-Day Commands

| Command | What It Does |
|---------|--------------|
| `purlin:verify [name] [--auto-fix]` | Run the verification workflow. `--auto-fix` enables the auto-fix iteration loop. |
| `purlin:complete <name>` | Mark a verified feature as complete. |
| `purlin:discovery [name]` | Record a structured finding. |
| `purlin:regression <cmd>` | Author, run, or evaluate regression suites. |
| `purlin:smoke <feature>` | Promote a feature to the smoke tier. |
| `purlin:qa-report` | Summary of discoveries and verification status. |
| `purlin:fixture` | Manage test fixtures — create, list, verify, or push to remote. |
| `purlin:web-test [name]` | Playwright visual verification (cross-mode from QA). |
| `purlin:unit-test [name]` | Run unit tests (cross-mode from QA). |
| `purlin:server` | Start/stop dev server for web testing (cross-mode from QA). |
| `purlin:status` | Check what needs verification. |
| `purlin:find <topic>` | Search specs for a topic. |
| `purlin:help` | Full command list for QA mode. |
