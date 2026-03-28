---
name: smoke
description: This skill activates QA mode
---

**Purlin mode: QA**

Purlin agent: This skill activates QA mode.

---

## Usage

```
purlin:smoke <feature>          — Promote a test to smoke tier
purlin:smoke suggest             — Suggest features that should be smoke
```

## Path Resolution

> Scripts at `${CLAUDE_PLUGIN_ROOT}/scripts/`. References at `${CLAUDE_PLUGIN_ROOT}/references/`.
> **Test infrastructure:** See `${CLAUDE_PLUGIN_ROOT}/references/test_infrastructure.md` for result schemas, harness types, status interpretation, and smoke tier rules.

---

## Subcommand: `purlin:smoke <feature>`

Promote a feature's test to smoke tier with an optional simplified fast-running version.

### Protocol

1. **Read the feature spec** at `features/<feature>.md`. Identify what type of tests exist:
   - Unit tests (`### Unit Tests`)
   - QA scenarios (`### QA Scenarios` — `@auto` or `@manual`)
   - Regression JSON (`tests/<feature>/regression.json` or `tests/qa/scenarios/<feature>.json`)

2. **Add to smoke tier table.** Read `PURLIN_OVERRIDES.md` (or `.purlin/QA_OVERRIDES.md` in legacy projects). Add the feature to the `## Test Priority Tiers` table with tier `smoke`. If the table doesn't exist, create it:

   ```markdown
   ## Test Priority Tiers

   | Feature | Tier |
   |---------|------|
   | <feature> | smoke |
   ```

3. **Offer to simplify.** Ask the user:

   ```
   <feature> promoted to smoke tier.

   Current tests:
     - N unit test scenarios
     - N QA scenarios (M @auto, K @manual)
     - Regression: PASS/FAIL/none

   Smoke tests should run fast and catch critical breakage.
   Want me to create a simplified smoke version? [yes / no]
   ```

4. **If yes — create smoke regression.** Create a focused regression JSON at `tests/qa/scenarios/<feature>_smoke.json` that:
   - Tests ONLY the critical path (1-3 scenarios max)
   - Strips setup overhead where possible
   - Uses the fastest harness type available for the feature
   - Targets < 30 second execution time
   - References the full regression suite for comprehensive coverage

   Format:
   ```json
   {
     "feature": "<feature>",
     "frequency": "per-feature",
     "tier": "smoke",
     "smoke_of": "<feature>.json",
     "scenarios": [
       {
         "name": "critical_path_check",
         "description": "Minimal verification that <core behavior> works",
         ...
       }
     ]
   }
   ```

5. **Commit** with message: `qa(<feature>): promote to smoke tier`

---

## Subcommand: `purlin:smoke suggest`

Analyze the project and suggest features that should be smoke tier.

### Protocol

1. **Run scan.** Execute `${CLAUDE_PLUGIN_ROOT}/scripts/cdd/scan.sh --only features,smoke,deps` and parse the JSON output.

2. **Identify smoke candidates.** A feature is a strong smoke candidate if:
   - It is a prerequisite for 3+ other features (high fan-out in dependency graph)
   - It has `arch_*` or `policy_*` as a prefix (foundational constraint)
   - It is in the "Install, Update & Scripts" or "Coordination & Lifecycle" category
   - Its name contains: `launcher`, `init`, `config`, `status`
   - It has existing regression tests that PASS (proven testable)

3. **Filter out already-classified.** Read the tier table and exclude features already marked smoke.

4. **Present suggestions.** For each candidate:

   ```
   Smoke Tier Suggestions
   ━━━━━━━━━━━━━━━━━━━━━━

   agent_launchers_common — prerequisite for 12 features, has passing regression
   purlin_scan_engine — core work discovery, no smoke coverage yet
   purlin_agent_launcher — launcher is critical path, regression PASS

   Promote any of these? Type feature name(s) or "skip".
   ```

5. **If the user selects features,** run `purlin:smoke <feature>` for each.

---

## Smoke Tier Rules

- **Smoke tests run FIRST** in every QA verification pass (before standard, before full-only).
- **Smoke tests should be fast** — target < 30 seconds per feature.
- **A smoke failure blocks all other verification** — if smoke fails, stop and report. Don't waste time on standard/full tests when the foundation is broken.
- **Every project should have 5-15 smoke features** covering the critical path.
- **Smoke ≠ comprehensive** — smoke catches "is it completely broken?" not "is every edge case handled?"
