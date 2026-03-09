# TOMBSTONE: pl_isolated_push

**Retired:** 2026-03-08
**Reason:** /pl-isolated-push skill removed along with the isolated teams feature.

## Files to Delete

- `.claude/commands/pl-isolated-push.md` -- command file (skill definition)

## Dependencies to Check

- `instructions/references/architect_commands.md` -- remove from Isolated Session Variant (covered in Phase 3)
- `instructions/references/builder_commands.md` -- same
- `instructions/references/qa_commands.md` -- same
- All three `*_BASE.md` instruction files -- remove from authorized commands list (covered in Phase 3)

## Context

This skill performed handoff checklist verification and merged the isolation branch to the collaboration branch via `git merge --ff-only`. It was the primary workflow for completing an isolated session. No longer needed without isolated teams.
