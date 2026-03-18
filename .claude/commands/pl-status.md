**Purlin command: shared (all roles)**

Run `tools/cdd/status.sh` and summarize:

- Feature counts by status (TODO / TESTING / COMPLETE)
- Your role-specific action items, highest priority first. Each item includes a reason (from `role_status_reason`) explaining WHY the status was assigned.
- Any open discoveries or tombstones requiring attention

**Role-filtered shortcut:** If you know your role, use `tools/cdd/status.sh --role <role>` for a filtered view containing only your features and action items.

**Status values and what they mean:**

| Role | Status | Meaning |
|------|--------|---------|
| Architect | DONE | No spec gaps, no pending disputes or decisions |
| Architect | TODO | Spec gate failures, unacknowledged decisions, or open disputes |
| Builder | DONE | Tests pass, no open BUGs, feature not in TODO lifecycle |
| Builder | TODO | Feature in TODO lifecycle (spec modified or never built) |
| Builder | FAIL | tests.json exists with status FAIL |
| Builder | BLOCKED | OPEN SPEC_DISPUTE suspends work |
| Builder | INFEASIBLE | Builder halted work, Architect must revise spec |
| QA | CLEAN | Tests pass, no discoveries |
| QA | TODO | Feature in TESTING with manual scenarios |
| QA | FAIL | OPEN BUGs exist |
| QA | DISPUTED | OPEN SPEC_DISPUTEs exist |
| QA | N/A | No test coverage or no QA-relevant items |

**Architect-specific: Uncommitted Changes Check**

After completing the standard output above, if you are the Architect, check for uncommitted changes:

1.  Run `git status` and `git diff` to identify staged changes, unstaged modifications, and untracked files.
2.  **Architect-owned files** (`features/*.md`, `features/*.impl.md`, `instructions/*.md`, `.purlin/*.md`, `README.md`, `.gitignore`, `.purlin/release/*.json`, `.purlin/config.json`):
    *   Present a summary of changed files grouped by change type (new, modified, deleted).
    *   Read the diffs to understand the substance of each change.
    *   Propose a commit message following the project's commit convention (e.g., `spec(feature_name): add edge-case scenarios`, `docs(readme): update release history`). The message must reflect the "why" not just the "what."
    *   Ask the user: **"These Architect-owned files have uncommitted changes. Commit with the above message?"**
3.  **Non-Architect-owned files** (Builder source, scripts, tests, etc.): Note them in the output but take no action -- the Builder handles their own commits.
4.  **Clean working tree:** Report "No uncommitted changes."
