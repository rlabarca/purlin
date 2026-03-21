# Tombstone: Policy Test Quality Standards

> **Status:** RETIRED
> **Retired:** 2026-03-20
> **Reason:** Content absorbed into `/pl-unit-test` skill (`.claude/commands/pl-unit-test.md`). The skill is now the single source of truth for test quality standards (anti-patterns AP-1 through AP-5, deletion invariant, minimum assertion depth, test tier decision matrix, quality rubric gate).

## Files to Delete

- `features/policy_test_quality.md` -- the retired policy anchor

## Dependencies to Check

- `instructions/BUILDER_BASE.md:127` -- references `policy_test_quality.md` guidelines (update to `/pl-unit-test`)
- `.claude/commands/pl-build.md:75` -- references `policy_test_quality.md` for test quality self-audit (update to `/pl-unit-test`)
- `features/arch_testing.md` -- no direct reference found, but add cross-reference to `/pl-unit-test` for the Unit tier

## Notes

This was a policy anchor with no scenarios and no dependent features (nothing declared `> Prerequisite: features/policy_test_quality.md`). Its value was entirely in the content, not the anchor cascade mechanism. All substantive content is preserved in the skill.
