---
name: status
description: Show project status with sync state and actionable work items
---

## Arguments

`/status [role]`

- No argument → all roles
- `pm` → PM work only
- `engineer` → Engineer work only
- `qa` → QA work only

## Get Status

```
purlin_status(verbosity: "focused", role: <from argument, default "all">)
```

Server-side classification. Returns pre-bucketed work items — you never see raw feature arrays.

### Response Fields

| Field | Contents |
|-------|----------|
| `lifecycle_counts` | Feature counts by lifecycle (TODO, TESTING, COMPLETE, TOMBSTONE) |
| `total_features` | Total count |
| `sync_counts` | Counts per sync status (synced, code_ahead, spec_ahead, new, unknown) |
| `sync_details` | Per-feature drift: `name`, `sync_status`, `last_code_date`, `last_spec_date`, `last_impl_date`. Only actionable entries (not synced/unknown). |
| `work` | Role-keyed dict. Each: `count` + deduplicated `items[]` (one per feature, highest-priority reason wins) |
| `delivery_plan_summary` | Current phase info if plan exists |
| `smoke_candidates` | Features recommended for smoke tier |
| `git_state` | `branch`, `clean`, `dirty_file_count` |

Each work item: `name`, `file`, `reason`, `priority`, optional `details`.

## Output

### All Roles (`/status`)

```
Project: N features (X COMPLETE, Y TESTING, Z TODO)
Sync: A synced, B code ahead, C spec ahead | Branch: <branch> | Uncommitted: N files

Engineer: X items (N tombstones, N spec-modified, N TODO)
QA: X items (N testing, N regression stale)
PM: X items (N spec gaps, N unacknowledged deviations)

Top priority: <role> — <highest priority item>
```

When `sync_details` is non-empty, show drift after summary:

```
Sync drift:
  auth_middleware: code ahead (code 2h ago, spec unchanged)
  webhook_delivery: spec ahead (spec 3h ago, code 2d ago)
  notification_system: new (spec exists, no code yet)
```

### Single Role (`/status pm`, `/status engineer`, `/status qa`)

```
Project: N features (X COMPLETE, Y TESTING, Z TODO)
Branch: <branch> | Uncommitted: N files

<Role> Work (X items):
  <items grouped by reason, sorted by priority>
```

Group by reason: tombstones, failures, spec-modified, TODO, advisory. Include sync drift when relevant to the role.

## Classification Rules

Implemented in `scan_engine.classify_work_items()`. Server applies them — do not re-implement.

**Engineer** (priority order): tombstones > test/regression FAIL > spec_modified_after_completion > TODO (excluding INFEASIBLE) > open BUGs > delivery plan phase > code_ahead (advisory: `"Run purlin:spec-catch-up to update the spec, or purlin:spec-code-audit for a full bidirectional audit."`)

**QA:** regression STALE/FAIL > TESTING with QA scenarios > SPEC_UPDATED discoveries

**PM:** incomplete spec (missing requirements) > unacknowledged deviations > code_ahead (spec needs updating: `"Run purlin:spec-catch-up to reconcile."`) > spec_ahead > SPEC_DISPUTE/INTENT_DRIFT discoveries

## Uncommitted Changes

After status output, run `git status`/`git diff`:
- **Spec files** — summarize, propose commit message, ask user.
- **Other files** — note, no action.
- **Clean** — "No uncommitted changes."

If worktrees exist under `.purlin/worktrees/`, show one-line summary.

## Other Files

When the session has OTHER file edits (from sync_state `unclassified_writes` or `git status` showing files matching `write_exceptions`), show at the bottom of the output:

```
Other files changed this session: docs/guide.md, README.md
```

Informational only — no priority, no work items, no action required.
