**Purlin command: shared (all roles)**

Run `tools/cdd/status.sh`, read `CRITIC_REPORT.md`, and summarize:

- Feature counts by status (TODO / TESTING / COMPLETE)
- Your role-specific action items from the Critic report, highest priority first
- Any open discoveries or tombstones requiring attention

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
