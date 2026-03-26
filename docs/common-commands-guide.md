# Common Commands Guide

Commands you can run in any mode — project status, mode switching, collaboration, and session management.

---

## Checking Project Status

```
/pl-status
```

Scans the project and shows what needs doing, organized by mode. Each item includes a reason annotation so you know why it's listed.

Output includes:

- Feature counts by lifecycle (TODO / TESTING / COMPLETE / TOMBSTONE)
- Work items grouped by mode, highest priority first
- Open discoveries requiring attention
- Active worktrees (if any)
- A suggestion for which mode to enter

Run this whenever you want to know what's next. It's the starting point after every session launch.

---

## Switching Modes

```
/pl-mode              # Show current mode and available commands
/pl-mode pm           # Switch to PM mode
/pl-mode engineer     # Switch to Engineer mode
/pl-mode qa           # Switch to QA mode
```

With no argument, shows your current mode and its commands. With an argument, switches to that mode.

If you have uncommitted changes when switching, the agent asks whether to commit first. Uncommitted work isn't lost — it carries into the new mode if you choose not to commit.

You can also activate a mode by running any mode-specific skill directly. For example, `/pl-spec` activates PM mode, `/pl-build` activates Engineer, and `/pl-verify` activates QA.

| Mode | What It Does | Write Access |
|------|-------------|--------------|
| `pm` | Spec authoring, design anchors | Feature specs, design/policy anchors |
| `engineer` | Build, test, delivery | Code, tests, scripts, companions |
| `qa` | Verification, discovery, regression | Discovery sidecars, QA tags, regression JSON |

---

## Searching Specs

```
/pl-find <topic>
```

Searches all feature specs, anchor nodes, and instruction files for coverage of a topic. Reports:

- Which feature spec covers it (file, section, and scenario)
- Whether an anchor node governs the concern
- Whether coverage exists only in process/instruction files
- A recommendation: new spec needed, refinement needed, anchor update needed, or already covered

**Examples:**

```
/pl-find authentication       # Where is auth covered?
/pl-find error handling       # Any specs for error states?
/pl-find dark mode            # Is there a design anchor for theming?
```

---

## Session Recovery

```
/pl-resume                    # Restore after context clear or restart
/pl-resume save               # Save checkpoint before clearing context
/pl-resume merge-recovery     # Resolve pending worktree merge failures
```

The agent runs `/pl-resume` automatically at the start of every session. You'll use it manually in two situations:

**Saving before a context clear:** When you're about to run `/clear` or close the terminal and want to pick up where you left off:

```
/pl-resume save
/clear
```

The checkpoint captures your current mode, in-progress work, completed items, and next steps. On the next session start, the agent restores this state automatically.

**Resolving failed merges:** If a worktree merge failed (e.g., due to conflicts), the agent detects it at startup. You can also trigger resolution manually:

```
/pl-resume merge-recovery
```

---

## Branch Collaboration

```
/pl-remote push                          # Push current branch to remote
/pl-remote pull                          # Pull remote changes into local
/pl-remote pull feature-xyz              # Pull a specific branch
/pl-remote add                           # Configure a git remote (interactive)
/pl-remote add git@github.com:org/repo   # Configure with URL
/pl-remote branch create feature-xyz     # Create and switch to a new branch
/pl-remote branch join feature-xyz       # Switch to an existing branch
/pl-remote branch leave                  # Return to main
/pl-remote branch list                   # List collaboration branches
```

Manages branch-based collaboration with safety checks: push/pull verify sync state before acting, and force-push is never allowed.

**Typical workflow:**

```
/pl-remote branch create my-feature      # Start a branch
# ... do work, commit ...
/pl-remote push                          # Share your work
# ... teammate pushes changes ...
/pl-remote pull                          # Get their changes
/pl-remote branch leave                  # Done, back to main
```

The remote name defaults to `origin`. Override it in `.purlin/config.json` under `branch_collab.remote`.

---

## Comparing Branches

```
/pl-whats-different
```

Shows a plain-English summary of what changed on the remote collaboration branch compared to your local `main`. Must be run from the `main` branch.

When a mode is active, produces a role-specific briefing: PM sees spec changes, Engineer sees code changes, QA sees verification state changes.

**Setup:** Requires an active collaboration branch (set up via `/pl-remote branch create` or `/pl-remote branch join`).

---

## Editing Project Overrides

```
/pl-override-edit
```

Opens your project's `PURLIN_OVERRIDES.md` for guided editing. The agent:

1. Reads the current override file and the corresponding base file.
2. Scans for conflicts, warnings, and redundancies.
3. Applies your proposed change (additive only — no deletions).
4. Asks for confirmation before writing.

Each mode can only edit its own section of the overrides file. Use `--scan-only` to check for conflicts without making changes:

```
/pl-override-edit --scan-only
```

---

## Managing Worktrees

```
/pl-worktree list              # Show all worktrees and their status
/pl-worktree cleanup-stale     # Remove stale/orphaned worktrees
```

Worktrees are isolated copies of the repository used for parallel feature builds. You typically don't create them manually — the agent spawns them during `/pl-build` when a delivery plan has independent features.

`list` shows each worktree's label, mode, PID, status (active/stale/orphaned), and age. `cleanup-stale` removes dead worktrees, prompting before discarding any with uncommitted changes.

---

## Agentic Toolbox

```
/pl-toolbox                          # Interactive menu
/pl-toolbox list                     # Show all tools
/pl-toolbox run <tool>               # Execute a tool
/pl-toolbox run tool1 tool2          # Run multiple tools sequentially
/pl-toolbox create                   # Create a new project tool
/pl-toolbox add <git-url>            # Download a community tool
```

Tools are independent, agent-executable units — scripts, checklists, or instructions that the agent can run on demand. Three categories:

| Category | Location | Description |
|----------|----------|-------------|
| Purlin | Framework-distributed | Read-only, bundled with Purlin |
| Project | `.purlin/toolbox/` | Your project-specific tools |
| Community | Downloaded via `add` | Shared tools from git repos |

**Common operations:**

- `list` to see what's available
- `run` to execute (by name or ID — fuzzy matching supported)
- `create` to build a new tool (walks you through it)
- `add` to install a community tool from a git URL

---

## Updating Purlin

```
/pl-update-purlin
/pl-update-purlin --dry-run
```

Updates the Purlin submodule to the latest version. The agent:

1. Fetches the latest version and shows what changed.
2. Scans for conflicts with your local customizations.
3. Advances the submodule.
4. Refreshes commands and config.
5. Resolves conflicts with three-way diffs.
6. Cleans up stale artifacts from previous versions.

Use `--dry-run` to preview changes without modifying anything. See the [Installation Guide](installation-guide.md) for manual update steps.

---

## Reporting Framework Bugs

```
/pl-purlin-issue
/pl-purlin-issue "scan crashes when config.json is empty"
```

Generates a structured bug report for the Purlin framework itself (not project-level bugs — use `/pl-discovery` for those). The agent collects:

- Your description and expected behavior
- Purlin version, deployment mode, and git state
- Relevant error output from the conversation

The output is a copy-paste-ready report formatted for a Purlin Engineer debugging session.

---

## Getting Help

```
/pl-help
```

Prints the full command table for your current mode. If no mode is active, shows all commands across all modes.

---

## Mode-Specific Skills

These commands activate and are documented in their respective mode guides:

- **PM mode:** `/pl-spec`, `/pl-anchor`, `/pl-design-ingest`, `/pl-design-audit` — see [PM Mode Guide](pm-agent-guide.md)
- **Engineer mode:** `/pl-build`, `/pl-unit-test`, `/pl-web-test`, `/pl-delivery-plan`, `/pl-infeasible`, `/pl-propose`, `/pl-spec-code-audit` — see [Engineer Mode Guide](engineer-agent-guide.md)
- **QA mode:** `/pl-verify`, `/pl-complete`, `/pl-discovery`, `/pl-regression`, `/pl-smoke`, `/pl-qa-report` — see [QA Mode Guide](qa-agent-guide.md)
