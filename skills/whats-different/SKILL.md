---
name: whats-different
description: Show what changed since last session or on a collaboration branch, grouped by file type with optional role focus
---

## Arguments

```
/whats-different                → auto-detect context, all file types
/whats-different pm             → PM-focused briefing
/whats-different engineer       → Engineer-focused briefing
/whats-different qa             → QA-focused briefing
/whats-different <feature>      → detailed diff for one feature
```

## Context Detection

1. `.purlin/runtime/active_branch` exists and non-empty → **collab** (compare against remote branch)
2. Otherwise → **solo** (compare against last session)

---

## Solo (since last session)

### 1. Find Comparison Point

Read `.purlin/runtime/last_session_head` (written by session-init hook).

- SHA differs from HEAD → changes exist, proceed.
- File missing → fall back to `git log --since="24 hours ago"` or last 10 commits.
- HEAD equals stored SHA → "No changes since session start." Exit.

### 2. Gather and Classify

```
git log <last_session_head>..HEAD --oneline
git diff --name-status <last_session_head>..HEAD
```

Classify each file using `purlin_classify` (returns CODE, SPEC, QA, IMPL, or OTHER). Map CODE/SPEC/QA/IMPL files to feature stems. Group by type, with OTHER files in a separate informational section:

```
Changes since last session (12h ago, 5 commits):

SPEC changes:
  webhook_delivery: updated retry strategy, added batch endpoint

CODE changes:
  scripts/webhook.py: retry logic (+42 lines)
  scripts/webhook_batch.py: new file

IMPL updates:
  webhook_delivery: [DEVIATION] exponential backoff

QA changes:
  webhook_delivery: 4 regression scenarios added

Other changes (not tracked):
  docs/api-guide.md: updated webhook section
  README.md: version bump
```

Read diffs for meaningful summaries, not just file names.

### 3. Sync Drift

After file groups, show per-feature drift from `purlin_status(verbosity: "minimal")`:

```
Sync drift:
  auth_middleware: code ahead (code 2h ago, spec unchanged) — run purlin:spec-catch-up
  webhook_delivery: synced
```

For `code_ahead` features, always include the `purlin:spec-catch-up` hint so the PM knows the next action.

### 4. Role Briefing

When a role argument is given, prepend a focused action summary:

**`/whats-different pm`** — spec changes to review, deviations to acknowledge, code-ahead features needing PM attention.

**`/whats-different engineer`** — code changes, spec updates affecting existing code, sync debt, tombstones to process.

**`/whats-different qa`** — test results, regression staleness, TESTING features, new scenarios.

Each item gets a sequential numeric ID for drill-down.

When a role argument is given, OTHER changes are collapsed at the bottom: `Also changed (not tracked): docs/api-guide.md, README.md (+2 more)` — not highlighted, not actionable, just FYI.

---

## Collab (vs remote branch)

### 1. Config + Fetch

Remote from `.purlin/config.json` (`branch_collab.remote` → `remote_collab.remote` → `"origin"`).

```
git fetch <remote> <branch>
```

### 2. Sync State

Compare `origin/<branch>..HEAD` and `HEAD..origin/<branch>`. States: SAME, AHEAD, BEHIND, DIVERGED.

SAME → "In sync. Nothing to summarize." Exit.

### 3. Digest

Same file-type grouping as solo. If DIVERGED, show both directions.

### 4. Sync Drift and Companion Staleness

After the file-type digest, read sync ledger and overlay drift status for features touched in the diff:

```
Sync drift:
  auth_middleware: code ahead (code 2h ago, spec unchanged) — run purlin:spec-catch-up
  webhook_delivery: synced
```

For `code_ahead` features, always include the `purlin:spec-catch-up` hint.

For each feature with code changes: if `.impl.md` exists but was NOT updated in the diff, flag it:

```
Companion check:
  auth_login: 3 code files changed, impl not updated
```

Role briefing works the same as solo.

---

## Feature Drill-Down

`/whats-different webhook_delivery` → detailed diff across all file types for that feature (spec diff, code summary, impl entries, QA state).

## ID Drill-Down

After any numbered briefing, user can reply with an ID ("3", "#3"). Read source files for that item and explain: what changed, original state, recommended next steps.
