**Purlin command: shared (all roles)**

## Path Resolution

Read `.purlin/config.json` and extract `tools_root` (default: `"tools"`). Resolve project root via `PURLIN_PROJECT_ROOT` env var or by climbing from CWD until `.purlin/` is found. Set `TOOLS_ROOT = <project_root>/<tools_root>`.

---

Run `${TOOLS_ROOT}/cdd/scan.sh` and summarize the scan results:

- Feature counts by status (TODO / TESTING / COMPLETE)
- Your mode-specific action items, highest priority first. Each item includes a reason explaining WHY the status was assigned.
- Any open discoveries or tombstones requiring attention

**Status values and what they mean:**

| Mode | Status | Meaning |
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

**PM-specific: Uncommitted Changes Check**

After completing the standard output above, if you are the PM, check for uncommitted changes:

1.  Run `git status` and `git diff` to identify staged changes, unstaged modifications, and untracked files.
2.  **PM-owned files** (`features/*.md`, `features/*.impl.md`, `instructions/*.md`, `.purlin/*.md`, `README.md`, `.gitignore`, `.purlin/release/*.json`, `.purlin/config.json`):
    *   Present a summary of changed files grouped by change type (new, modified, deleted).
    *   Read the diffs to understand the substance of each change.
    *   Propose a commit message following the project's commit convention (e.g., `spec(feature_name): add edge-case scenarios`, `docs(readme): update release history`). The message must reflect the "why" not just the "what."
    *   Ask the user: **"These PM-owned files have uncommitted changes. Commit with the above message?"**
3.  **Non-PM-owned files** (Engineer source, scripts, tests, etc.): Note them in the output but take no action -- the Engineer handles their own commits.
4.  **Clean working tree:** Report "No uncommitted changes."
