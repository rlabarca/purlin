# Test Infrastructure Reference

Canonical reference for regression test result formats, harness types, status interpretation, and smoke tier classification. Skills should reference this file instead of restating these definitions.

For the complete testing lifecycle (who defines, implements, runs, and verifies each test type), see `testing_lifecycle.md`.

## Result File Locations

| File | Owner | Purpose |
|------|-------|---------|
| `tests/<feature>/tests.json` | Engineer | Unit test results (produced by test runner) |
| `tests/<feature>/regression.json` | QA | Regression test results (produced by harness runner) |
| `tests/qa/scenarios/<feature>.json` | QA | Regression scenario declarations |
| `tests/qa/scenarios/<feature>_smoke.json` | QA | Simplified smoke regression scenarios |

## Regression Result Schema (`regression.json`)

```json
{
  "feature": "<feature_stem>",
  "status": "PASS|FAIL",
  "passed": 5,
  "failed": 1,
  "total": 6,
  "test_file": "tests/qa/scenarios/<feature>.json",
  "details": [
    {
      "name": "<scenario-name>:<assertion-context>",
      "status": "PASS|FAIL",
      "scenario_ref": "features/<feature>.md:<scenario-name>",
      "expected": "<human-readable expected behavior>",
      "actual_excerpt": "<first ~500 chars of actual output>",
      "assertion_tier": 1
    }
  ]
}
```

## Scenario Declaration Schema (`tests/qa/scenarios/<feature>.json`)

```json
{
  "feature": "<feature_stem>",
  "harness_type": "agent_behavior|web_test|custom_script",
  "frequency": "per-feature|pre-release",
  "scenarios": [
    {
      "name": "<scenario_name>",
      "fixture_tag": "<optional fixture tag>",
      "setup_commands": ["<optional setup commands>"],
      "assertions": [
        {
          "tier": 1,
          "pattern": "<regex>",
          "context": "<human-readable description>"
        }
      ]
    }
  ]
}
```

## Harness Types

| Type | What it does | Runs in-session? | Typical duration |
|------|-------------|-----------------|-----------------|
| `agent_behavior` | Runs `claude --print` as a subprocess to test agent skills | Yes (non-interactive subprocess) | 30-60s per scenario |
| `web_test` | Manages dev server, fetches pages, evaluates assertions | Yes | 5-10s per scenario |
| `custom_script` | Executes a QA-authored script with `--write-results` | Yes | 10-30s per scenario |

All harness types run in-session. `agent_behavior` invokes `claude --print` as a stateless, non-interactive subprocess — no nested session conflict.

## Status Interpretation

| Status | Meaning | Action |
|--------|---------|--------|
| `PASS` | All assertions succeeded | None |
| `FAIL` | One or more assertions failed | Engineer fixes code; QA re-runs |
| `NOT_RUN` | Scenario file exists but never executed | Run via `purlin:regression` |
| `STALE` | Source changed since results were generated | Re-run via `purlin:regression` |

A feature with STALE or FAIL regression results MUST NOT be marked `[Complete]`.

## Assertion Tiers

| Tier | Description | Quality |
|------|------------|---------|
| 1 | Keyword-presence (`(?i)error`) | Brittle, false-positive prone |
| 2 | Pattern with context (`(?i)Error: permission denied`) | Reliable for specific behavior |
| 3 | Behavioral with negative test coverage | Best — verifies intent, not incidental output |

Suites where >50% of assertions are Tier 1 are flagged `[SHALLOW]`.

## Smoke Tier

### What Smoke Tests Are

Critical-path tests that verify the foundation hasn't broken. They run FIRST in every QA verification pass and block all further verification on failure. Target: 5-15 smoke features per project.

### Smoke Candidate Criteria

A feature is a smoke candidate if ALL of:
- 3+ dependents (high fan-out in the dependency graph)
- Not already classified as smoke
- Has `[Complete]` lifecycle status

Additional signals (used by `purlin:smoke suggest`):
- `arch_*` or `policy_*` prefix (foundational constraint)
- Category: "Install, Update & Scripts" or "Coordination & Lifecycle"
- Name contains: launcher, init, config, status, scan

### Smoke Execution Rules

- Smoke regressions (`_smoke.json`) run BEFORE smoke QA scenarios
- Smoke scenarios run BEFORE all standard-tier features
- ANY smoke failure displays `SMOKE FAILURE` banner and blocks further verification
- Smoke regressions target < 30 second execution, 1-3 scenarios max

### Smoke Regression Schema

```json
{
  "feature": "<feature_stem>",
  "harness_type": "<type>",
  "frequency": "per-feature",
  "tier": "smoke",
  "smoke_of": "<feature>.json",
  "scenarios": [...]
}
```

### Test Design Authority

QA is the test design authority for regression and smoke tests. QA decides what to test, how to test it, what harness to use, and what's critical path. PM's `## Regression Guidance` in feature specs is optional input — not a prerequisite.
