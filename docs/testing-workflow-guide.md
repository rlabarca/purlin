# Testing Workflow Guide

The complete journey from idea to verified, regression-tested feature.

---

## The Big Picture

Purlin uses one agent with three roles, working in sequence. Each role discovers its own work from the previous role's commits — you don't coordinate between them.

```
PM → Engineer → QA
↑                 |
+-- discoveries --+
```

**PM** writes the spec. **Engineer** implements it. **QA** verifies it and automates what it can. When verification reveals problems, discoveries flow back to PM or Engineer for resolution.

---

## Step 1: Write the Spec (PM)

Create a spec:

```
purlin:spec dashboard-overview
```

PM mode asks questions about scope, edge cases, behavior, and constraints, then produces a feature spec with:

- **Requirements** — behavioral rules.
- **QA Scenarios** — verification steps (written untagged — QA classifies them later).
- **Unit Tests** — what Engineer mode will automate.
- **Visual Specification** — token maps and checklists (when designs exist).

### With Figma Designs

First, import the design as an invariant (one-time setup):

```
purlin:invariant add-figma https://www.figma.com/design/ABC123/My-App
```

Then reference it during spec authoring — `purlin:spec` reads the Figma design via MCP, extracts components and tokens, and generates `brief.json` (structured design data that Engineer mode reads instead of needing Figma access).

### Without Designs

Describe the feature in plain language. PM mode asks clarifying questions and builds the spec from your answers.

---

## Step 2: Build and Test (Engineer)

Build the feature:

```
purlin:build dashboard-overview
```

Engineer mode reads the spec and:

1. **Implements** — writes application code, scripts, and config files.
2. **Writes unit tests** — tested against a quality rubric (tests must fail when the implementation is removed, assert specific values, use realistic inputs).
3. **Verifies visual specs** — for web features, checks every visual checklist item via Playwright.
4. **Commits a status tag:**
   - `[Complete]` if only unit tests exist (QA never sees this feature).
   - `[Ready for Verification]` if QA scenarios exist (QA picks it up next).

When the engineer discovers something the spec didn't anticipate, it records the decision in a companion file so PM can review it later.

---

## Step 3: Verify (QA)

Verify the feature:

```
purlin:verify                        # Verify all TESTING features
purlin:verify dashboard-overview     # Verify a specific feature
purlin:verify --auto-fix             # Enable auto-fix iteration loop
```

QA mode finds all features marked `[Ready for Verification]` and runs through them.

### Automated Phase

1. Credits features Engineer mode already completed (unit-tests-only).
2. Runs smoke tests first (if configured) — catches critical breakage early.
3. Executes `@auto` regression scenarios from prior sessions.
4. Classifies new scenarios: proposes automation where possible, tags the rest `@manual`.
5. Commits status tags for everything that passed automated checks.

### Manual Phase

Presents a numbered checklist of remaining `@manual` items. You perform each step and report pass/fail. Failures become discoveries routed to the appropriate mode.

### After Verification

- **Zero discoveries** — QA mode marks the feature `[Complete] [Verified]`.
- **Bugs found** — Recorded as `[BUG]` discoveries, routed to Engineer mode.
- **Spec issues** — Recorded as `[DISCOVERY]`, `[INTENT_DRIFT]`, or `[SPEC_DISPUTE]`, routed to PM mode.

---

## How Regression Testing Works

Regression tests ensure that features keep working after future changes.

### Who Does What

| Role | Responsibility |
|------|----------------|
| **PM** | Writes QA scenarios in the spec (untagged). |
| **Engineer** | Writes and maintains unit tests. Results in `tests.json`. |
| **QA** | Authors regression scenario files, classifies scenarios, evaluates results. Results in `regression.json`. |

### The Regression Cycle

1. **QA mode authors regression files** from the spec's QA scenarios (`purlin:regression author`). Regression scenario files (`tests/qa/scenarios/*.json`) are write-guard protected — they can only be written through `purlin:regression` or `purlin:verify`, not manually.
2. **You run the suite** in a separate terminal (`./tests/qa/run_all.sh`).
3. **QA mode evaluates results** (`purlin:regression evaluate`) — creates bug reports for failures, reports test quality.

### When Results Go Stale

A regression result becomes stale when the feature's source code changes, the test infrastructure changes, or the prior run failed. Stale features are prioritized for re-testing and can't be marked complete until they pass again.

---

## How Smoke Testing Works

Smoke tests are the critical-path checks that run before everything else.

### Who Does What

| Role | Responsibility |
|------|----------------|
| **PM** | Writes the scenarios that become smoke tests. |
| **QA** | Decides which features are smoke-tier (`purlin:regression`), authors simplified smoke regressions. |
| **Engineer** | Fixes smoke test failures (they're blocking). |

### How It Fits In

During QA verification, smoke-tier features run first (Phase A, Step 2). If any fail, QA mode halts and asks whether to stop or continue. This catches catastrophic breakage before you spend time on less critical features.

### Setting It Up

```
purlin:regression promote config-layering  # Promote a feature to smoke tier
purlin:regression suggest                 # Get suggestions for which features to promote
```

QA mode adds the feature to the smoke tier and optionally creates a quick regression (1-3 scenarios, under 30 seconds).

Every project should have 5-15 smoke features covering the functionality users would notice first if broken.

---

## Fixtures

Some test scenarios need controlled project state — specific config values, git history, or branch structures. Purlin uses **fixture tags**: immutable git tags in a dedicated repo, each representing a snapshot of project state.

PMs declare fixture tags in specs (`### 2.x Integration Test Fixture Tags`). Engineers create the fixture repo and tags during `purlin:build`. QA references tags in regression scenario JSON. The harness runner checks out tags at test time and cleans up after each scenario.

**Fixture repos** live at `.purlin/runtime/fixture-repo` (local, gitignored) or at a URL configured via `fixture_repo_url` in `.purlin/config.json` (team-shared). For simple state (one file, one env var), use inline `setup_commands` in scenario JSON instead.

Tags are immutable once created. The fixture repo is derived (not precious state) and can be regenerated from project files.

---

## Quick Reference

### By Situation

| You want to... | What to do |
|----------------|------------|
| Build a new feature from Figma | `purlin:spec` → `purlin:build` → `purlin:verify` |
| Build a feature without designs | `purlin:spec` → `purlin:build` → `purlin:verify` |
| Fix bugs found during QA | `purlin:build`, then `purlin:verify` |
| Resolve a spec dispute | `purlin:spec`, then `purlin:build`, then `purlin:verify` |
| Set up regression coverage | `purlin:regression author` |
| Add smoke tests | `purlin:regression promote feature-name` |
| Run the full regression suite | Terminal: `./tests/qa/run_all.sh` |

### Key Commands

| Command | Mode | What It Does |
|---------|------|--------------|
| `purlin:spec <topic>` | PM | Create or update a feature spec. |
| `purlin:build [name]` | Engineer | Implement a feature from its spec. |
| `purlin:verify [name]` | QA | Run the verification workflow. |
| `purlin:regression <cmd>` | QA | Author, run, evaluate regressions, and manage smoke tier (`promote`, `suggest`). |
| `purlin:status` | Everyone | See what needs doing. |
