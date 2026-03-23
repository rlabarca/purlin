**Purlin command owner: QA**

If you are not operating as the Purlin QA Agent, respond: "This is a QA command. Ask your QA agent to run /pl-regression-author instead." and stop.

---

## Path Resolution

Read `.purlin/config.json` and extract `tools_root` (default: `"tools"`). Resolve project root via `PURLIN_PROJECT_ROOT` env var or by climbing from CWD until `.purlin/` is found. Set `TOOLS_ROOT = <project_root>/<tools_root>`.

---

## Overview

Create scenario JSON files from feature specs. This skill is infrequent -- only needed when new features reach Builder DONE status with no scenario file.

Scenario files and harness scripts are behavioral verification artifacts, not application code -- the Builder does NOT write or modify them.

**MANDATORY UX RULE:** Whenever you ask the user to run something in an external terminal, you MUST print the exact, complete, copy-pasteable command. Never describe what to run in prose.

---

## Prerequisite Check: Harness Runner Framework

Before authoring, check whether the harness runner framework exists:
- Check for `${TOOLS_ROOT}/test_support/harness_runner.py`.
- If missing: print the handoff message below and STOP.

```
Cannot author regression scenarios -- the harness runner framework
has not been built yet.

NEXT STEP:
  Launch Builder. The Builder will build the harness runner framework
  as part of its normal TODO work.
  After Builder finishes, re-run QA to author scenarios.
```

---

## Step 1 -- Discover Features Needing Authoring

Run `${TOOLS_ROOT}/cdd/status.sh --role qa` and parse the output. Identify features meeting ALL criteria:

- Feature has `### Regression Testing` section or `## Regression Guidance` section or `> Web Test:` metadata.
- Builder status is DONE (implementation exists to test against).
- No corresponding `tests/qa/scenarios/<feature_name>.json` exists.

If zero features match: print "No features need regression scenario authoring." and stop.

---

## Step 2 -- Present Authoring Plan

```
Regression Authoring: N features need scenario files

  1. instruction_audit — has Regression Testing section
  2. cdd_startup — has Regression Guidance section
  3. pl_web_test — has Web Test metadata

Begin authoring? [yes / skip]
```

If user skips, stop.

---

## Step 3 -- Author Scenario File (per feature)

One feature at a time. Sequential processing to conserve context.

For each feature:

1. Read the feature spec. Focus on `### Regression Testing`, `## Regression Guidance`, `> Web Test:`, and the Gherkin scenarios.
2. **Evaluate fixture needs** (see Fixture Integration below).
3. Compose the scenario JSON file following the schema in `features/regression_testing.md` Section 2.7:
   - Set `harness_type` based on the feature's test pattern (`agent_behavior`, `web_test`, or `custom_script`).
   - Set `frequency` to `pre-release` for long-running suites (e.g., skill behavior tests using `claude --print`), or omit for standard per-feature frequency.
   - Map Gherkin scenarios to scenario entries with appropriate assertions and tiers.
   - Include `fixture_tag` if fixtures are available, or `setup_commands` for simple inline state.
4. Write the file to `tests/qa/scenarios/<feature_name>.json`.
5. Commit: `git commit -m "qa(<feature_name>): author regression scenario"`.
6. Print progress: `"Authored M/N scenarios. K remaining."`.
7. Move to next feature.

---

## Step 4 -- Generate Consumer Wrapper (first authoring session only)

If `tests/qa/run_all.sh` does not exist, generate the thin wrapper:

```bash
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$(git rev-parse --show-toplevel)/${TOOLS_ROOT}/test_support/run_regression.sh" --scenarios-dir "$SCRIPT_DIR/scenarios"
```

Adjust the path to match the project's `tools_root` configuration. Commit: `git commit -m "qa: generate regression runner wrapper"`.

---

## Step 5 -- Authoring Complete

Print the handoff message and run `${TOOLS_ROOT}/cdd/status.sh`:

```
Regression scenarios authored: N features.

NEXT STEPS:
  1. Run regression tests:
         ./tests/qa/run_all.sh
  2. When tests finish, launch Builder to process results and fix failures.
  3. After Builder fixes, re-run tests:
         ./tests/qa/run_all.sh
  4. When all tests pass, launch QA to process final results.
```

---

## Fixture Integration

During Step 3, per feature, apply this decision logic:

### Fixture Repo Check

Before evaluating per-feature fixture needs, check whether a fixture repo exists:

1. Check convention path: `.purlin/runtime/fixture-repo`
2. Check config: `fixture_repo_url` in `.purlin/config.json`
3. Check per-feature: `> Test Fixtures:` metadata

If none resolves to an accessible repo AND the current feature needs controlled state, prompt the user:

```
This feature needs controlled test state, but no fixture repo exists.

Options:
  1. Create a local fixture repo (I'll set it up at .purlin/runtime/fixture-repo)
  2. Use a remote repo (provide the git URL)
  3. Skip fixtures for now (use inline setup_commands instead)

Choice? [1 / 2 <url> / 3]
```

- **Option 1:** Run `${TOOLS_ROOT}/test_support/fixture.sh init`. Announce: `"Created local fixture repo at .purlin/runtime/fixture-repo"`.
- **Option 2:** Record the URL in `.purlin/config.local.json` under `fixture_repo_url`. Announce: `"Configured remote fixture repo: <url>"`.
- **Option 3:** Fall through to inline `setup_commands`.

### Per-Feature Fixture Evaluation

1. Does the `### Regression Testing` section reference fixture tags?
   - Yes: Run `${TOOLS_ROOT}/test_support/fixture.sh list` to check if tags exist.
   - Tags exist: Use them in the scenario JSON `fixture_tag` field. Update `tests/qa/fixture_usage.json`.
   - Tags missing: QA creates them directly via `fixture add-tag` if the state can be constructed. For complex state requiring Builder expertise, note the gap for Builder.

2. No explicit fixture tags, but scenario needs controlled state?
   - Simple state (single config, no git history): Use `setup_commands` in the scenario JSON.
   - Moderate state (specific file content, config combinations): QA creates a fixture tag directly via `fixture add-tag`, then references it in the scenario JSON.
   - Complex state (elaborate git history, build artifacts): Record the recommendation in `tests/qa/fixture_recommendations.md` for the Builder to handle.

3. Announce fixture usage: `"Using fixture tag main/<feature>/<slug> (local repo)"`

---

## Context Management

- Each scenario file is independent (no cross-feature state).
- QA loads one spec at a time (~200 lines), writes one JSON file (~30 lines), commits.
- Estimated capacity: 20-30 features per session before context pressure.
- Mid-session checkpoint: use `/pl-resume save` to capture regression authoring state.
- No separate queue file. Progress is tracked by file existence: `tests/qa/scenarios/<feature_name>.json` present = authored.
