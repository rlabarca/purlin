Push: run agent-driven handoff checks and merge current branch to main.

**Owner: All roles** (architect, builder, qa)

## Steps

### 1. Infer Role

Read the current branch name:
```
git rev-parse --abbrev-ref HEAD
```

Map to role:
- `spec/*` → architect
- `build/*` → builder
- `qa/*` → qa
- Other → ask the user to specify the role before continuing

### 2. Resolve PROJECT_ROOT

Use `PURLIN_PROJECT_ROOT` env var if set. Otherwise, parse `git worktree list --porcelain` and identify the main checkout: the entry whose `branch` field is `refs/heads/main`, or the first entry (the one without a `worktree` prefix path relative to the current one). Extract its absolute path.

### 3. Pre-Flight Sync Check

**a. Dirty check:**
```
git status --porcelain
```

Filter out any lines where the file path starts with `.purlin/` — these are environment-specific
config files excluded from dirty state per the collaboration policy (ref: cdd_collab_mode.md §2.3).

If any non-.purlin/ output remains, abort: "Commit or stash changes before pushing."

**b. Behind-main check:**
```
git -C <PROJECT_ROOT> log HEAD..main --oneline
git -C <PROJECT_ROOT> log main..HEAD --oneline
```
Count N = commits behind main, M = commits ahead of main.

If N > 0 AND M == 0 (BEHIND):
- Print: "Branch is N commit(s) behind main — auto-rebasing before merge check."
- Run: `git rebase main` (fast-forward — no commits to replay, no conflict risk)
- If rebase fails, abort: "Auto-rebase failed — resolve conflicts manually, then retry."
- After rebase, re-run dirty check (step 3a) to confirm clean state.

If N > 0 AND M > 0 (DIVERGED):
- Block immediately. Print:
  ```
  Branch is DIVERGED from main — cannot auto-resolve.
  Main has N commit(s) this branch is missing:
    <git log HEAD..main --oneline>
  Run /pl-work-pull to rebase and resolve before retrying /pl-work-push.
  ```
- Stop here. Do NOT proceed to handoff checklist.

### 4. Agent-Driven Handoff Evaluation

Evaluate each item below. Record PASS or FAIL with a one-line reason.

**Shared (all roles):**

| Item | How to evaluate |
|------|----------------|
| `git_clean` | Already verified in step 3a — mark PASS. |
| `branch_naming` | Current branch matches role prefix (`spec/*`, `build/*`, `qa/*`). PASS if matches, FAIL if not. |
| `critic_report` | Read `CRITIC_REPORT.md` in PROJECT_ROOT. If missing or older than 24 hours (check file mtime), mark as WARNING (non-blocking). If report contains CRITICAL or HIGH items attributed to the current role, mark FAIL. |

**Architect-only (role == architect):**

| Item | How to evaluate |
|------|----------------|
| `spec_gate_pass` | Read `CRITIC_REPORT.md` Architect section. Any HIGH or CRITICAL items on feature files modified in `git diff main..HEAD -- features/`? FAIL if yes, PASS if none. |
| `impl_notes_stub` | For each `features/*.md` file modified in `git diff main..HEAD`, check that a `## Implementation Notes` section (or stub line `See [*.impl.md]`) exists. FAIL for any file missing it. |
| `visual_spec_complete` | For each modified feature file that contains a `## Visual Specification` section: verify a `**Reference:**` line exists and at least one `- [ ]` checkbox is present. FAIL if either is missing. |

**Builder-only (role == builder):**

| Item | How to evaluate |
|------|----------------|
| `tests_pass` | For each feature file modified in `git diff main..HEAD -- features/`, check whether `tests/<feature_name>/tests.json` exists with `"status": "PASS"`. FAIL for any feature missing a passing tests.json. |
| `impl_notes_updated` | Scan `## Implementation Notes` sections in modified feature files (or their `.impl.md` companions) for unacknowledged `[DEVIATION]` or `[DISCOVERY]` tags. FAIL if any are found without an Architect acknowledgement note. |
| `status_commit_made` | Run `git log main..HEAD --oneline`. Output must contain a line with `[Ready for Verification]` or `[Complete]`. FAIL if neither is present. |

**QA-only (role == qa):**

| Item | How to evaluate |
|------|----------------|
| `scenarios_complete` | For each in-scope feature: confirm all manual scenarios have been attempted. A scenario may be marked as blocked by an open BUG (explicitly noted) rather than attempted. FAIL only if scenarios were not attempted and have no blocking BUG noted. Features where all scenarios were attempted (even if some failed) are PASS. |
| `discoveries_addressed` | For each `features/*.md` modified in `git diff main..HEAD`, check `## User Testing Discoveries`. PASS if all discovery entries are written and committed to the branch — OPEN status is expected and acceptable (routes to Builder after merge). FAIL only if QA has uncommitted discovery notes (found bugs but did not commit them). |
| `complete_commit_made` | Run `git log main..HEAD --oneline`. For every in-scope feature that is fully clean (all scenarios pass, zero OPEN discoveries), a `[Complete]` commit must exist. PASS if all in-scope features have open discoveries (no clean features requiring a completion commit). FAIL only when a clean feature exists that has no `[Complete]` commit. |

### 5. Report Checklist

Print a compact table:

```
Handoff Checklist — <role> / <branch>
────────────────────────────────────────
  git_clean          PASS
  branch_naming      PASS
  critic_report      PASS
  spec_gate_pass     FAIL  — 2 HIGH items on features/foo.md
  impl_notes_stub    PASS
  visual_spec_complete PASS
────────────────────────────────────────
```

### 6. Decision

**If any item is FAIL:**
- Print: "Handoff checks failed — merge blocked."
- List each failing item with its reason.
- Do NOT merge. Stop here.

**If all items are PASS (or WARNING only):**
- Run: `git -C <PROJECT_ROOT> merge --ff-only <current-branch>`
- If `--ff-only` fails (diverged despite pre-flight): print "Branches diverged — run /pl-work-pull to rebase, then retry." Do NOT force merge. (This should be rare since Step 3b now catches DIVERGED up front.)

### 7. Report

On successful merge:
```
Merged <branch> into main (N commits).
```

## Notes

- Does NOT push to remote. Use `git push origin main` separately if needed.
- Auto-pull uses `git rebase main` to preserve linear history required by `--ff-only` merge to main.
- The agent evaluates all checklist items directly from file contents and git output — no shell script is invoked.
