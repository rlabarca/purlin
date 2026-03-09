# Implementation Notes: CDD Isolated Teams Mode

The CDD dashboard is read-only with respect to worktree monitoring — it uses `git -C <path>` to query state without modifying anything, and Isolated Teams Mode detection happens on every `/status.json` call.

The `/isolate/create` and `/isolate/kill` endpoints are intentional exceptions to the read-only pattern: they delegate to `tools/collab/create_isolation.sh` and `tools/collab/kill_isolation.sh` respectively. These endpoints are explicit write operations initiated by the user; they are not invoked automatically by the dashboard's status polling.

**Name parsing from path:** `_name_from_path(worktree_path)` extracts the final directory component of the worktree path. For `.worktrees/feat1`, this returns `"feat1"`. `_role_from_branch()` is removed entirely.

**`isolations_active` replaces `collab_mode`:** The `/status.json` field is renamed. Any consumer that previously read `collab_mode` must update to `isolations_active`. The semantics are equivalent: true when at least one worktree is detected under `.worktrees/`.

**`get_isolation_worktrees()` replaces `get_collab_worktrees()`:** Same detection logic (git worktree list, filter to `.worktrees/` paths), renamed function.

**Delivery phase detection:** `_read_delivery_phase(worktree_path)` reads `<worktree_path>/.purlin/cache/delivery_plan.md`, parses for a line matching `status: IN_PROGRESS` in a phase block, and extracts current/total. Returns `None` if the file is absent or no IN_PROGRESS phase exists. Parse failures are silently ignored (missing or malformed plans do not block status polling).

**Collaboration branch abstraction:** `_get_collaboration_branch()` returns the branch the project root is currently on (`git rev-parse --abbrev-ref HEAD`). This is the active branch during branch collaboration, `main` otherwise. All worktree comparison functions (`_worktree_state`, `_compute_sync_state`) accept a `collab_branch` parameter; `get_isolation_worktrees()` resolves it once and passes it through.

**Retained from prior implementation (tribal knowledge):**
- `commits_ahead`: uses `git rev-list --count <collab_branch>..HEAD` in `_worktree_state()`.
- `last_commit`: uses `git log -1 --format='%h %s (%cr)'` in `_worktree_state()`.
- `sync_state`: computed by `_compute_sync_state(branch, collab_branch)` running two `git log` range queries from PROJECT_ROOT. Query 1: `git log <branch>..<collab_branch> --oneline` (behind check). Query 2: `git log <collab_branch>..<branch> --oneline` (ahead check). Returns "DIVERGED" if both non-empty, "BEHIND" if only query 1 non-empty, "AHEAD" if only query 2 non-empty, "SAME" if both empty.
- `committed`: computed via `git diff <collab_branch>...<branch> --name-only` (three-dot) run from PROJECT_ROOT. Three-dot diffs against common ancestor — always empty for SAME/BEHIND, reflects only branch-side changes for AHEAD/DIVERGED. May be all-zero for AHEAD/DIVERGED if commits are `--allow-empty`.
- `uncommitted`: computed via `git -C <path> status --porcelain` run from the worktree directory. Captures staged, unstaged, and untracked changes. Independent of `local_branch_diff` state — a worktree at SAME can have uncommitted changes. For renames (`XY old -> new`), the new path is used for categorization. `.purlin/` files excluded.
- `_handle_config_agents()` propagates updated config to all active worktree `.purlin/config.local.json` files after the project root write. Failures collected as `warnings`.
- Agent Config heading annotation applied server-side in `generate_html()`.
- Kill modal: dedicated overlay element (`kill-modal-overlay`) with 3-state content (dirty / unsynced / clean) and per-isolation name scoping. Populated by `showKillModal(name, dryRunResponse)`.

**Shared helpers:** `_categorize_files(lines)` categorizes a list of file paths into `{specs, tests, other}` counts (shared by committed and uncommitted parsing). `_format_category_counts(counts)` renders a counts dict as space-separated category text for the HTML table cells.

**Section structure:** The dashboard renders four top-level collapsible sections: ACTIVE, COMPLETE, LOCAL BRANCH, ISOLATED TEAMS. LOCAL BRANCH and ISOLATED TEAMS are peers in the DOM — sibling `<section>` elements at the same level. ISOLATED TEAMS is NOT a child of LOCAL BRANCH. LOCAL BRANCH expands to show Local (main) git status; ISOLATED TEAMS expands to show the creation row and Sessions table.

**Input value persistence:** The name input's value is saved to a JS module-level variable (e.g., `let _pendingIsolationName = ""`) immediately before any DOM refresh. After the DOM update, the value is written back to the input element and the Create button's disabled state is re-evaluated. On successful create, the module-level variable is cleared. This avoids any localStorage dependency and works within the existing polling cycle.

**Name input styling:** Inherits the same CSS class or inline styles as the header filter input. Key tokens: `background: var(--purlin-surface)`, `border: 1px solid var(--purlin-border)`, `color: var(--purlin-primary)`, `placeholder color: var(--purlin-dim)`. This ensures correct theme switching without additional CSS.

**Collapsed section label severity logic:** `_collapsed_label(worktrees)` computes the severity order: DIVERGED > BEHIND > AHEAD > SAME. It iterates the list once, tracking the highest-severity state seen, then returns the CSS class and label string. If `worktrees` is empty, it returns `("", "ISOLATED TEAMS")`.

**Worktree detection alternative:** When `PURLIN_PROJECT_ROOT` is set, `test -f "$PURLIN_PROJECT_ROOT/.git"` confirms a worktree — in a git worktree the `.git` entry is a file pointer, not a directory. The primary detection method (`git rev-parse --abbrev-ref HEAD` matching `^isolated/`) is sufficient; this is a secondary option.

**Resolved discoveries (pruned from User Testing Discoveries):**
- SPEC_DISPUTE — Length validation: `maxlength` attribute prevents over-length input at the browser level; no inline message needed. Character validation (non-`[a-zA-Z0-9_-]`) still shows disabled button + inline message. Scenario renamed to "New Isolation Input Rejects Invalid Characters" (feat@1 test input). Verified 2026-02-24.
- SPEC_DISPUTE — Name length limit raised from 8 to 12 characters: updated HTML `maxlength`, JS `validateIsolationName()`, hint text, and `create_isolation.sh` server-side validation.
- INTENT_DRIFT — Focus restoration on auto-refresh: `refreshStatus()` saves `document.activeElement === isoInput` before DOM refresh and calls `restoredInput.focus()` after value restore.
- DISCOVERY (acknowledged) — Creation row padding: added `padding-top:4px` to creation row container div so the input focus ring doesn't clip under the section header. Cosmetic fix, no scenario needed.
- BUG — `pl-isolated-push`/`pl-isolated-pull` isolation startup table: added both commands to startup table in ARCHITECT_BASE.md, BUILDER_BASE.md, and QA_BASE.md. Autocomplete visibility on main is a platform limitation outside instruction-file control.

**Bug fixes preserved from prior implementation (do not regress):**
- Modal button styling uses `btn-critic` class (not `btn` — no CSS definition).
- Dirty detection in `kill_isolation.sh` excludes `.purlin/` files (grep -v filter).
- Four-state `sync_state` + theme colors: SAME -> `st-good` (green), AHEAD -> `st-todo` (yellow), BEHIND -> `st-todo` (yellow), DIVERGED -> `st-disputed` (orange/`--purlin-status-warning`).
- `committed` uses three-dot diff (`git diff main...<branch>`) not two-dot — three-dot shows only branch-side changes from common ancestor; two-dot shows all differences between tips (including main-side changes, which was a bug for BEHIND state).
- Auto-refresh timer paused during create/kill requests to prevent error messages being wiped.

**Staleness banner:** `_staleness_banner_html(worktrees)` counts worktrees with `sync_state == "DIVERGED"` and renders a warning banner above the Sessions table when count > 0. Banner includes worktree count text and a dismiss button. Inserted in `generate_html()` between the creation row and sessions table.

**Isolation digest (What's Different?):** Per-worktree cached digest, modeled after the collaboration-level What's Different feature. `_is_isolation_digest_stale(worktree_path, isolation_name)` compares the digest file's recorded tip SHA against the current worktree HEAD — stale if they differ. The dashboard renders a "What's Different?" button per isolation row (hidden when `sync_state == "SAME"`). Clicking opens a modal (`iso-wd-modal-overlay`) that shows the cached digest content or a "no digest" message. Users can regenerate via the modal. Endpoints: `POST /isolate/<name>/whats-different/generate` triggers `tools/collab/whats_different.sh` for the worktree, `GET /isolate/<name>/whats-different/read` returns cached digest content. `_parse_isolation_name_from_path(path)` extracts the isolation name from URL paths matching `/isolate/<name>/...`.

**Rename: `main_diff` → `sync_state`, `_compute_main_diff` → `_compute_sync_state`:** Applied throughout serve.py, test file, and this companion file. The HTML column header was also renamed from "Main Diff" to "Sync State". The old names were confusing because sync is relative to the collaboration branch (not always `main`).
