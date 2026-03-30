---
name: status
description: Show project status with sync state and actionable work items
---

## Scan

Run `purlin_scan` (with `tombstones: true`) to get full project state.

## Work Interpretation Rules

Analyze the scan JSON to classify features into role-based work items. Show all work grouped by role.

> **MANDATORY RULE — spec_modified_after_completion:**
> When a feature has `spec_modified_after_completion: true`, it IS Engineer work. Period.
> Do NOT dismiss it as "advisory." Do NOT say "no re-implementation needed."
> Do NOT skip it because tests pass or lifecycle says COMPLETE.
> The spec changed — the Engineer MUST re-read the spec, diff it against the implementation,
> re-run tests, and update code if any spec requirements changed.
> List every such feature as an Engineer work item with reason "spec modified after completion."

**Engineer work (check ALL of these — a feature matching ANY rule is Engineer work):**
1. Features with `tombstone: true` — **highest priority**, process deletions before any other work
2. Features with `test_status: FAIL` or `regression_status: FAIL` — fix failures first
3. Features with `spec_modified_after_completion: true` — see mandatory rule above
4. Features in TODO lifecycle with no open INFEASIBLE — new work
5. Open BUG discoveries with `action_required: Engineer`
6. Delivery plan features in current phase
7. Features with companion debt (`companion_debt` scan entries) — companion file missing or stale since last code activity. Show as advisory items with hint: `"Run purlin:spec-code-audit to reconcile companion files in bulk."`

**QA work:**
- Features where tests pass, QA scenarios exist, lifecycle is TESTING
- SPEC_UPDATED discoveries awaiting re-verification
- `spec_modified_after_completion` is NOT a QA concern — it is Engineer-only. Do NOT show it in QA work items or treat it as a completion blocker. If the Engineer has re-validated and re-tagged the feature, QA proceeds normally.
- **Regression status:** Features with STALE or FAIL `regression_status` in scan results — show as QA work items with reason `"regression STALE"` or `"regression FAIL"`. Include hint: `"Run purlin:regression to update."`
- **Smoke candidates:** Read `smoke_candidates` from scan results. If non-empty, show after QA work items:
  ```
  Smoke candidates (unclassified):
    feature_name — N dependents
  ```
  This is informational — no action required. QA can promote via `purlin:smoke`.

**PM work:**
- Features where `sections.requirements` is false (incomplete spec)
- Unacknowledged deviations (PM needs to accept/reject)
- SPEC_DISPUTE and INTENT_DRIFT discoveries

## Work Item Priority Ranking

Action items within each role MUST be sorted in this order (highest priority first):

1. **Tombstones** — Engineer processes tombstones before any regular work
2. **FAIL** — Test failures or regression failures require immediate attention
3. **TESTING** — Features in verification (QA) or features blocked by spec issues (PM)
4. **TODO** — Features not yet started
5. **Informational** — Smoke candidates, cosmetic notes

## Output Format

**Always shown:**
- Feature counts by lifecycle (TODO / TESTING / COMPLETE)
- **Worktree summary** (when worktrees exist): scan `git worktree list` for entries under `.purlin/worktrees/`, read `.purlin_session.lock` for PID liveness, display one-line summary: `Worktrees: W1 (active), W2 (stale)`. Use `purlin:worktree list` for full detail.

**Work items:**
- Show work items grouped by role (Engineer, QA, PM), sorted by priority, with reason annotations
- Open discoveries grouped by role

**Status values and what they mean:**

| Role | Status | Meaning |
|------|--------|---------|
| PM | DONE | No spec gaps, no pending disputes or decisions |
| PM | TODO | Spec gate failures, unacknowledged decisions, or open disputes |
| Engineer | DONE | Tests pass, no open BUGs, feature not in TODO lifecycle |
| Engineer | TODO | Feature in TODO lifecycle (spec modified or never built) |
| Engineer | FAIL | tests.json exists with status FAIL |
| Engineer | BLOCKED | OPEN SPEC_DISPUTE suspends work |
| Engineer | INFEASIBLE | Engineer halted work, PM must revise spec |
| QA | CLEAN | Tests pass, no discoveries |
| QA | TODO | Feature in TESTING with manual scenarios |
| QA | FAIL | OPEN BUGs exist |
| QA | DISPUTED | OPEN SPEC_DISPUTEs exist |
| QA | N/A | No test coverage or no QA-relevant items |

**Uncommitted Changes Check**

After completing the standard output above, check for uncommitted changes:

1.  Run `git status` and `git diff` to identify staged changes, unstaged modifications, and untracked files.
2.  **Spec files** (`features/**/*.md`, `features/**/*.impl.md`, `instructions/*.md`, `.purlin/*.md`, `README.md`, `.gitignore`, `.purlin/toolbox/*.json`, `.purlin/config.json`):
    *   Present a summary of changed files grouped by change type (new, modified, deleted).
    *   Read the diffs to understand the substance of each change.
    *   Propose a commit message following the project's commit convention (e.g., `spec(feature_name): add edge-case scenarios`, `docs(readme): update release history`). The message must reflect the "why" not just the "what."
    *   Ask the user: **"These spec files have uncommitted changes. Commit with the above message?"**
3.  **Other files** (source, scripts, tests, etc.): Note them in the output but take no action.
4.  **Clean working tree:** Report "No uncommitted changes."
