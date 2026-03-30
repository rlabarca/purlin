---
name: whats-different
description: Show what changed on the remote collaboration branch, grouped by file type
---

Generate a plain-English summary of what's different between the current HEAD and the remote collab branch (`origin/<branch>`). Groups changes by file type (SPEC, CODE, IMPL, QA) for easy handoff between collaborators.

## Steps

### 0. Main Branch Guard

Run: `git rev-parse --abbrev-ref HEAD`

If the result is not `main`, abort immediately:

```
This command is only valid from the main checkout.
Current branch: <branch>. Run purlin:whats-different from the project root (branch: main).
```

Do NOT proceed to Step 1.

### 1. Branch Guard

Read `.purlin/runtime/active_branch`. If the file is absent or empty, abort:

```
No active collaboration branch. Use purlin:remote branch create <name> to start one, or purlin:remote branch join <name> to join an existing one.
```

Extract the branch name from the file contents (single line, trimmed).

### 2. Load Config

Read remote name from `.purlin/config.json`: check `branch_collab.remote` first, fall back to `remote_collab.remote`, default to `"origin"` if both absent.

Construct the target branch: `<session>`.

### 3. Fetch and Sync State

```
git fetch <remote> <session>
```

Run two range queries:

```
git log origin/<session>..HEAD --oneline
git log HEAD..origin/<session> --oneline
```

Determine state: SAME, AHEAD, BEHIND, or DIVERGED.

If SAME: print "HEAD is in sync with <session>. Nothing to summarize." Exit.

### 4. Generate File-Type Grouped Digest

Run `git diff --name-status HEAD...origin/<session>` to get the list of changed files.

Classify each changed file using the project's file classification (CODE, SPEC, QA, IMPL). Group and display as:

```
SPEC changes:
  webhook_delivery.md: §2.3 retry strategy, §2.5 batch endpoint (3h ago)
  auth_middleware.md: new edge-case scenarios (1d ago)

CODE changes:
  scripts/webhook.py: 3 files changed (+142, -28) (3h ago)
  auth_middleware: 3 files (1d ago)

IMPL updates:
  webhook_delivery.impl.md: [DEVIATION] exponential backoff, [AUTONOMOUS] batch limit

QA changes:
  webhook_delivery: 4 regression scenarios added, 1 DISCOVERY recorded
  auth_middleware: regression results now STALE
```

For each group, read the actual diffs to provide meaningful summaries (not just file names). Show timestamps relative to now.

If a feature stem argument was provided, show detailed diff for just that feature across all file types.

### 5. Display Result

Output the grouped digest directly. If the diff is large, summarize each group with counts and highlight the most significant changes.

### 6. ID Drill-Down (Conversational)

After displaying the digest, be prepared for the user to reply with a numeric ID (e.g., "3", "#3", "tell me about 3"). When this happens:

1. Identify the corresponding item from the most recent digest.
2. Read the relevant source files (feature spec, companion file, discovery sidecar, git diff).
3. Provide a detailed explanation: what the original state was, what changed, the full context, and recommended next steps.

No script or endpoint is needed — this is conversational. The IDs make it easy to request detail without typing file paths.
