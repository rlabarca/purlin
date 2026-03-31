# TOMBSTONE: purlin_fixture

**Retired:** 2026-03-31
**Reason:** Fixture management ceremony replaced by inline guidance in core skills. Fixture usage is encouraged; dedicated management skill was over-engineered.

## Files to Delete

- `skills/fixture/SKILL.md` — the fixture management skill
- `features/skills_qa/purlin_fixture.md` — the fixture skill spec
- `features/skills_qa/purlin_fixture.impl.md` (if exists)

## Dependencies to Check

- `features/skills_qa/purlin_web_test.md` — references `arch_testing.md` but not fixture directly
- `features/test_infrastructure/test_fixture_repo.md` — the fixture repo spec remains valid (defines the format); it is infrastructure, not a skill
- `features/test_infrastructure/skill_behavior_regression.md` — references `test_fixture_repo.md`

## Context

The `purlin:fixture` skill provided a 141-line management workflow for fixture repos (init, add-tag, list, three-tier resolution, setup scripts, lifecycle). Most of its value was guidance about when and how to use fixtures. That guidance has been distributed to the skills that need it:

- **`purlin:spec`** — PM guidance: when to declare fixture tags, when they're overkill, tag format
- **`purlin:build`** — Engineer guidance: use fixtures for complex state, inline setup for simple state
- **`purlin:verify`** — QA guidance: fixture-unavailable scenarios are INCONCLUSIVE, engineer-routable
- **`purlin:unit-test`** — Already had fixture exclusion guidance (unchanged)

The fixture repo infrastructure (`test_fixture_repo.md`) and format conventions remain. Only the dedicated management skill is retired.
