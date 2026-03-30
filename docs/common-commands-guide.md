# Common Commands Guide

Commands you can run in any mode — project status, mode switching, collaboration, and session management.

---

## Checking Project Status

```
purlin:status
```

Scans the project and shows what needs doing, organized by mode. Each item includes a reason annotation so you know why it's listed.

Output includes:

- Feature counts by lifecycle (TODO / TESTING / COMPLETE / TOMBSTONE)
- Work items grouped by mode, highest priority first
- Open discoveries requiring attention
- Active worktrees (if any)
- A suggestion for which mode to enter (when no mode is active)

Run this whenever you want to know what's next. It's the starting point after every session launch.

---

## Switching Modes

```
purlin:mode              # Show current mode and available commands
purlin:mode pm           # Switch to PM mode
purlin:mode engineer     # Switch to Engineer mode
purlin:mode qa           # Switch to QA mode
```

With no argument, shows your current mode and its commands. With an argument, switches to that mode.

If you have uncommitted changes when switching, the agent asks whether to commit first. Uncommitted work isn't lost — it carries into the new mode if you choose not to commit.

You can also activate a mode by running any mode-specific skill directly. For example, `purlin:spec` activates PM mode, `purlin:build` activates Engineer, and `purlin:verify` activates QA.

| Mode | What It Does | Write Access |
|------|-------------|--------------|
| `pm` | Spec authoring, design anchors | Feature specs, design/policy anchors |
| `engineer` | Build, test, delivery | Code, tests, scripts, companions |
| `qa` | Verification, discovery, regression | Discovery sidecars, QA tags, regression JSON |

---

## Searching Specs

```
purlin:find <topic>
```

Searches all feature specs, anchor nodes, and instruction files for coverage of a topic. Reports:

- Which feature spec covers it (file, section, and scenario)
- Whether an anchor node governs the concern
- Whether coverage exists only in process/instruction files
- A recommendation: new spec needed, refinement needed, anchor update needed, or already covered

**Examples:**

```
purlin:find authentication       # Where is auth covered?
purlin:find error handling       # Any specs for error states?
purlin:find dark mode            # Is there a design anchor for theming?
```

---

## Session Recovery

**You do not need to run `purlin:resume` to start working.** The `SessionStart` hook handles context recovery automatically on every launch. Just invoke any skill directly (e.g., `purlin:build`, `purlin:spec`, `purlin:mode engineer`).

Use `purlin:resume` manually in two situations:

```
purlin:resume                           # Restore after /clear or context compaction
purlin:resume save                      # Save checkpoint before clearing context
purlin:resume merge-recovery            # Resolve pending worktree merge failures
```

Recovery flags (used when restoring a session):

```
purlin:resume --mode engineer           # Restore and activate a mode
purlin:resume --build                   # Shortcut: Engineer mode + auto-start
purlin:resume --verify [feature]        # Shortcut: QA mode + auto-start
purlin:resume --worktree --build        # Isolated worktree + Engineer auto-start
purlin:resume --yolo                    # Enable auto-approve for permissions (persists)
purlin:resume --no-yolo                 # Disable auto-approve (persists)
purlin:resume --effort <high|medium>    # Set effort level for this session
```

The two situations where you use it manually:

**Saving before a context clear:** When you're about to run `/clear` or close the terminal and want to pick up where you left off:

```
purlin:resume save
/clear
```

The checkpoint captures your current mode, in-progress work, completed items, and next steps. On the next session start, the agent restores this state automatically.

**Resolving failed merges:** If a worktree merge failed (e.g., due to conflicts), the agent detects it at startup. You can also trigger resolution manually:

```
purlin:resume merge-recovery
```

---

## Branch Collaboration

```
purlin:remote push                          # Push current branch to remote
purlin:remote pull                          # Pull remote changes into local
purlin:remote pull feature-xyz              # Pull a specific branch
purlin:remote add                           # Configure a git remote (interactive)
purlin:remote add git@github.com:org/repo   # Configure with URL
purlin:remote branch create feature-xyz     # Create and switch to a new branch
purlin:remote branch join feature-xyz       # Switch to an existing branch
purlin:remote branch leave                  # Return to main
purlin:remote branch list                   # List collaboration branches
```

Manages branch-based collaboration with safety checks: push/pull verify sync state before acting, and force-push is never allowed.

**Typical workflow:**

```
purlin:remote branch create my-feature      # Start a branch
# ... do work, commit ...
purlin:remote push                          # Share your work
# ... teammate pushes changes ...
purlin:remote pull                          # Get their changes
purlin:remote branch leave                  # Done, back to main
```

The remote name defaults to `origin`. Override it in `.purlin/config.json` under `branch_collab.remote`.

---

## Comparing Branches

```
purlin:whats-different
```

Shows a plain-English summary of what changed on the remote collaboration branch compared to your local `main`. Must be run from the `main` branch.

When a mode is active, produces a role-specific briefing: PM sees spec changes, Engineer sees code changes, QA sees verification state changes.

**Setup:** Requires an active collaboration branch (set up via `purlin:remote branch create` or `purlin:remote branch join`).

---

---

## Managing Worktrees

```
purlin:worktree list              # Show all worktrees and their status
purlin:worktree cleanup-stale     # Remove stale/orphaned worktrees
purlin:worktree cleanup-stale --dry-run   # Preview what would be cleaned
```

Worktrees are isolated copies of the repository used for parallel feature builds. You typically don't create them manually — the agent spawns them during `purlin:build` when a delivery plan has independent features.

`list` shows each worktree's label, mode, PID, status (active/stale/orphaned), and age. `cleanup-stale` removes dead worktrees, prompting before discarding any with uncommitted changes.

---

## Agentic Toolbox

```
purlin:toolbox                          # Interactive menu
purlin:toolbox list                     # Show all tools
purlin:toolbox run <tool>               # Execute a tool
purlin:toolbox run tool1 tool2          # Run multiple tools sequentially
purlin:toolbox create                   # Create a new project tool
purlin:toolbox add <git-url>            # Download a community tool
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
purlin:update                    # Update to latest release tag
purlin:update v0.8.7             # Update to a specific version
purlin:update --dry-run          # Preview changes without modifying anything
purlin:update --auto-approve     # Apply without confirmation prompts
```

Updates the Purlin plugin to the latest release tag. This ensures you only pull tagged releases, never unreleased work-in-progress. Pass a specific version to target a particular release.

The agent:

1. Fetches the latest version and resolves the target release tag.
2. Scans for conflicts with your local customizations.
3. Refreshes skills, hooks, and the MCP server.
4. Resolves conflicts with three-way diffs.
5. Cleans up stale artifacts from previous versions.

See the [Installation Guide](installation-guide.md) for details.

---

## Reporting Framework Bugs

```
purlin:purlin-issue
purlin:purlin-issue "scan crashes when config.json is empty"
```

Generates a structured bug report for the Purlin framework itself (not project-level bugs — use `purlin:discovery` for those). The agent collects:

- Your description and expected behavior
- Purlin version, deployment mode, and git state
- Relevant error output from the conversation

The output is a copy-paste-ready report formatted for a Purlin Engineer debugging session.

---

## Getting Help

```
purlin:help
```

Prints the full command table for your current mode. If no mode is active, shows all commands across all modes.

---

## Mode-Specific Skills

These commands activate and are documented in their respective mode guides:

- **PM mode:** `purlin:spec`, `purlin:anchor`, `purlin:invariant`, `purlin:design-audit` — see [PM Mode Guide](pm-agent-guide.md)
- **Engineer mode:** `purlin:build`, `purlin:unit-test`, `purlin:web-test`, `purlin:delivery-plan`, `purlin:server`, `purlin:infeasible`, `purlin:propose`, `purlin:spec-code-audit`, `purlin:spec-from-code`, `purlin:tombstone` — see [Engineer Mode Guide](engineer-agent-guide.md)
- **QA mode:** `purlin:verify`, `purlin:complete`, `purlin:discovery`, `purlin:regression`, `purlin:smoke`, `purlin:qa-report`, `purlin:fixture` — see [QA Mode Guide](qa-agent-guide.md)
