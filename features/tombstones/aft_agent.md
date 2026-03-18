# TOMBSTONE: aft_agent

**Retired:** 2026-03-18
**Reason:** The AFT:Agent typed pattern is removed as part of the AFT taxonomy elimination. The agent testing pattern (fixture checkout, prompt construction, multi-turn scripting, assertions) is absorbed into `features/arch_testing.md` as a reference pattern. The Purlin-dev harness continues to exist as a project-specific regression tool.

## Files to Delete

- `features/aft_agent.impl.md` -- companion file (archive; no longer governed by a feature spec)
- `tests/aft_agent/` -- test results directory for the retired feature

## Dependencies to Check

- `dev/test_agent_interactions.sh` -- continues to exist but is no longer governed by a typed AFT feature. Update any references to `features/aft_agent.md` or the AFT:Agent pattern.
- `dev/test_aft_agent_harness.py` -- update references to `aft_agent.md` if any
- `.claude/commands/pl-regression.md` -- remove `> AFT Agent:` harness mapping; replaced by `### Regression Testing` section-based discovery
- `dev/setup_fixture_repo.sh` -- fixture tags under `main/aft_agent/` may need renaming or removal

## Context

This feature defined the AFT:Agent pattern for automated agent interaction testing -- scripting multi-turn conversations with agent roles using `claude --print`. The pattern itself (fixture checkout, prompt construction, assertion tiers, negative tests) is valuable and preserved in `arch_testing.md`. What is removed is the typed AFT categorization and the `> AFT Agent:` metadata convention.

Features that previously declared `> AFT Agent: <role>` now use a `### Regression Testing` section in their spec body to describe regression test requirements. The Critic discovers regression-eligible features via this section rather than metadata tags.

**Successor pattern:** `arch_testing.md` (testing pattern) + per-feature `### Regression Testing` sections
