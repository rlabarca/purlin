# Purlin Testing Workflow Guide

How to take a feature from idea to verified, automated regression coverage.

> **Implementation status:** The auto-first protocol, `@auto`/`@manual` scenario
> classification, and two-line QA dashboard display are specified and partially
> implemented. The core mechanisms (AUTO status, `@auto` parsing, harness runner,
> fixture tools, two-line display) are working. The `@manual` tag parsing and
> the untagged-scenario classification flow (Step 3) are specified but pending
> Builder implementation. Until then, QA classifies scenarios via
> `/pl-regression-author` and manual tagging.

---

## Overview

Four agents work in sequence. You launch them one at a time. Each agent discovers its own work from the previous agent's commits -- you don't coordinate between them.

```
PM --> Architect --> Builder --> QA
 ^                               |
 +-------- discoveries ----------+
```

**PM** writes the spec. **Architect** validates it. **Builder** implements it. **QA** verifies it and automates what it can. Discoveries (bugs, disputes) flow back upstream.

---

## 1. Write the Spec

### With Figma (PM Agent)

Launch a PM session. Give it a Figma URL.

The PM reads the design via Figma MCP and produces a complete feature spec:

- **Requirements** -- behavioral rules
- **Visual Specification** -- Token Map (Figma tokens mapped to your project's design tokens), screen-by-screen checklists
- **QA Scenarios** -- verification steps (written untagged -- QA classifies them later)
- **Unit Tests** -- what the Builder will automate

The PM also generates `brief.json` -- structured design data the Builder reads instead of needing Figma access.

**Your role:** Provide the Figma URL, answer clarifying questions, approve the spec.

### Without Figma (Architect Agent)

Launch an Architect session. Describe the feature.

The Architect writes the spec directly: requirements, scenarios, prerequisites. No Visual Specification unless you provide mockups.

**Your role:** Describe what you want, answer questions, approve.

---

## 2. Validate and Classify

### Architect Agent

The Architect runs automatically after specs exist. It:

1. **Reads every spec** and checks for gaps -- missing scenarios, broken prerequisite links, ambiguous requirements.
2. **Assigns QA priority tiers** in `QA_OVERRIDES.md`:
   - `smoke` -- core functionality. If broken, the app is unusable. Verified first.
   - `standard` -- important but not app-breaking. Default.
   - `full-only` -- polish and edge cases. Verified last or skipped in quick passes.
3. **Commits and regenerates [the Critic](critic-and-cdd-guide.md) report** so the Builder knows what to build.

**Your role:** Approve the work plan. Answer architectural questions.

---

## 3. Build and Test

### Builder Agent

Launch: `./pl-run-builder.sh`

The Builder discovers TODO features from the Critic report and for each one:

1. **Implements** -- application code, scripts, config files.
2. **Writes unit tests** -- tested against a 6-point quality rubric. No grep-the-source-code shortcuts. Results land in `tests/<feature>/tests.json`.
3. **Verifies visual specs** -- for features with a Visual Specification section, the Builder verifies ALL visual checklist items. Web test features (`> Web Test:` metadata) are verified via Playwright (`/pl-web-test`). Non-web features are verified by inspecting the running application or output. Visual verification is Builder-owned -- QA does not re-verify visual items.
4. **Commits a status tag:**
   - **Unit Tests only** (no QA Scenarios in the spec): Builder marks `[Complete]`. Done. QA never sees this feature.
   - **Has QA Scenarios**: Builder marks `[Ready for Verification]`. QA picks it up next.

**Your role:** Approve the work plan. Answer implementation questions. Run external commands when asked.

---

## 4. Verify

### QA Agent

Launch a QA session. QA finds all `[Ready for Verification]` features automatically.

### The Auto-First Protocol

QA's goal is to automate as much as possible on the first pass, so future sessions run faster. It works through seven steps:

#### Step 1 -- Credit Builder Work

Features the Builder already completed (unit-tests-only, cosmetic changes) are auto-credited. No human time.

#### Step 2 -- Smoke Gate

If a tier table exists in `QA_OVERRIDES.md`, QA identifies smoke-tier features first and runs ALL their scenarios -- `@auto`, untagged, and `@manual` alike. This is a fast check of the most critical features.

If any smoke scenario **fails**, QA halts and asks:
```
Smoke failure: policy_critic -- "Spec Gate validates prerequisites"
Fix before continuing full verification? [yes to stop / no to continue]
```

This catches catastrophic breakage before you spend time on the full batch. If there's no tier table, this step is skipped.

#### Step 3 -- Run Existing Automations

Scenarios tagged `@auto` from a prior QA session already have regression JSON. QA invokes the harness runner. No human involvement. Smoke-tier `@auto` scenarios already ran in Step 2 -- they're skipped here.

#### Step 4 -- Classify New Scenarios

This is the key step. For every QA Scenario that has **no tag** yet (Architect/PM wrote it, QA hasn't seen it):

1. QA evaluates whether the scenario can be automated: Are the assertions deterministic? No physical hardware? No subjective judgment?

2. **If automatable**, QA proposes the approach:
   ```
   Scenario "Dashboard shows correct feature count" looks automatable.

   Proposed: web_test harness, no fixtures needed, 2 assertions (Tier 2).
   Author regression JSON and add @auto? [yes / no]
   ```

3. **You say yes**: QA authors the regression JSON via `/pl-regression-author`, runs it via the harness runner, and adds `@auto` to the scenario heading. Automated for every future session.

4. **You say no** (or it's not feasible): QA adds `@manual` to the scenario heading. It enters the manual verification path. QA never asks about this scenario again.

**After this step, every scenario is tagged.** Nothing stays untagged. Smoke-tier untagged scenarios already classified in Step 2 -- skipped here.

#### Step 5 -- LLM Delegation

Some scenarios need Claude to analyze output (complex reasoning, multi-step evaluation). QA composes the exact command and asks you to run it in a separate terminal.

#### Step 6 -- Standard and Full-Only Manual

QA presents remaining `@manual` scenarios: standard-tier first, then full-only.

#### Step 7 -- Full Manual Pass

`@manual` scenarios walked through step-by-step with grouped batches for efficiency.

### What You Do During Verification

- Perform the steps QA describes and say PASS or FAIL
- Copy-paste and run commands QA prints
- Say "yes" or "no" when QA proposes automation (Step 4)

### After Verification

- **Zero discoveries**: QA marks the feature `[Complete] [Verified]`.
- **Bugs found**: QA records them as discoveries and routes to Builder (code bugs) or Architect (spec issues).

---

## 5. Set Up Fixtures

### When QA Needs Controlled State

Some scenarios need a specific project state to test against -- particular config values, git history, branch structures. Purlin uses **fixture tags**: immutable git tags in a dedicated repo, each representing a snapshot of project state.

When QA encounters a scenario that needs fixtures during regression authoring, it checks for a fixture repo. If none exists:

```
This feature needs controlled test state, but no fixture repo exists.

Options:
  1. Create a local fixture repo (at .purlin/runtime/fixture-repo)
  2. Use a remote repo (provide the git URL)
  3. Skip fixtures for now (use inline setup instead)

Choice? [1 / 2 <url> / 3]
```

- **Option 1** -- QA creates a local bare git repo immediately. Good for most projects.
- **Option 2** -- You provide any git URL (GitHub, GitLab, Bitbucket, local bare repo). QA configures it. Good for team-shared fixtures.
- **Option 3** -- QA uses inline setup commands in the regression JSON. Good for simple state.

### How Fixture Tags Work

```
.purlin/runtime/fixture-repo/        <-- bare git repo
  tags:
    main/cdd_branch_collab/sync-ahead
    main/cdd_branch_collab/sync-diverged
    main/cdd_startup/expert-mode
```

**Naming:** `main/<feature-name>/<scenario-slug>`

Each tag is an immutable snapshot. The harness runner checks out the tag into a temp directory, runs the test against that state, and cleans up.

### Who Creates Fixture Tags

**QA** creates most fixtures directly during regression authoring (`fixture add-tag`). For each scenario, QA constructs the needed project state in a temp directory and tags it.

**Builder** (launched with `./pl-run-builder.sh -qa`) handles complex fixtures that need application-level knowledge -- elaborate build states, database migrations, multi-branch git histories. QA records these as recommendations in `tests/qa/fixture_recommendations.md`.

### Fixture Lifecycle

- Tags are **immutable** -- once created, they never change.
- When a feature is retired, `fixture prune` identifies orphan tags for cleanup.
- A setup script can regenerate all tags deterministically from project files, so the fixture repo is derived (not precious state).

---

## 6. Build Test Infrastructure

Test Infrastructure features (fixture setup, regression harness, test tooling) appear alongside all other features in the Builder's TODO list. The Builder discovers and implements them through the normal Critic-driven workflow -- no special mode or flag needed.

For complex fixtures that need application-level knowledge, QA records recommendations in `tests/qa/fixture_recommendations.md` for the Builder to pick up.

---

## 7. Run Regression

### Executing the Suite

After QA has authored regression scenarios, you run them yourself in a separate terminal:

```bash
./tests/qa/run_all.sh
```

This discovers all scenario JSON files in `tests/qa/scenarios/`, runs each one via the harness runner, continues past failures, and prints a summary:

```
Regression Summary:
  PASS  instruction_audit (5/5)
  FAIL  branch_collab (3/5)
  PASS  cdd_startup (8/8)

Total: 16/18 passed (3 features, 1 failure)
```

### Processing Results

Launch QA after the run completes. QA reads the results, creates BUG discoveries for failures, and reports assertion quality:

```
Tier Distribution: T1=3  T2=12  T3=6  (untagged=0)
```

- **Tier 1** -- keyword presence ("found the word `error`"). Vulnerable to false positives.
- **Tier 2** -- specific finding (exact file name, defect identifier). Reliable.
- **Tier 3** -- state verification (checked the agent's output artifact). Most robust.

Suites with >50% Tier 1 assertions get flagged as `[SHALLOW]`.

### The Feedback Loop

```
QA authors scenarios --> you run tests --> failures?
                                            |
                              yes: launch Builder to fix code
                                    then re-run tests
                              no:  done, ship it
```

If a test failure is actually a broken test (not a code bug), Builder flags it for QA with `Action Required: QA`. QA fixes the scenario JSON.

---

## Quick Reference

### Agent Sequence by Situation

| You want to... | Launch sequence |
|----------------|-----------------|
| Build a new feature from Figma | PM, Architect, Builder, QA |
| Build a feature without design | Architect, Builder, QA |
| Fix bugs found during QA | Builder, then QA |
| Resolve a spec dispute | Architect, then Builder, then QA |
| Set up regression coverage | QA (via `/pl-regression-author`) |
| Create complex test fixtures | Builder |
| Ship a release | Architect with `/pl-release-run` |

### Scenario Tag Lifecycle

```
Architect/PM writes scenario
        |
   (untagged)
        |
  QA first encounter
        |
  "Can this be automated?"
       / \
     yes   no
      |     |
   @auto  @manual
```

- **Untagged** -- not yet seen by QA. Treated as manual for planning.
- **@auto** -- QA authored regression JSON. Harness runner executes it automatically.
- **@manual** -- requires human judgment. QA never re-proposes automation.

Tags are QA outputs. Architects and PMs write scenarios without tags.

### Key Commands

| Command | Who | What it does |
|---------|-----|-------------|
| `./pl-run-builder.sh` | Builder | Implementation session |
| `./tests/qa/run_all.sh` | You (terminal) | Run full regression suite |
| `/pl-verify` | QA | Batched verification workflow |
| `/pl-regression-author` | QA | Author regression scenario JSON files |
| `/pl-regression-run` | QA | Execute existing regression scenarios |
| `/pl-regression-evaluate` | QA | Process results, create BUG discoveries |
| `/pl-web-test` | Builder | Visual verification via Playwright |
| `/pl-status` | Any agent | Show Critic report and feature status |
