# Implementation Notes: /pl-remote-push

**[DISCOVERY] [ACKNOWLEDGED]** Skill file missing FORBIDDEN enforcement reflection
**Source:** /pl-spec-code-audit --deep (M23)
**Severity:** MEDIUM
**Details:** Spec §2.8 defines FORBIDDEN Pattern Enforcement (no force push, no push to wrong branch). The skill file (`.claude/commands/pl-remote-push.md`) contains no explicit prohibition or validation notes. An agent following the skill alone would have no inline constraint against force-push.
**Suggested fix:** Add a FORBIDDEN enforcement section to the skill file listing the prohibitions from spec §2.8 and `policy_branch_collab.md` Section 4.
