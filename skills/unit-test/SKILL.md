---
name: unit-test
description: Run tests and emit proof files with coverage report
---

Run tests (unit tier unless `--all`), emit proof files via feature-scoped overwrite, and report coverage per feature.

## Usage

```
purlin:unit-test [feature]      Run tests for a specific feature (unit tier)
purlin:unit-test                Run all unit-tier tests
purlin:unit-test --all          Run all tests across all tiers
```

## Step 1 — Detect Test Framework

Read `.purlin/config.json` for `test_framework`. If set to a specific framework, use it. If `"auto"` or missing, detect from project files using the same heuristics as `purlin:init` Step 3 (see `references/supported_frameworks.md` for the full detection logic).

## Step 2 — Run Tests

```bash
# pytest (unit tier)
pytest -m "not integration"

# pytest (all tiers with --all)
pytest

# jest (unit tier)
npx jest --testPathPattern="unit"

# jest (all tiers with --all)
npx jest
```

The proof plugins (`scripts/proof/pytest_purlin.py`, `scripts/proof/jest_purlin.js`, `scripts/proof/shell_purlin.sh`) emit `<feature>.proofs-<tier>.json` next to the spec file. This is a **feature-scoped overwrite**: each run replaces all proof entries for the tested feature in that tier file, preserving entries from other features.

### Proof File Freshness Check

After tests run, before reporting results, verify that proof files (`*.proofs-*.json`) were modified AFTER the test command started. If proof files are older than the test run or don't exist, the proof plugin didn't emit — something went wrong. Report:

```
WARNING: Proof files were not updated by the test run. The proof plugin may not be loaded.
→ Check: is the proof plugin registered in conftest.py / jest.config.js?
→ Run: purlin:init --force to re-scaffold the proof plugin
```

Never write proof JSON files directly. Only the test framework plugin writes proof files.

## Step 3 — Report Coverage

Call `sync_status` after tests complete. Display the full result. **This is not optional** — without `sync_status`, the agent doesn't know if coverage is complete.

```
Test results:
  auth_login: PASSING (3/3 rules proved)
  user_profile: PARTIAL (1/2 rules proved)
    RULE-2: NO PROOF → write a test with @pytest.mark.proof("user_profile", "PROOF-2", "RULE-2")
    → PARTIAL means more tests needed to reach PASSING.
  webhook_delivery: FAILING (2/3 rules proved)
    RULE-1: FAIL → Fix: test_webhook_basic is failing
```

## Step 4 — Commit proof files (mandatory)

After proof files are written, commit them:

```
git add specs/**/*.proofs-*.json
git commit -m "test(<feature>): <passed>/<total> rules proved"
```

For multi-feature runs:
```
git commit -m "test: run unit tier (<passed>/<total> features fully proved)"
```

Proof files are project records, not ephemeral build artifacts. Uncommitted proof files make sync_status output inconsistent with what purlin:verify and purlin:drift see.

## Writing Tests with Proof Markers

When tests are missing, write them with proof markers. For marker syntax (pytest, Jest, Shell), see `references/formats/proofs_format.md`. For test quality rules (what makes a proof STRONG vs HOLLOW), see `references/audit_criteria.md`.

## Note

This skill does NOT issue verification receipts. That is `purlin:verify`'s job. This skill runs tests, emits proof files, and reports coverage.
