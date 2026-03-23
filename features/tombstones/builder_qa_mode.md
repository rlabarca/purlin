# TOMBSTONE: builder_qa_mode

**Retired:** 2026-03-23
**Reason:** The `-qa` launcher flag created an artificial boundary between "normal work" and "test infrastructure work." Test Infrastructure features are now normal Builder work -- no special mode needed. The regression skill split (pl-regression-author, pl-regression-run, pl-regression-evaluate) makes the Builder's test infrastructure role clear without a mode flag.

## Files to Delete

- `tools/cdd/test_builder_qa_mode.py` -- entire file (unit tests for retired feature)
- `tests/builder_qa_mode/` -- entire directory (test results for retired feature)

## Code to Remove

- `pl-run-builder.sh:21` -- remove `-qa) export PURLIN_BUILDER_QA=true; shift ;;` case
- `tools/init.sh:170` -- remove `-qa) export PURLIN_BUILDER_QA=true; shift ;;` from launcher generator
- `tools/cdd/serve.py:1130-1146` -- remove `PURLIN_BUILDER_QA` env var resolution and `qa_mode` config block injection
- `tools/cdd/serve.py:1216` -- remove `if qa_mode:` filter (Test Infrastructure features should be visible in normal mode)
- `tools/cdd/serve.py:1241` -- remove `if not qa_mode:` exclusion (stop hiding Test Infrastructure features)
- `tools/cdd/serve.py:1315-1322` -- remove `qa_mode_recommendation` logic (no longer recommending `-qa` sessions)
- `.claude/commands/pl-fixture.md:81` -- remove "Standard build exclusion" paragraph referencing `qa_mode: true`. Replace with: "Fixtures are set up when explicitly directed by the user or when the feature spec contains a fixture tag section."

## Docs to Update

- `docs/builder-agent-guide.md` -- remove Section 8 ("The -qa Flag") and lines 35-38
- `docs/testing-workflow-guide.md` -- remove lines referencing `-qa` flag, "Builder with `-qa` Flag" section (lines 220-243), and `-qa` entries in the summary tables
- `docs/qa-agent-guide.md:201` -- remove `via ./pl-run-builder.sh -qa` reference; replace with "for the Builder to handle"

## Dependencies to Check

- `features/test_fixture_repo.md:369` -- scenario references "qa_mode enabled"; update scenario wording to remove qa_mode reference
- `tests/test_fixture_repo/tests.json:69` -- test `test_qa_mode_enabled_in_config` references qa_mode; Builder should update or remove this test
- `features/builder_qa_mode.impl.md` -- companion file; delete alongside the feature

## Context

The Builder QA Mode feature defined a `-qa` launcher flag that set `PURLIN_BUILDER_QA=true`, causing serve.py to filter the Builder's feature set to only "Test Infrastructure" category features. The rationale was to prevent test infrastructure work from mixing into normal feature-building sessions.

This separation is being retired because:
1. The regression skill split (pl-regression-author/run/evaluate) makes test infrastructure work discoverable through normal Critic action items
2. Test Infrastructure features should appear alongside all [TODO] features -- the Builder builds what the Critic says needs building
3. The `-qa` flag added cognitive overhead ("do I need -qa for this?") without proportional benefit

After cleanup, the Builder sees ALL features regardless of category. No filtering, no special mode, no recommendation to use `-qa`.
