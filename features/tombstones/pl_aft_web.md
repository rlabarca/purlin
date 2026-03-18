# TOMBSTONE: pl_aft_web

**Retired:** 2026-03-18
**Reason:** Renamed to `features/pl_web_test.md`. The AFT taxonomy has been removed; `/pl-aft-web` becomes `/pl-web-test`.

## Files to Delete

- `.claude/commands/pl-aft-web.md` -- rename to `.claude/commands/pl-web-test.md`
- `tests/pl_aft_web/` -- rename to `tests/pl_web_test/`
- `features/pl_aft_web.md` -- already deleted by Architect
- `features/pl_aft_web.impl.md` -- already replaced by `pl_web_test.impl.md`

## Dependencies to Check

- `tools/critic/critic.py` -- `_parse_aft_web()` function and `aft_web` key references
- `tools/critic/test_critic.py` -- test data using `> AFT Web:` metadata
- `tools/cdd/serve.py` -- may reference `aft_web` keys
- `dev/setup_fixture_repo.sh` -- fixture tags and metadata references
- All instruction files and command tables referencing `/pl-aft-web`

## Context

This feature was renamed from `pl_aft_web` to `pl_web_test` as part of the AFT taxonomy removal. The command `/pl-aft-web` becomes `/pl-web-test`, metadata `> AFT Web:` becomes `> Web Test:`, and `> AFT Start:` becomes `> Web Start:`. The Critic parser should accept both old and new metadata forms during the transition period for backward compatibility with consumer projects.

**Successor:** `features/pl_web_test.md`
