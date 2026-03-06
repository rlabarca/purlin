# Tombstone: policy_remote_collab.md

> Retired: 2026-03-06
> Replaced-By: features/policy_branch_collab.md
> Reason: Session abstraction removed. Branch name is now the identifier directly. "Remote Collaboration" renamed to "Branch Collaboration". All collab session concepts replaced with direct branch operations.

## Deletion Checklist

- [x] Replacement spec created: `features/policy_branch_collab.md`
- [x] All prerequisite links updated to point to replacement
- [x] Command references updated: `/pl-collab-push` -> `/pl-remote-push`, `/pl-collab-pull` -> `/pl-remote-pull`
- [x] Runtime file renamed: `active_remote_session` -> `active_branch`
- [x] Config key renamed: `remote_collab` -> `branch_collab` (with backward compat fallback)
