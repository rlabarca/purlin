# TOMBSTONE: aft_regression_testing

**Retired:** 2026-03-18
**Reason:** Renamed to `features/regression_testing.md`. AFT taxonomy removed; regression testing is now a general-purpose concept not tied to AFT types.

## Files to Delete

- `features/aft_regression_testing.md` -- already deleted by Architect
- `features/aft_regression_testing.impl.md` -- already replaced by `regression_testing.impl.md`
- `dev/aft_runner.sh` -- rename to `dev/regression_runner.sh`
- `tests/aft_regression_testing/` -- rename to `tests/regression_testing/`

## Dependencies to Check

- `.claude/commands/pl-regression.md` -- update all AFT references, harness mapping
- `dev/test_agent_interactions.sh` -- update references to aft_runner.sh
- `.purlin/runtime/aft_trigger.json` -- path renamed to `.purlin/runtime/regression_trigger.json`
- `.purlin/runtime/aft_result.json` -- path renamed to `.purlin/runtime/regression_result.json`

## Context

The regression testing infrastructure is being decoupled from the AFT type system. The runner script, trigger/result files, and QA skill are renamed to remove AFT prefixes. Discovery of regression-eligible features changes from metadata-based (`> AFT Agent:`, `> AFT Web:`) to section-based (`### Regression Testing` in the feature spec) plus `> Web Test:` metadata.

**Successor:** `features/regression_testing.md`
