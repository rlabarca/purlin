# Purlin Testing Workflow Guide

A step-by-step guide to the full testing lifecycle: from design through verification to automated regression.

---

## The Big Picture

Purlin uses four specialized agents that work in sequence. Each agent self-discovers work from the previous agent's commits via the Critic -- no manual coordination needed.

```
PM --> Architect --> Builder --> QA
 ^                               |
 +-------- discoveries ----------+
```

You launch agents one at a time. Each one finds its own work, does it, commits, and tells you what to do next.

---

## Phase 1: Design (PM Agent)

**When:** You have a Figma design or a feature idea.

**Launch:** Start a Claude session with PM instructions loaded.

### What the PM does:

1. **Spec authoring** -- Creates or refines `features/<name>.md` with:
   - Requirements (what the feature does)
   - Visual Specification (what it looks like -- Token Map, checklists)
   - QA Scenarios (how to verify it)
   - Unit Tests (what the Builder automates)

2. **Design ingestion** (if Figma is available) -- `/pl-design-ingest`:
   - Reads Figma designs via MCP
   - Generates Token Map (Figma tokens to project tokens)
   - Creates `brief.json` with structured design data
   - Populates Visual Specification checklists

3. **Output:** A complete feature spec at `[TODO]` status.

### What you do:

- Provide Figma URLs or describe the feature
- Answer clarifying questions
- Approve the spec

---

## Phase 2: Validation (Architect Agent)

**When:** PM has committed feature specs.

**Launch:** Start a Claude session with Architect instructions loaded.

### What the Architect does:

1. **Gap analysis** -- Reads specs, checks for missing scenarios, broken prerequisites, structural issues.
2. **Tier classification** -- Assigns each feature a QA priority tier (`smoke`, `standard`, `full-only`) in `QA_OVERRIDES.md`. This controls the order QA verifies things.
3. **Anchor node maintenance** -- Updates architectural constraints if needed.
4. **Commits and runs the Critic** -- Regenerates status for the next agent.

### What you do:

- Approve the work plan
- Answer architectural questions

---

## Phase 3: Implementation (Builder Agent)

**When:** Specs are validated (Architect status = DONE).

**Launch:** `./pl-run-builder.sh`

### What the Builder does:

1. **Reads specs** -- Discovers TODO features from the Critic report.
2. **Implements** -- Writes application code, scripts, and config.
3. **Unit tests** (`/pl-unit-test`) -- Writes and runs tests against a 6-point quality rubric. Results go to `tests/<feature>/tests.json`.
4. **Web tests** (`/pl-web-test`) -- For features with `> Web Test:` metadata and Visual Specification, runs Playwright-based visual verification.
5. **Status commits:**
   - Features with **only Unit Tests** (no QA Scenarios): Builder marks `[Complete]` directly. QA is never invoked.
   - Features with **QA Scenarios**: Builder marks `[Ready for Verification]`. QA picks these up next.

### What you do:

- Approve the work plan
- Answer implementation questions
- Run any commands the Builder asks you to execute externally

---

## Phase 4: Verification (QA Agent)

**When:** Builder has marked features `[Ready for Verification]`.

**Launch:** Start a Claude session with QA instructions loaded.

### The Auto-First Protocol

QA follows a 7-step verification protocol, designed to minimize human effort by handling automatable work first:

**Step 1 -- Auto pass:** Credit Builder-verified features (Unit Tests only, cosmetic changes). Zero human time.

**Step 2 -- Run @auto scenarios:** Execute QA Scenarios tagged with `@auto` directly:
- If a regression JSON file exists (`tests/qa/scenarios/<feature>.json`), QA invokes the harness runner automatically.
- If no regression JSON exists, QA runs the scenario manually first. If it passes cleanly, QA authors the regression JSON and adds the `@auto` tag -- promoting it from manual to automated for next time.

**Step 3 -- Visual smoke:** For web features (`> Web Test:`), QA invokes `/pl-web-test` for a quick Playwright screenshot and checklist check. For non-web features, QA asks you for a screenshot.

**Step 4 -- LLM delegation:** For scenarios needing Claude's analysis capabilities, QA composes the command and asks you to run it.

**Step 5 -- Smoke-tier manual first:** QA presents manual scenarios in priority order: smoke tier first, then standard, then full-only.

**Step 6 -- Full manual pass:** Visual checklists grouped by screen (one screenshot, multiple checks). Manual scenarios step-by-step.

**Step 7 -- Automation opportunity:** After verification, QA identifies scenarios that could be automated. Adds `@auto` tags and/or authors regression JSON files for future runs.

### What you do:

- Perform the manual verification steps QA describes
- Say PASS or FAIL for each item
- Provide screenshots when asked
- Run external commands when asked (copy-paste from QA's output)

### Completion:

- Features with zero discoveries: QA marks `[Complete] [Verified]`
- Features with discoveries: QA records BUGs/DISCOVERYs, routes to Builder/Architect

---

## Phase 5: Regression (QA Agent -- `/pl-regression`)

**When:** Features are verified and you want automated regression coverage.

**Launch:** Same QA session, or a new one. QA auto-detects regression work.

### The regression flow has three modes:

### Author Mode

QA discovers features that need regression scenario files and authors them one at a time.

**Fixture setup** -- When a scenario needs controlled project state:

1. **QA checks for a fixture repo.** If none exists, QA asks you:
   ```
   This feature needs controlled test state, but no fixture repo exists.

   Options:
     1. Create a local fixture repo (at .purlin/runtime/fixture-repo)
     2. Use a remote repo (provide the git URL)
     3. Skip fixtures for now (use inline setup instead)

   Choice? [1 / 2 <url> / 3]
   ```

2. **For Option 1:** QA runs `fixture init` and creates the local repo immediately.

3. **For Option 2:** You provide a git URL (any empty git repo works -- GitHub, GitLab, local bare repo). QA configures it.

4. **QA creates fixture tags** (`fixture add-tag`) for simple/moderate state directly. Each tag is an immutable snapshot of project state for one test scenario. Tags follow the convention: `main/<feature-name>/<scenario-slug>`.

5. **For complex fixtures** (elaborate git history, database state): QA records a recommendation and routes to the Builder via a `-qa` session.

After authoring, QA gives you a handoff message:
```
Regression scenarios authored: 8 features.

NEXT STEPS:
  1. Run regression tests:
         ./tests/qa/run_all.sh
  2. When tests finish, launch Builder to process results and fix failures.
```

### Run Mode

QA composes a copy-pasteable command for you to run in a separate terminal. You run it, tell QA when it finishes.

### Process Mode

QA reads the results, creates BUG discoveries for failures, reports tier distribution (Tier 1 = keyword match, Tier 2 = specific finding, Tier 3 = state verification), and flags shallow suites.

---

## Phase 6: Test Infrastructure (Builder -- `-qa` flag)

**When:** QA has recorded fixture recommendations that need Builder expertise, or regression harness infrastructure needs building.

**Launch:** `./pl-run-builder.sh -qa`

### What happens:

- Builder sees **only** Test Infrastructure category features.
- Reads `tests/qa/fixture_recommendations.md` for pending fixture work.
- Creates complex fixture tags, builds harness runner infrastructure, etc.
- Normal features are completely hidden -- no risk of mixing concerns.

After completing, the Builder recommends returning to QA:
```
Created fixture tags for 3 features in .purlin/runtime/fixture-repo.

NEXT STEP:
  Launch QA to continue regression scenario authoring.
  QA will use the new fixtures automatically.
```

---

## Quick Reference: Agent Sequencing

| Situation | Launch |
|-----------|--------|
| New feature from Figma | PM, then Architect, then Builder, then QA |
| New feature, no design | Architect, then Builder, then QA |
| Bug found in QA | Builder (fixes code), then QA (re-verifies) |
| Spec dispute | Architect (resolves), then Builder, then QA |
| Regression authoring | QA with `/pl-regression` |
| Complex fixture creation | Builder with `-qa` flag |
| All features done, ready to ship | Architect with `/pl-release-run` |

---

## How Fixture Tags Work

Fixture tags are immutable git tags in a dedicated bare repo. Each tag is a snapshot of project state needed for one test scenario.

```
.purlin/runtime/fixture-repo/     <-- bare git repo (local)
  tags:
    main/cdd_branch_collab/sync-state-ahead
    main/cdd_branch_collab/sync-state-diverged
    main/cdd_startup/expert-mode
```

**Tag naming:** `<project-ref>/<feature-name>/<scenario-slug>`

**Who creates them:**
- **QA** creates simple/moderate fixtures during regression authoring
- **Builder** (in `-qa` mode) creates complex fixtures requiring application knowledge

**Who consumes them:**
- The **harness runner** checks out a tag, runs the test, cleans up
- The **Critic** validates declared tags exist (flags missing ones)

**Lifecycle:**
- Tags are immutable -- once created, they do not change
- When a feature is retired (tombstoned), `fixture prune` flags orphan tags
- A setup script can regenerate all tags deterministically from project files

---

## Tips

- **Each agent self-discovers work.** You do not need to tell the Builder what to implement -- it reads the Critic report and finds TODO features automatically.
- **Commits are the coordination mechanism.** Agents communicate through git commits and the Critic report, not chat.
- **`@auto` tags are incremental.** A scenario starts manual. QA promotes it to `@auto` after it passes cleanly and regression JSON is authored. Over time, more scenarios become automated.
- **The `-qa` flag is for test infrastructure only.** Normal Builder sessions hide Test Infrastructure features. Use `-qa` when QA needs fixture or harness work done.
- **Smoke tier = verify first.** The Architect classifies features as smoke/standard/full-only. QA verifies smoke features first -- these are the ones that break everything if they fail.
