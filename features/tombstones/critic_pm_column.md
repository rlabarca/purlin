# TOMBSTONE: critic_pm_column

**Retired:** 2026-03-13
**Reason:** Consolidated into `critic_role_status.md` which defines the unified role status model for all 4 roles (PM, Architect, Builder, QA) in one place. The PM-specific patch approach created inconsistencies with the 3-role schema in `critic_tool.md`.

## Files to Delete

- `tools/critic/test_critic_pm_column.py` -- entire file (migrate tests to `test_critic_role_status.py`)
- `tests/critic_pm_column/` -- entire directory (migrate to `tests/critic_role_status/`)
- `features/critic_pm_column.impl.md` -- companion file for the retired feature

## Dependencies to Check

- `tools/critic/critic.py` -- PM routing logic (Owner tag parsing, PM action item generation, PM role status computation) should be verified against `critic_role_status.md` Section 2.5 requirements. The implementation is retained; only test organization changes.
- `tools/critic/test_critic_pm_column.py` -- all 24 tests should be migrated to `test_critic_role_status.py` covering the same scenarios now defined in `critic_role_status.md`.

## Context

The `critic_pm_column` feature added PM as a first-class role in the Critic, covering: Owner tag parsing, PM-specific SPEC_DISPUTE routing, design-related action item routing (stale designs, unprocessed artifacts), PM role status computation, CDD dashboard PM column display, and aggregate report PM section. All core Critic behavior (Sections 2.1-2.4, 2.6) has been absorbed into `features/critic_role_status.md`. Dashboard display requirements (Section 2.5) were already absorbed into `features/cdd_status_monitor.md`. The implementation code in `critic.py` is unchanged -- only the spec organization and test file naming need migration.
