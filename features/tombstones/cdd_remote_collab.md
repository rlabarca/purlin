# Tombstone: cdd_remote_collab.md

> Retired: 2026-03-06
> Replaced-By: features/cdd_branch_collab.md
> Reason: Session abstraction removed from CDD dashboard. "Remote Collaboration" renamed to "Branch Collaboration". Session-based UI replaced with direct branch operations (Create/Join/Leave). Delete functionality removed. Endpoints migrated from `/remote-collab/*` to `/branch-collab/*`.

## Deletion Checklist

- [x] Replacement spec created: `features/cdd_branch_collab.md`
- [x] All prerequisite links updated to point to replacement
- [x] Companion file ported: `cdd_remote_collab.impl.md` -> `cdd_branch_collab.impl.md`
- [x] Endpoints renamed: `/remote-collab/*` -> `/branch-collab/*`
- [x] status.json keys updated: `remote_collab` -> `branch_collab`, `active_session` -> `active_branch`
