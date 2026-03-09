# TOMBSTONE: pl_isolated_pull

**Retired:** 2026-03-08
**Reason:** /pl-isolated-pull skill removed along with the isolated teams feature.

## Files to Delete

- `.claude/commands/pl-isolated-pull.md` -- command file (skill definition)

## Dependencies to Check

- `instructions/references/architect_commands.md` -- remove from Isolated Session Variant (covered in Phase 3)
- `instructions/references/builder_commands.md` -- same
- `instructions/references/qa_commands.md` -- same
- All three `*_BASE.md` instruction files -- remove from authorized commands list (covered in Phase 3)

## Context

This skill rebased the isolation branch onto the collaboration branch to incorporate new commits. No longer needed without isolated teams.
