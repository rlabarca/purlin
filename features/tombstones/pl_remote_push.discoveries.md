# Discovery Sidecar: pl_remote_push

## [BUG] M23: Skill file missing FORBIDDEN enforcement

- **Status:** RESOLVED
- **Action Required:** Engineer
- **Description:** The skill file at `.claude/commands/pl-remote-push.md` had no FORBIDDEN enforcement directives despite spec section 2.8 documenting explicit prohibitions (no force push, no push to non-collaboration branch, no unchecked user input).
- **Resolution:** Added `## FORBIDDEN` section to the skill file with three enforcement directives matching spec section 2.8 and `policy_branch_collab.md` Section 4. Added four tests verifying the FORBIDDEN section and each directive are present.
