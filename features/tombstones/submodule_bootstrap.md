# TOMBSTONE: submodule_bootstrap

**Retired:** 2026-03-05
**Reason:** Fully superseded by `features/project_init.md` (Unified Project Init). The bootstrap.sh script and its test are no longer needed.

## Files to Delete

- `tools/bootstrap.sh` -- entire file (deprecation shim, replaced by `tools/init.sh`)
- `tools/test_bootstrap.sh` -- entire file (tests moved to `tools/test_init.sh`)

## Dependencies to Check

- `features/project_init.md` -- Prerequisite link already removed; inline references to `submodule_bootstrap.md` sections already updated to be self-contained.
- `features/release_submodule_safety_audit.md` -- Prerequisite link and body references updated to point to `project_init.md`.
- `features/python_environment.md` -- Reference to `bootstrap.sh` in Section 2.2 table updated.
- `instructions/HOW_WE_WORK_BASE.md` -- Section 6 reference updated from `bootstrap.sh` to `init.sh`.
- `.purlin/release/local_steps.json` -- `submodule_safety_audit` step audit scope reference updated.
- `.claude/commands/pl-edit-base.md` -- Reference to `bootstrap.sh` updated.
- `features/pl_update_purlin.md` -- Section 2.12 stale artifacts list now includes `bootstrap.sh` and `test_bootstrap.sh`.

## Context

The Submodule Bootstrap feature defined the original `tools/bootstrap.sh` script for initializing consumer projects that use Purlin as a git submodule. It handled `.purlin/` directory creation, config patching, launcher script generation, command file distribution, and gitignore setup.

`project_init.md` superseded it with a unified `tools/init.sh` that supports both full init and idempotent refresh modes. The bootstrap.sh script was temporarily retained as a deprecation shim that delegated to init.sh. With the shim no longer needed, both `bootstrap.sh` and its test script `test_bootstrap.sh` should be deleted.

The submodule safety contract requirements (Sections 2.10-2.14 of the retired spec) remain valid and are now self-contained within `project_init.md` and referenced by `release_submodule_safety_audit.md`.
