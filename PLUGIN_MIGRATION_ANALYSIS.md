# Purlin: Submodule to Claude Plugin Migration Analysis

## Context

Purlin is currently distributed as a git submodule consumed by projects. This creates friction: multi-step onboarding (`git submodule add`, `pl-init.sh`, symlink management), manual version management (`git pull` in submodule), extensive path resolution logic for submodule-safe code, and a 500-line launcher script (`pl-run.sh`) to orchestrate sessions. Claude Code now offers a native plugin system designed for exactly this distribution model. This analysis maps Purlin's complete feature set to the plugin architecture to evaluate feasibility, gains, losses, and new capabilities.

---

## 1. Core User Stories (What Purlin Delivers)

These are the outcomes users get from Purlin, abstracted from implementation. Any migration must preserve these.

| # | User Story | Key Mechanism Today |
|---|-----------|-------------------|
| 1 | **Specs before code** -- PM writes feature specs; Engineer implements from them; QA verifies against them | Skills (`/pl-spec`, `/pl-build`, `/pl-verify`), CDD scan engine, `/pl-status` |
| 2 | **Mode-gated writes** -- Agent can only write files appropriate to its current role | Prompt-level Mode Guard in PURLIN_BASE.md, `file_classification.md` reference |
| 3 | **Deviation tracking** -- Implementation divergences from spec are recorded, never silently lost | Companion files (`*.impl.md`), companion file commit covenant, pre-switch gate |
| 4 | **Structured QA** -- Scenarios defined in specs, executed automatically, discoveries routed to responsible parties | QA skills, regression JSON, harness runner, discovery sidecars |
| 5 | **Phased delivery** -- Large changes split into dependency-ordered phases with parallel execution | Delivery plan, execution groups, `engineer-worker` subagents in worktrees |
| 6 | **Knowledge colocation** -- Implementation notes, QA findings, and standards live alongside feature specs | Companions, discovery sidecars, anchor nodes in `features/` |
| 7 | **Session continuity** -- Agent state survives context clears and terminal restarts | PID-scoped checkpoints, `/pl-resume` 7-step protocol |
| 8 | **Invariant constraints** -- Externally-sourced immutable rules enforced during builds | `features/i_*.md`, FORBIDDEN pattern pre-scan, invariant.py |
| 9 | **Design system integration** -- Figma designs ingested, token maps created, visual verification via triangulation | Figma MCP, Playwright MCP, design anchors, visual spec convention |
| 10 | **Project state awareness** -- Authoritative scan of all features, states, test results, dependency graphs | `scan.py` (1100+ lines), `graph.py`, `/pl-status` |
| 11 | **Terminal identity** -- Visual indication of mode + branch in iTerm2/Warp badges and titles | `identity.sh`, launcher pre-session badge, mode switch updates |
| 12 | **Worktree concurrency** -- Parallel feature builds in isolated git worktrees with merge serialization | Launcher `--worktree`, `merge-worktrees.sh` hook, merge lock, breadcrumbs |
| 13 | **Agentic toolbox** -- Independent tools (spec_check, spec_map, invariant_audit) runnable at any time | 3-tier toolbox (Purlin/Project/Community), resolution engine |

---

## 2. Mapping User Stories to Plugin Components

### Story 1: Specs Before Code
**Plugin mapping: Direct.** All 36 skill files (`.claude/commands/*.md`) become `skills/*/SKILL.md` in the plugin's `skills/` directory, namespaced as `purlin:pl-build`, `purlin:pl-spec`, etc. The scan engine (`scan.py`, `graph.py`) moves to `scripts/cdd/`. Feature specs remain project-level in `features/`. The skill content (the full protocol) translates 1:1 -- skill files are already self-contained markdown prompts.

### Story 2: Mode-Gated Writes
**Plugin mapping: Improved.** Today this is prompt-level enforcement (agent is instructed not to write wrong-mode files). The plugin's **`PreToolUse` hook** enables mechanical enforcement: a hook script intercepts every `Write`/`Edit`/`NotebookEdit` call, checks the target file against `file_classification.json` and the current mode state, and returns exit code 2 (blocking error) if the write violates boundaries. The agent literally cannot write wrong-mode files. This is the single biggest architectural improvement.

### Story 3: Deviation Tracking
**Plugin mapping: Direct + Enhanced.** Companion file protocols live in skill content (translates 1:1). The **`FileChanged` hook** adds continuous companion debt tracking -- whenever code files change, the hook can remind the agent about companion updates. Pre-switch gates remain in the `/pl-mode` skill (prompt-level, same as today).

### Story 4: Structured QA
**Plugin mapping: Direct.** QA skills become plugin skills. The `verification-runner` agent definition translates to `agents/verification-runner.md` with `isolation: worktree`. Harness runner scripts move to `scripts/test_support/`. Playwright and Figma MCP servers are declared in the plugin's `.mcp.json` and auto-started when the plugin is enabled.

### Story 5: Phased Delivery
**Plugin mapping: Direct.** Delivery plan skills translate 1:1. The `engineer-worker` agent definition with `isolation: worktree` is natively supported by the plugin agent system. **`WorktreeCreate`/`WorktreeRemove` hooks** provide lifecycle management that Purlin currently implements manually.

### Story 6: Knowledge Colocation
**Plugin mapping: Direct.** This is entirely a project-level convention. The plugin provides skills that create/manage colocated files and reference docs that define the convention. Reference documents ship at `${CLAUDE_PLUGIN_ROOT}/references/`.

### Story 7: Session Continuity
**Plugin mapping: Improved.** The **`SessionStart` hook** automatically triggers the restore protocol on every session start -- no more depending on the agent remembering to run `/pl-resume`. **`PreCompact` hook** auto-saves checkpoints before context compaction (currently requires manual `/pl-resume save`). Checkpoint storage moves to `${CLAUDE_PLUGIN_DATA}/checkpoints/` which persists across plugin updates.

### Story 8: Invariant Constraints
**Plugin mapping: Direct.** Invariant skills and validation scripts translate 1:1. The `PreToolUse` mode guard hook also blocks writes to `features/i_*.md` regardless of mode.

### Story 9: Design System Integration
**Plugin mapping: Direct.** Figma and Playwright MCP servers declared in plugin `.mcp.json`. Figma access token stored via plugin's `userConfig` mechanism (prompted at enable time, stored in macOS keychain). Design skills translate 1:1.

### Story 10: Project State Awareness
**Plugin mapping: Direct.** Scan engine scripts move to `scripts/cdd/`. Output remains in project `.purlin/cache/scan.json` (project scripts may read it). Path resolution simplifies: `${CLAUDE_PLUGIN_ROOT}/scripts` replaces `PURLIN_PROJECT_ROOT`-based climbing.

### Story 11: Terminal Identity
**Plugin mapping: Degraded.** The launcher currently sets terminal identity BEFORE the agent starts (`--name`, `--remote-control`). In the plugin model, the `SessionStart` hook fires AFTER session start -- brief period without identity. The Claude Code session name (visible in `claude --resume` picker) cannot be set by plugins. iTerm badge and terminal title can still be set via hook scripts.

### Story 12: Worktree Concurrency
**Plugin mapping: Mixed.** Agent `isolation: worktree` is native. `SessionEnd` hook handles merge-back. But the launcher's `--worktree` flag (create worktree before agent starts) has no plugin equivalent. Label assignment and merge lock serialization remain custom scripts.

### Story 13: Agentic Toolbox
**Plugin mapping: Direct.** Purlin tools bundled with plugin. Project and community tools remain project-level in `.purlin/toolbox/`. Toolbox management skills translate 1:1.

---

## 3. Advantages of the Plugin Approach

### 3.1 Onboarding: Multi-step to single command
**Today:** `git submodule add`, `pl-init.sh` (808-line script), symlink management, `.mcp.json` config, learn `pl-run.sh`.
**Plugin:** `claude plugin install purlin`. Done. User config prompts appear at enable time (Figma token, default model). No submodule, no symlinks, no init script.

### 3.2 Updates: Git gymnastics to native versioning
**Today:** `cd purlin && git pull && cd .. && git add purlin && git commit`, then `pl-init.sh --upgrade` for schema changes. No rollback.
**Plugin:** `claude plugin update purlin`. Semantic versioning. Rollback via `claude plugin install purlin@1.2.3`. `${CLAUDE_PLUGIN_DATA}` persists across updates.

### 3.3 Mechanical mode guard enforcement (PreToolUse hook)
Today's mode guard is prompt-level -- the model is instructed not to write wrong-mode files. With `PreToolUse`, a hook script mechanically intercepts every write call and blocks violations with exit code 2. Transforms soft enforcement into a hard guarantee.

### 3.4 Automatic context recovery (SessionStart hook)
Today, recovery depends on the agent running `/pl-resume` (triggered by CLAUDE.md). If the agent starts without CLAUDE.md, recovery fails. With `SessionStart`, the plugin automatically triggers restore on every session start.

### 3.5 Auto-checkpoint before compaction (PreCompact hook)
Currently no automatic checkpoint save when context fills. Users must remember `/pl-resume save`. With `PreCompact`, the plugin auto-saves.

### 3.6 Isolation eliminates submodule safety mandate
The entire "Submodule Compatibility Mandate" (5-point checklist, pre-commit gate, test coverage for both deployment modes) exists because `tools/` is inside the project. As a plugin, `${CLAUDE_PLUGIN_ROOT}` is completely separate from the project. No path climbing, no `PURLIN_PROJECT_ROOT`, no submodule immutability enforcement needed.

### 3.7 Team sharing via scoped installation
**Today:** Every team member needs Purlin as a submodule at a consistent version.
**Plugin:** Installed once per user. Projects declare dependency in `.claude/settings.json`. Version pinning ensures consistency. Four scope levels (managed > project > local > user).

### 3.8 Namespace clarity
All skills namespaced as `purlin:pl-build` etc. No collision with project commands or other plugins. Auto-invocability preserved.

### 3.9 Marketplace discoverability
Listed in Claude Code marketplace with ratings, reviews, documentation. Teams discover and adopt without prior knowledge.

### 3.10 Companion file debt tracking (FileChanged hook)
`FileChanged` hook fires on code file modifications, enabling continuous companion debt reminders -- not just at mode switch time.

### 3.11 Composability
Purlin coexists with other plugins (deployment, monitoring, etc.) without conflict. Could theoretically be split into composable sub-plugins (purlin-core, purlin-design, purlin-qa).

---

## 4. Disadvantages of the Plugin Approach

### 4.1 Loss of launcher pre-session orchestration (MAJOR)
`pl-run.sh` (504 lines) runs BEFORE the agent starts. It provides:
- Interactive model/effort selection menu with saved preferences
- `--worktree` flag (creates worktree before session)
- Session naming (`--name`, `--remote-control` flags)
- Initial session message injection ("Begin Purlin session. Enter Engineer mode.")
- `--yolo` mode (`--dangerously-skip-permissions`)

The plugin's `SessionStart` hook fires AFTER session start. No plugin mechanism can replicate pre-session orchestration. **Mitigation:** A thin companion launcher script (50-80 lines) handles CLI flags and delegates to `claude --plugin-dir` or `claude` with env vars.

### 4.2 Prompt assembly splits into multiple injection points
Today, the launcher concatenates `PURLIN_BASE.md` (199 lines) + `PURLIN_OVERRIDES.md` (160 lines) via `--append-system-prompt-file` into one coherent document. In the plugin model, base instructions come from the plugin (via `settings.json` or `InstructionsLoaded` hook) and project overrides come from project CLAUDE.md or settings. The seamless single-document model splits into two separate sources with potentially different ordering.

### 4.3 State location bifurcation
Two state locations: `${CLAUDE_PLUGIN_DATA}` (plugin-specific, persists across updates) and project `.purlin/` (project-specific). Scan output, delivery plans, and toolbox configs must stay in `.purlin/` because project scripts may read them. Plugin-internal state (mode tracking) goes to `${CLAUDE_PLUGIN_DATA}`. Developers must understand which goes where.

### 4.4 Cross-plugin instruction conflicts
If a team uses Purlin + another plugin with different commit conventions or file ownership rules, there's no coordination mechanism. Today's unified instruction set guarantees Purlin has full behavioral control.

### 4.5 Testing infrastructure changes
Plugin-internal tests can't be run by consumer projects. The current test suite (`test_purlin_launcher.sh`, `test_purlin_scan.sh`, Python tests in `tools/test_support/`) must move to the plugin's CI/CD pipeline. Consumer projects lose the ability to verify their installation.

### 4.6 Skill naming length
`/pl-build` becomes `/purlin:pl-build` (or auto-invoked without prefix). Longer to type. Minor but daily friction.

---

## 5. New Capabilities Enabled (or Done Differently)

### 5.1 PreToolUse mode guard (NEW -- hard enforcement)
Script intercepts Write/Edit/NotebookEdit, checks file classification + mode state, blocks violations mechanically. Replaces prompt-level soft enforcement with a hard guarantee. This alone may justify the migration.

### 5.2 Automatic session recovery (DIFFERENT -- hook replaces CLAUDE.md instruction)
`SessionStart` hook fires automatically. No more depending on the agent reading CLAUDE.md and remembering `/pl-resume`. Works even with bare `claude` invocations.

### 5.3 Pre-compaction checkpoint (NEW)
`PreCompact` hook auto-saves session state before context window compaction. Currently impossible -- no hook point exists.

### 5.4 Continuous companion debt tracking (NEW)
`FileChanged` hook on code files tracks companion debt in real-time, not just at mode switch time.

### 5.5 Native worktree lifecycle (DIFFERENT)
`WorktreeCreate`/`WorktreeRemove` hooks replace manual worktree management in `pl-run.sh` and `manage.sh`.

### 5.6 Channels integration (NEW -- possible)
Plugin channels could enable: PM approves deviations via Slack message injected into session, QA findings auto-posted to a channel. Entirely new collaboration surface.

### 5.7 LSP for feature specs (NEW -- possible)
A custom LSP server could provide code intelligence for `.md` feature files: autocompletion of scenario references, prerequisite link validation, deviation tag syntax checking. No equivalent exists today.

### 5.8 Output styles (NEW)
Standardized, visually polished formatting for scan results, status reports, QA findings. Currently embedded as prose in skill files.

### 5.9 Plugin `userConfig` for credentials (DIFFERENT)
Figma tokens and other secrets stored in macOS keychain via plugin's native `userConfig` mechanism. Replaces manual config management. `${user_config.KEY}` substitution in MCP configs.

### 5.10 Scan refresh on file changes (NEW -- possible)
`FileChanged` hook on feature files, test results, or companion files could incrementally update the scan cache, keeping project state perpetually fresh without manual `scan.sh` invocations.

---

## 6. The `purlin:resume` Skill -- Eliminating the Launcher

Deep investigation of Claude Code's runtime APIs reveals that most "launcher-only" capabilities are actually available from within a running session. This means a `purlin:resume` skill can replace `pl-run.sh` almost entirely.

### 6.1 What `purlin:resume` Replaces

The current launcher (`pl-run.sh`, 504 lines) does these things before the agent starts:

| Launcher Capability | `purlin:resume` Alternative | Mechanism |
|---|---|---|
| Model selection | Agent frontmatter default + `claude --model` override | `agents/purlin.md` sets default model; user overrides per-session via CLI |
| Effort selection | `/effort` command mid-session | Effort CAN be changed mid-session -- no launcher needed |
| YOLO mode | `PermissionRequest` hook auto-approve | Hook returns `behavior: "allow"` when yolo flag is set (see 6.2) |
| Worktree creation | `EnterWorktree` tool | Agent calls `EnterWorktree` programmatically from within the session |
| Session naming | `/rename` command or Bash OSC escape | Available mid-session; names persist in resume picker |
| Terminal identity | `SessionStart` hook + Bash in skill | Hook sets initial badge; skill updates on mode switch |
| Prompt assembly | `settings.json` `agent` key | Agent definition replaces system prompt with PURLIN_BASE.md content |
| Session message | `SessionStart` hook context injection | Hook adds "Begin Purlin session" context automatically |
| Config persistence | Plugin `userConfig` + `.purlin/config.json` | Credentials in keychain; preferences in project config |
| Auto-update check | Plugin marketplace versioning | `claude plugin update purlin` replaces manual git pull |
| Cleanup on exit | `SessionEnd` hook | Merge worktrees, clear session state, clean empty worktrees |

### 6.2 YOLO Mode via PermissionRequest Hook

The `PermissionRequest` hook fires whenever a permission dialog is about to be shown. It CAN auto-approve:

```json
// hooks/hooks.json (simplified)
{
  "PermissionRequest": [{
    "hooks": [{
      "type": "command",
      "command": "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/permission-manager.sh"
    }]
  }]
}
```

The hook script checks a YOLO flag in `.purlin/config.json` or `${CLAUDE_PLUGIN_DATA}/session_state.json`:

```bash
#!/bin/bash
INPUT=$(cat)
YOLO=$(python3 -c "import json; c=json.load(open('.purlin/config.json')); print(c.get('agents',{}).get('purlin',{}).get('bypass_permissions','false'))")
if [ "$YOLO" = "true" ]; then
  echo '{"hookSpecificOutput":{"hookEventName":"PermissionRequest","decision":{"behavior":"allow"}}}'
fi
exit 0
```

**Key insight:** Since the `PermissionRequest` hook fires session-wide, subagents (engineer-worker, verification-runner) inherit this behavior. When the hook auto-approves, ALL permission dialogs are auto-approved -- including those from subagents in worktrees. This solves the parallel build permission blocker without needing `permissionMode` in agent definitions.

**Limitation:** Managed deny rules (enterprise/organization settings) still take precedence. For individual users and small teams, this is a non-issue. For enterprise deployments with managed settings, the companion launcher with `--dangerously-skip-permissions` remains the fallback.

**Toggling:** `purlin:resume --yolo` sets the flag in config. `purlin:resume --no-yolo` clears it. The flag persists across sessions (same as today's `pl-run.sh --yolo`).

### 6.3 Worktree Entry via EnterWorktree Tool

Claude Code exposes `EnterWorktree` and `ExitWorktree` as callable tools. The `purlin:resume` skill can invoke `EnterWorktree` programmatically:

```
purlin:resume --worktree --mode engineer
```

Flow:
1. Skill calls `EnterWorktree` (creates worktree, switches session into it)
2. Writes `.purlin_worktree_label` (W1, W2, etc.) and `.purlin_session.lock`
3. Sets terminal identity with worktree label: `Engineer (W1)`
4. Proceeds with normal startup (scan, status, mode activation)

On session end, the `SessionEnd` hook runs `merge-worktrees.sh` to merge back -- same as today.

### 6.4 Session Naming via /rename

The `/rename` command is available mid-session. `purlin:resume` can call it:

```
purlin:resume --mode engineer
→ internally runs: /rename "purlin | Engineer (main)"
```

The name appears in the `claude --resume` picker and the prompt bar. This fully replaces `--name` and `--remote-control`.

### 6.5 Prompt Assembly via Agent Key

The plugin's `settings.json` activates a default agent:
```json
{ "agent": "purlin" }
```

The `agents/purlin.md` file contains:
```yaml
---
name: purlin
description: Purlin unified workflow agent
model: claude-opus-4-6[1m]
effort: high
---

<full PURLIN_BASE.md content here>
```

This replaces the system prompt entirely with Purlin's instructions. Project-level `PURLIN_OVERRIDES.md` layers on top via CLAUDE.md:
```markdown
# CLAUDE.md
See .purlin/PURLIN_OVERRIDES.md for project-specific rules.
```

The two-layer instruction model is preserved: base from plugin agent, overrides from project CLAUDE.md. No launcher concatenation needed.

### 6.6 The Complete `purlin:resume` Skill

```
purlin:resume [OPTIONS]

Options:
  --mode <pm|engineer|qa>    Set starting mode
  --build                    Shortcut: --mode engineer --auto
  --verify [feature]         Shortcut: --mode qa --auto [feature]
  --pm                       Shortcut: --mode pm
  --worktree                 Enter an isolated git worktree
  --yolo                     Enable auto-approve for all permissions
  --no-yolo                  Disable auto-approve
  --effort <high|medium>     Set effort level for this session

  No options: run checkpoint recovery + scan + suggest mode
```

**Execution flow:**
1. Check for checkpoint -- restore if found (same as `/pl-resume`)
2. If `--worktree`: call `EnterWorktree`, set labels and lock
3. If `--yolo`/`--no-yolo`: update config flag (PermissionRequest hook reads it)
4. If `--effort`: run `/effort <level>`
5. Set terminal identity via Bash (iTerm badge + Warp tab + title)
6. Rename session via Bash (OSC escape or equivalent)
7. If `--mode`: activate mode, run scan, present work
8. If `--build`/`--verify`: activate mode + invoke `purlin:build` or `purlin:verify`
9. If no options: run scan, suggest mode, wait for user

### 6.7 What Still Requires a Companion Launcher

Only ONE thing cannot be done from within a session:

**Model selection.** The model is fixed at session start. The `agents/purlin.md` frontmatter sets a default (e.g., `claude-opus-4-6[1m]`), but per-session override requires `claude --model sonnet`.

For users who want per-session model choice, two options:
- **Shell alias:** `alias purlin='claude --model claude-opus-4-6[1m]'`, `alias purlin-fast='claude --model claude-sonnet-4-6'`
- **Minimal launcher (10 lines):**
  ```bash
  #!/bin/bash
  case "${1:-}" in
    --sonnet) shift; claude --model claude-sonnet-4-6 "$@" ;;
    --haiku)  shift; claude --model claude-haiku-4-5-20251001 "$@" ;;
    *)        claude "$@" ;;  # Uses agent default from settings.json
  esac
  ```

This is optional. Most users will use the agent default and never need it.

### 6.8 Remaining Gaps (Truly Cannot Be Replicated)

| Gap | Impact | Severity |
|---|---|---|
| Pre-session model selection menu | Users who frequently switch models lose the interactive menu | Low -- shell aliases or 10-line launcher cover this |
| Managed deny rule override | Enterprise deployments with strict managed settings can't use hook-based YOLO | Low -- affects only locked-down enterprise environments |
| Pre-switch gates as mechanical enforcement | No hook event for skill invocation; companion file gate remains prompt-level | None -- same as today, not a regression |

---

## 7. Repo Restructure: Current → Plugin Layout

The Purlin repo itself becomes the plugin. No separate distribution repo. The plugin system ignores files it doesn't recognize, so dev-only artifacts (features/, tests/, dev/) coexist harmlessly.

### Skill Naming Convention

All skills drop the `pl-` prefix. The plugin namespace provides the grouping:

| Current | Plugin |
|---|---|
| `/pl-build` | `purlin:build` |
| `/pl-verify` | `purlin:verify` |
| `/pl-spec` | `purlin:spec` |
| `/pl-mode` | `purlin:mode` |
| `/pl-status` | `purlin:status` |
| `/pl-resume` | `purlin:resume` (retired — consolidated into purlin:resume) |
| etc. | etc. |

### Current Repo Structure → Target Plugin Structure

```
rlabarca/purlin (CURRENT)               rlabarca/purlin (TARGET)
─────────────────────────               ─────────────────────────
                                        .claude-plugin/
                                        ├── plugin.json          ← NEW: manifest
.claude/
├── commands/pl-*.md (36 files)         skills/                  ← MOVED + RENAMED
├── agents/*.md                         ├── build/SKILL.md       (was .claude/commands/pl-build.md)
                                        ├── verify/SKILL.md      (was .claude/commands/pl-verify.md)
                                        ├── ... (34 more)
                                        ├── start/SKILL.md       ← NEW
                                        ├── init/SKILL.md        ← NEW
                                        └── upgrade/SKILL.md     ← NEW

                                        agents/                  ← MOVED
                                        ├── purlin.md            ← NEW (main agent, PURLIN_BASE.md content)
                                        ├── engineer-worker.md   (was .claude/agents/)
                                        └── verification-runner.md

tools/                                  scripts/                 ← RENAMED from tools/
├── cdd/scan.py                         ├── mcp/purlin_server.py ← NEW (MCP server wrapping scan engine)
├── cdd/graph.py                        ├── mcp/scan_engine.py   (refactored from tools/cdd/scan.py)
├── cdd/invariant.py                    ├── mcp/graph_engine.py  (refactored from tools/cdd/graph.py)
├── cdd/scan.sh                         ├── mcp/invariant_engine.py
├── config/resolve_config.py            ├── mcp/config_engine.py (refactored from tools/config/)
├── terminal/identity.sh                ├── mcp/bootstrap.py     (simplified from tools/bootstrap.py)
├── hooks/merge-worktrees.sh            ├── terminal/identity.sh (moved as-is)
├── toolbox/*.py                        ├── toolbox/*.py         (moved, simplified paths)
├── worktree/manage.sh                  ├── worktree/manage.sh   (moved as-is)
├── test_support/                       ├── test_support/        (moved as-is)
├── bootstrap.py                        └── ... (other supporting scripts)
├── resolve_python.sh                   ← DELETED (not needed, MCP server runs persistently)
├── init.sh                             ← DELETED (replaced by purlin:init skill)

                                        hooks/                   ← NEW
                                        ├── hooks.json
                                        └── scripts/
                                            ├── session-start.sh
                                            ├── session-end-merge.sh (was tools/hooks/merge-worktrees.sh)
                                            ├── mode-guard.sh
                                            ├── permission-manager.sh
                                            ├── pre-compact-checkpoint.sh
                                            └── companion-debt-tracker.sh

instructions/                           references/              ← RENAMED from instructions/references/
├── PURLIN_BASE.md                      ├── file_classification.md (moved from instructions/references/)
├── references/*.md                     ├── file_classification.json ← NEW (machine-readable)
                                        ├── active_deviations.md
                                        ├── ... (13 more)

                                        templates/               ← RENAMED from purlin-config-sample/
purlin-config-sample/                   ├── config.json
├── config.json                         ├── PURLIN_OVERRIDES.md
├── PURLIN_OVERRIDES.md                 └── CLAUDE.md
├── CLAUDE.md.purlin
├── gitignore.purlin

.mcp.json                              .mcp.json                ← UPDATED (add purlin MCP server)
                                        settings.json            ← NEW ({ "agent": "purlin" })
                                        output-styles/           ← NEW
                                        └── purlin-status.md

pl-run.sh                              ← DELETED
CLAUDE.md                              CLAUDE.md                (updated for plugin context)
README.md                              README.md                (updated)
CHANGELOG.md                           CHANGELOG.md             (updated)

── FILES THAT STAY UNCHANGED (dev/framework artifacts, invisible to plugin) ──
features/                               features/                (Purlin's own feature specs)
tests/                                  tests/                   (Purlin's own tests)
dev/                                    dev/                     (Purlin dev-only scripts)
.purlin/                                .purlin/                 (Purlin's own project config)
.gitignore                              .gitignore               (updated)
LICENSE                                 LICENSE
```

### Summary of Changes

| Action | Count | Details |
|---|---|---|
| NEW files/dirs | ~12 | `.claude-plugin/`, `skills/resume/`, `skills/init/`, `skills/upgrade/`, `agents/purlin.md`, `hooks/`, `scripts/mcp/`, `references/file_classification.json`, `settings.json`, `output-styles/` |
| MOVED + RENAMED | ~55 | 36 skill files, 2 agent files, ~15 reference docs, `purlin-config-sample/` → `templates/` |
| REFACTORED | ~6 | scan.py → scan_engine.py (importable module), graph.py, invariant.py, config, bootstrap (simplified paths) |
| DELETED | ~8 | `pl-run.sh`, `tools/init.sh`, `tools/resolve_python.sh`, `tools/cdd/scan.sh`, `.claude/commands/` (empty after move), `.claude/agents/` (empty after move) |
| UNCHANGED | ~100+ | `features/`, `tests/`, `dev/`, `.purlin/`, `docs/`, `assets/`, `LICENSE`, `.gitignore` |

### Distribution: The Repo IS the Plugin

Consumer projects point directly at this repo. No separate marketplace repo needed:

```json
// In consumer project's .claude/settings.json
{
  "extraKnownMarketplaces": {
    "purlin": {
      "source": "settings",
      "plugins": [{
        "name": "purlin",
        "source": { "source": "github", "repo": "rlabarca/purlin" }
      }]
    }
  },
  "enabledPlugins": { "purlin@purlin": true }
}
```

Version tags on the repo control plugin versions. `v1.0.0` tag = plugin version 1.0.0. The plugin system caches the install, so extra files (features/, tests/, dev/) are copied to cache but completely ignored.

For the public marketplace (later): submit at https://claude.ai/settings/plugins/submit. For enterprise: force-enable via managed settings.

---

## 8. Script Execution: The MCP Server Approach

### The Problem
The CDD scan engine (`scan.py`, 1100+ lines) is called 10-20 times per session. Today it runs via: skill → `scan.sh` → `resolve_python.sh` → `python3 scan.py` (~100-150ms startup per invocation). The mode guard hook also needs file classification on every write.

### Key Finding: Zero External Dependencies
All Purlin Python tools use **only Python stdlib** (json, os, re, subprocess, sys, etc.). No venv, no pip install, no dependency management needed. The optional `anthropic` package is only for LLM-based design features.

### Solution: Purlin MCP Server
Bundle a lightweight MCP server that wraps the scan engine as a persistent process. The server starts automatically when the plugin is enabled and exposes tools that Claude calls directly:

| MCP Tool | Purpose |
|---|---|
| `purlin_scan` | Full project scan → structured JSON |
| `purlin_status` | Interpreted work items by mode |
| `purlin_graph` | Dependency graph with cycle detection |
| `purlin_classify` | File path → CODE/SPEC/QA/INVARIANT (for mode guard hook) |
| `purlin_mode` | Get/set current mode state |
| `purlin_config` | Read/write .purlin/config.json |

**Benefits:** Zero startup overhead per call (Python already running), in-memory caching, first-class tool integration (no Bash intermediary), mode guard hook queries the server instead of spawning Python per write.

**Low-frequency operations stay as direct scripts:** toolbox management, terminal identity, merge-worktrees, worktree management.

---

## 9. User Experience Comparison

### Starting a Session

**Today (submodule):**
```bash
./pl-run.sh                           # Interactive
./pl-run.sh --auto-build              # Engineer, auto-start
./pl-run.sh --model opus --yolo       # Opus + YOLO
./pl-run.sh --verify my_feature       # QA verify specific feature
./pl-run.sh --worktree --auto-build   # Isolated worktree + auto-build
```

**Plugin:**
```bash
claude                                 # Plugin auto-activates, runs purlin:resume via SessionStart
purlin:resume --build                   # Engineer, auto-start
purlin:resume --yolo                    # Enable YOLO (persists)
purlin:resume --verify my_feature       # QA verify specific feature
purlin:resume --worktree --build        # Worktree + auto-build
```

### Daily Workflow

**Today:** User must remember to use `./pl-run.sh` (not bare `claude`). If they use bare `claude`, CLAUDE.md triggers `/pl-resume` but model/effort/YOLO are not set.

**Plugin:** User just runs `claude`. The plugin's `settings.json` activates the Purlin agent. The `SessionStart` hook runs the resume protocol. The `PermissionRequest` hook handles YOLO. Everything works regardless of how Claude Code is invoked.

---

## 10. Project Segmentation

### How Purlin stays isolated to projects that use it

The plugin system has four installation scopes. Purlin uses two of them to maintain clean segmentation:

| Scope | What goes here | Affects |
|---|---|---|
| **User** (`~/.claude/settings.json`) | Marketplace registration only | All projects can SEE the plugin, but it's not enabled |
| **Project** (`.claude/settings.json`, committed) | `enabledPlugins: { "purlin@purlin": true }` | Only THIS project activates Purlin |

**One-time user setup:** Register the marketplace so Claude Code knows where to find Purlin:
```json
// ~/.claude/settings.json (user scope, once)
{
  "extraKnownMarketplaces": {
    "purlin": {
      "source": "settings",
      "plugins": [{ "name": "purlin", "source": { "source": "github", "repo": "rlabarca/purlin" } }]
    }
  }
}
```

**Per-project opt-in:** Each project that uses Purlin adds enablement to its committed settings:
```json
// .claude/settings.json (project scope, committed to git)
{
  "enabledPlugins": { "purlin@purlin": true }
}
```

**What happens in each context:**

| Context | Plugin loaded? | Agent replaced? | Hooks active? | MCP server running? |
|---|---|---|---|---|
| Project WITH `enabledPlugins` | Yes | Yes (purlin agent) | Yes (mode guard, etc.) | Yes |
| Project WITHOUT `enabledPlugins` | No | No (standard Claude) | No | No |
| Bare `claude` outside any project | No | No | No | No |

The plugin's `settings.json` (`{ "agent": "purlin" }`) only takes effect when the plugin is loaded. Projects without Purlin enabled see standard Claude Code with zero interference -- no hooks, no MCP server, no agent replacement, no skill namespace pollution.

---

## 10b. Future: Dashboard Capability

The plugin architecture naturally supports a local web dashboard that a skill could launch:

**How it works:**
1. The Purlin MCP server (already running as a persistent Python process) spawns a lightweight HTTP thread on an auto-discovered port (bind to port 0, let the OS assign)
2. The port is written to `.purlin/runtime/dashboard.port` for other tools to discover
3. A `purlin:dashboard` skill tells the agent to start the dashboard and opens it in the browser
4. The dashboard reads from the same in-memory scan data the MCP server already maintains -- zero additional overhead
5. The Playwright MCP can navigate to `localhost:<port>` for automated visual verification of dashboard components

**Why this is clean in the plugin model:**
- The MCP server is already a persistent Python process with scan data in memory
- Adding an HTTP endpoint is ~20 lines of `http.server` (stdlib)
- The port is ephemeral and project-scoped (written to `.purlin/runtime/`)
- Multiple projects can each have their own dashboard on different ports
- The dashboard dies when the MCP server dies (session end = cleanup)

**Alternative approach:** The dashboard could be a completely separate MCP server declared in `.mcp.json`, with its own process. This is cleaner for separation of concerns but adds another persistent process.

Either approach is fully supported by the plugin architecture. No changes needed to the migration plan -- this is additive.

---

## 11. Summary Assessment

| Category | Count | Notes |
|----------|-------|-------|
| User stories fully preserved | 10 of 13 | Stories 1, 3, 4, 6, 8, 9, 10, 13 translate 1:1 |
| User stories improved | 3 of 13 | Story 2 (mechanical mode guard), Story 7 (auto-recovery), Story 5 (PermissionRequest solves parallel builds) |
| User stories with minor degradation | 1 of 13 | Story 11 (terminal identity: brief gap before SessionStart hook fires) |
| Hard blockers | 0 | PermissionRequest hook solves the permission bypass gap |
| Minor gaps | 2 | Pre-session model selection (10-line launcher or aliases), managed deny rule override (enterprise edge case) |
| New capabilities | 6+ | Mechanical mode guard, auto-checkpoint, companion debt tracking, channels, LSP, output styles |
| Eliminated complexity | 7 items | Launcher, init script, submodule management, symlinks, path climbing, submodule safety mandate, tools_root resolution |

**Bottom line:** The migration is not only viable -- it's a clear improvement. The `PermissionRequest` hook eliminates the last hard blocker. The `purlin:resume` skill replaces the 504-line launcher. The `settings.json` agent key handles prompt assembly. `EnterWorktree` handles worktree creation. `/rename` handles session naming. Model selection is deprecated as a Purlin feature (users use `claude --model` directly).

---

## 12. `purlin:resume` Specification

### Purpose
Replaces `pl-run.sh` (504 lines) as the session entry point. Handles everything the launcher did, from within the running session.

### Usage
```
purlin:resume [OPTIONS]

Session setup:
  --mode <pm|engineer|qa>    Activate a mode
  --build                    Shortcut: --mode engineer + auto-start
  --verify [feature]         Shortcut: --mode qa + auto-start [+ feature]
  --pm                       Shortcut: --mode pm
  --worktree                 Enter an isolated git worktree
  --yolo                     Enable auto-approve for all permission prompts (persists)
  --no-yolo                  Disable auto-approve (persists)
  --effort <high|medium>     Set effort level for this session
  --find-work <true|false>   Enable/disable work discovery (persists)

  No options: run checkpoint recovery + scan + suggest mode
```

### Execution Flow

**Step 0 -- Environment Detection**
1. Check for `.purlin/` directory. If missing: "Run `purlin:init` first." Stop.
2. Read `.purlin/config.json` for project settings.
3. Check `${CLAUDE_PLUGIN_DATA}/session_state.json` for persisted session flags.

**Step 1 -- Flag Processing**
- `--yolo`: Write `bypass_permissions: true` to `.purlin/config.json`. The PermissionRequest hook reads this and auto-approves all permission dialogs.
- `--no-yolo`: Write `bypass_permissions: false`.
- `--effort`: Execute `/effort <level>` (Claude Code built-in).
- `--find-work`: Write `find_work` to config.

**Step 2 -- Worktree Entry** (only if `--worktree`)
1. Call `EnterWorktree` tool (Claude Code built-in).
2. Write `.purlin_worktree_label` (W1, W2, ...) and `.purlin_session.lock`.

**Step 3 -- Session Identity**
1. Set terminal identity: iTerm badge + Warp tab + terminal title.
2. Rename session: `"<project> | <badge>"`

**Step 4 -- Checkpoint Recovery**
Same as current `/pl-resume` Steps 0-1. Merge breadcrumb check, stale reaping, checkpoint detection.

**Step 5 -- Work Discovery** (if no checkpoint and find_work != false)
1. Run scan. Run `purlin:status`. Suggest mode.

**Step 6 -- Mode Activation**
Priority: CLI flag > checkpoint mode > config default_mode > user input.
If `--build`: activate Engineer + invoke `purlin:build`.
If `--verify`: activate QA + invoke `purlin:verify`.

### Hook Integration
| Hook Event | Script | Purpose |
|---|---|---|
| SessionStart | session-start.sh | Context reminder: "Purlin active, run purlin:resume" |
| SessionEnd | session-end-merge.sh | Merge worktrees, cleanup |
| PreToolUse (Write/Edit) | mode-guard.sh | Mechanical mode guard |
| PermissionRequest | permission-manager.sh | YOLO auto-approve |
| PreCompact | pre-compact-checkpoint.sh | Auto-save checkpoint |
| FileChanged | companion-debt-tracker.sh | Real-time companion debt |

**Design decision:** SessionStart hook does NOT auto-run the full startup. It only injects a brief reminder. Full protocol runs via `purlin:resume`. This avoids heavy scan+status on every `/clear`.

---

## 13. Phased Conversion Plan (Detailed File Changes)

Each phase lists exactly what files and directories are created, moved, renamed, modified, or deleted. Phases are sequential. Each ends with a commit and checkpoint.

---

### Phase 0: Plugin Scaffold (1 session)

**Creates:**
| File/Dir | Purpose |
|---|---|
| `.claude-plugin/plugin.json` | Plugin manifest with metadata, userConfig |
| `settings.json` | `{ "agent": "purlin" }` -- activates main agent |
| `agents/purlin.md` | Main agent definition (PURLIN_BASE.md content as system prompt) |

**No moves, no deletes.** Existing repo structure unchanged. Plugin not yet functional (no skills loaded).

**Commit:** `engineer(plugin): scaffold plugin manifest and main agent definition`

---

### Phase 1: Skill Migration (2-3 sessions)

**Creates:**
| File/Dir | Source | Notes |
|---|---|---|
| `skills/build/SKILL.md` | `.claude/commands/pl-build.md` | Add frontmatter, update cross-refs to `purlin:*` |
| `skills/verify/SKILL.md` | `.claude/commands/pl-verify.md` | " |
| `skills/spec/SKILL.md` | `.claude/commands/pl-spec.md` | " |
| `skills/mode/SKILL.md` | `.claude/commands/pl-mode.md` | " |
| `skills/resume/SKILL.md` | `.claude/commands/pl-resume.md` | " |
| `skills/status/SKILL.md` | `.claude/commands/pl-status.md` | " |
| `skills/delivery-plan/SKILL.md` | `.claude/commands/pl-delivery-plan.md` | " |
| `skills/unit-test/SKILL.md` | `.claude/commands/pl-unit-test.md` | " |
| `skills/web-test/SKILL.md` | `.claude/commands/pl-web-test.md` | " |
| `skills/complete/SKILL.md` | `.claude/commands/pl-complete.md` | " |
| `skills/discovery/SKILL.md` | `.claude/commands/pl-discovery.md` | " |
| `skills/anchor/SKILL.md` | `.claude/commands/pl-anchor.md` | " |
| `skills/regression/SKILL.md` | `.claude/commands/pl-regression.md` | " |
| `skills/smoke/SKILL.md` | `.claude/commands/pl-smoke.md` | " |
| `skills/qa-report/SKILL.md` | `.claude/commands/pl-qa-report.md` | " |
| `skills/fixture/SKILL.md` | `.claude/commands/pl-fixture.md` | " |
| `skills/propose/SKILL.md` | `.claude/commands/pl-propose.md` | " |
| `skills/infeasible/SKILL.md` | `.claude/commands/pl-infeasible.md` | " |
| `skills/spec-code-audit/SKILL.md` | `.claude/commands/pl-spec-code-audit.md` | " |
| `skills/spec-from-code/SKILL.md` | `.claude/commands/pl-spec-from-code.md` | " |
| `skills/server/SKILL.md` | `.claude/commands/pl-server.md` | " |
| `skills/tombstone/SKILL.md` | `.claude/commands/pl-tombstone.md` | " |
| `skills/find/SKILL.md` | `.claude/commands/pl-find.md` | " |
| `skills/help/SKILL.md` | `.claude/commands/pl-help.md` | " |
| `skills/merge/SKILL.md` | `.claude/commands/pl-merge.md` | " |
| `skills/worktree/SKILL.md` | `.claude/commands/pl-worktree.md` | " |
| `skills/remote/SKILL.md` | `.claude/commands/pl-remote.md` | " |
| `skills/toolbox/SKILL.md` | `.claude/commands/pl-toolbox.md` | " |
| `skills/session-name/SKILL.md` | `.claude/commands/pl-session-name.md` | " |
| `skills/override-edit/SKILL.md` | `.claude/commands/pl-override-edit.md` | " |
| `skills/purlin-issue/SKILL.md` | `.claude/commands/pl-purlin-issue.md` | " |
| `skills/design-audit/SKILL.md` | `.claude/commands/pl-design-audit.md` | " |
| `skills/design-ingest/SKILL.md` | `.claude/commands/pl-design-ingest.md` | " |
| `skills/invariant/SKILL.md` | `.claude/commands/pl-invariant.md` | " |
| `skills/whats-different/SKILL.md` | `.claude/commands/pl-whats-different.md` | " |
| `skills/update/SKILL.md` | `.claude/commands/pl-update-purlin.md` | Simplified to `claude plugin update purlin` |
| `skills/resume/SKILL.md` | NEW | Full `purlin:resume` spec (replaces pl-run.sh) |
| `skills/init/SKILL.md` | NEW | Project initialization (replaces init.sh) |
| `skills/upgrade/SKILL.md` | NEW | Submodule-to-plugin migration |

**Deletes:**
| File/Dir | Reason |
|---|---|
| `.claude/commands/pl-*.md` (36 files) | Moved to `skills/` |

**Transforms applied to each skill:**
- Add SKILL.md YAML frontmatter (`name`, `description`)
- Replace `/pl-<name>` → `purlin:<name>` in all cross-references
- Replace `${TOOLS_ROOT}/` → `${CLAUDE_PLUGIN_ROOT}/scripts/` in script paths
- Replace `instructions/references/` → `${CLAUDE_PLUGIN_ROOT}/references/`

**Commit:** `engineer(plugin): migrate 36 skills + write start/init/upgrade`

---

### Phase 2: MCP Server + Script Migration (2-3 sessions)

**Creates:**
| File/Dir | Source | Notes |
|---|---|---|
| `scripts/mcp/purlin_server.py` | NEW | MCP stdio server (JSON-RPC) |
| `scripts/mcp/scan_engine.py` | `tools/cdd/scan.py` | Refactored as importable module |
| `scripts/mcp/graph_engine.py` | `tools/cdd/graph.py` | " |
| `scripts/mcp/invariant_engine.py` | `tools/cdd/invariant.py` | " |
| `scripts/mcp/config_engine.py` | `tools/config/resolve_config.py` | Simplified path resolution |
| `scripts/mcp/bootstrap.py` | `tools/bootstrap.py` | Remove submodule detection |
| `scripts/terminal/identity.sh` | `tools/terminal/identity.sh` | Moved as-is |
| `scripts/toolbox/resolve.py` | `tools/toolbox/resolve.py` | Simplified paths |
| `scripts/toolbox/manage.py` | `tools/toolbox/manage.py` | " |
| `scripts/toolbox/community.py` | `tools/toolbox/community.py` | " |
| `scripts/toolbox/purlin_tools.json` | `tools/toolbox/purlin_tools.json` | Moved as-is |
| `scripts/worktree/manage.sh` | `tools/worktree/manage.sh` | Moved as-is |
| `scripts/test_support/*` | `tools/test_support/*` | Moved as-is |
| `scripts/smoke/smoke.py` | `tools/smoke/smoke.py` | Moved as-is |

**Modifies:**
| File | Change |
|---|---|
| `.mcp.json` | Add `purlin` MCP server entry (python3 + purlin_server.py). Keep Playwright + Figma. |

**Deletes:**
| File/Dir | Reason |
|---|---|
| `tools/cdd/scan.py` | Refactored into `scripts/mcp/scan_engine.py` |
| `tools/cdd/graph.py` | Refactored into `scripts/mcp/graph_engine.py` |
| `tools/cdd/invariant.py` | Refactored into `scripts/mcp/invariant_engine.py` |
| `tools/cdd/scan.sh` | Replaced by MCP server |
| `tools/config/resolve_config.py` | Refactored into `scripts/mcp/config_engine.py` |
| `tools/bootstrap.py` | Refactored into `scripts/mcp/bootstrap.py` |
| `tools/resolve_python.sh` | Not needed (MCP server runs persistently) |
| `tools/init.sh` | Replaced by `purlin:init` skill |
| `tools/terminal/identity.sh` | Moved to `scripts/terminal/` |
| `tools/toolbox/*.py` | Moved to `scripts/toolbox/` |
| `tools/worktree/manage.sh` | Moved to `scripts/worktree/` |
| `tools/hooks/merge-worktrees.sh` | Moved to `hooks/scripts/` in Phase 3 |
| `tools/test_support/*` | Moved to `scripts/test_support/` |

After this phase, `tools/` is nearly empty (only `tools/mcp/manifest.json`, `tools/feature_templates/`, and any remaining dev-only test files). These remnants are cleaned up or moved in Phase 4.

**Commit:** `engineer(plugin): build MCP server + migrate scripts`

---

### Phase 3: Hook Implementation (1 session)

**Creates:**
| File/Dir | Source | Notes |
|---|---|---|
| `hooks/hooks.json` | NEW | Declares all 7 hook handlers |
| `hooks/scripts/session-start.sh` | NEW | Context injection on start/clear/compact |
| `hooks/scripts/session-end-merge.sh` | `tools/hooks/merge-worktrees.sh` | Adapted for plugin paths |
| `hooks/scripts/mode-guard.sh` | NEW | PreToolUse: queries MCP `purlin_classify` |
| `hooks/scripts/permission-manager.sh` | NEW | PermissionRequest: YOLO auto-approve |
| `hooks/scripts/pre-compact-checkpoint.sh` | NEW | Auto-save checkpoint before compaction |
| `hooks/scripts/companion-debt-tracker.sh` | NEW | FileChanged: real-time companion debt |
| `references/file_classification.json` | NEW | Machine-readable classification (hook fallback) |

**Deletes:**
| File/Dir | Reason |
|---|---|
| `tools/hooks/merge-worktrees.sh` | Moved to `hooks/scripts/session-end-merge.sh` |

**Modifies:**
| File | Change |
|---|---|
| `.claude/settings.json` | Remove old SessionStart/SessionEnd hooks (plugin hooks replace them) |

**Commit:** `engineer(plugin): implement hook handlers (mode guard, YOLO, lifecycle)`

---

### Phase 4: References, Templates, Agent Defs, Cleanup (1 session)

**Creates/Moves:**
| File/Dir | Source | Notes |
|---|---|---|
| `references/file_classification.md` | `instructions/references/file_classification.md` | Moved |
| `references/active_deviations.md` | `instructions/references/active_deviations.md` | " |
| `references/commit_conventions.md` | `instructions/references/commit_conventions.md` | " |
| `references/knowledge_colocation.md` | `instructions/references/knowledge_colocation.md` | " |
| `references/testing_lifecycle.md` | `instructions/references/testing_lifecycle.md` | " |
| `references/phased_delivery.md` | `instructions/references/phased_delivery.md` | " |
| `references/visual_spec_convention.md` | `instructions/references/visual_spec_convention.md` | " |
| `references/feature_format.md` | `instructions/references/feature_format.md` | " |
| `references/spec_authoring_guide.md` | `instructions/references/spec_authoring_guide.md` | " |
| `references/path_resolution.md` | `instructions/references/path_resolution.md` | " |
| `references/invariant_format.md` | `instructions/references/invariant_format.md` | " |
| `references/invariant_model.md` | `instructions/references/invariant_model.md` | " |
| `references/test_infrastructure.md` | `instructions/references/test_infrastructure.md` | " |
| `references/visual_verification_protocol.md` | `instructions/references/visual_verification_protocol.md` | " |
| `references/purlin_commands.md` | `instructions/references/purlin_commands.md` | " |
| `templates/config.json` | `purlin-config-sample/config.json` | Moved |
| `templates/PURLIN_OVERRIDES.md` | `purlin-config-sample/PURLIN_OVERRIDES.md` | " |
| `templates/CLAUDE.md` | `purlin-config-sample/CLAUDE.md.purlin` | Renamed |
| `templates/gitignore.purlin` | `purlin-config-sample/gitignore.purlin` | Moved |
| `output-styles/purlin-status.md` | NEW | Formatted status output |
| `agents/engineer-worker.md` | `.claude/agents/engineer-worker.md` | Update for plugin context |
| `agents/verification-runner.md` | `.claude/agents/verification-runner.md` | " |

**Deletes:**
| File/Dir | Reason |
|---|---|
| `instructions/references/*.md` (15 files) | Moved to `references/` |
| `instructions/PURLIN_BASE.md` | Content now in `agents/purlin.md` |
| `instructions/` (empty dir) | All contents moved |
| `purlin-config-sample/` (entire dir) | Moved to `templates/` |
| `.claude/agents/*.md` | Moved to `agents/` |
| `.claude/commands/` (empty after Phase 1) | Cleaned up |
| `pl-run.sh` | Replaced by `purlin:resume` skill |
| `tools/` (remaining contents) | All moved to `scripts/` or deleted |
| Remaining `tools/` dir | Empty after cleanup |

**Modifies:**
| File | Change |
|---|---|
| `agents/purlin.md` | Finalize system prompt: replace submodule references, update path conventions |
| `CLAUDE.md` | Update for plugin context (remove submodule/launcher references) |
| `README.md` | Update installation instructions, remove submodule setup |
| `.gitignore` | Remove submodule entries, add plugin cache patterns |
| `.mcp.json` | Finalize: purlin MCP server + Playwright + Figma |

**Commit:** `engineer(plugin): migrate references, templates, agent defs; clean up old structure`

---

### Phase 5: Integration Testing (1-2 sessions)

**No file changes to the repo.** This phase tests the plugin using `claude --plugin-dir .`:

- Validate plugin: `claude plugin validate .`
- Verify MCP server starts and all tools appear
- Test `purlin:resume` (all flags)
- Test mode guard hook (wrong-mode write → blocked)
- Test YOLO via PermissionRequest hook
- **Test PermissionRequest fires for subagent dialogs** (critical)
- Test worktree lifecycle (enter, work, merge-back on exit)
- Test full build cycle: `purlin:spec` → `purlin:build` → `purlin:verify` → `purlin:complete`
- Test `purlin:init` on a fresh test project
- Test MCP server crash + auto-restart

**Commit:** Only test fixture updates if any: `test(plugin): add integration test fixtures`

---

### Phase 6: Upgrade Skill + Consumer Testing (1 session)

**No changes to the Purlin repo.** Test on a consumer project:

- Start with a submodule-based consumer project
- Run `purlin:upgrade` (the skill written in Phase 1)
- Verify: submodule removed, stale artifacts cleaned, plugin declared, features preserved
- Run `purlin:resume` in the upgraded project
- Run a full build cycle to verify everything works

**Commit:** Bug fixes only if needed: `fix(plugin): <issue found during consumer testing>`

---

### Phase 7: Distribution + Release (1 session)

**Modifies:**
| File | Change |
|---|---|
| `.claude-plugin/plugin.json` | Set version to `1.0.0` |
| `CHANGELOG.md` | Write v1.0.0 release notes |
| `README.md` | Final installation instructions |

**Actions:**
- Tag `v1.0.0`
- Push to GitHub
- Test consumer install: `claude plugin install purlin` via inline marketplace in settings.json
- Verify version pinning and update flow

**Commit:** `chore(plugin): release v1.0.0`

---

### Phase Summary

| Phase | Sessions | Creates | Moves | Deletes | Key Outcome |
|---|---|---|---|---|---|
| 0 | 1 | 3 files | 0 | 0 | Plugin skeleton exists |
| 1 | 2-3 | 39 skill dirs | 0 | 36 command files | All skills in plugin format |
| 2 | 2-3 | ~15 script files + MCP server | ~12 tool files | ~15 old tool files | MCP server + scripts migrated |
| 3 | 1 | 8 hook files | 1 hook script | 1 old hook | Mechanical enforcement active |
| 4 | 1 | 1 output style | ~20 refs+templates | ~25 old locations | Old structure fully cleaned |
| 5 | 1-2 | 0 | 0 | 0 | Plugin validated end-to-end |
| 6 | 1 | 0 | 0 | 0 | Consumer upgrade tested |
| 7 | 1 | 0 | 0 | 0 | v1.0.0 released |
| **Total** | **~9-13** | **~65** | **~33** | **~77** | |

---

## 14. Consumer Project Upgrade Path (`purlin:upgrade`)

Migrates submodule-based projects to the plugin model in one command.

### Flow
1. **Pre-flight:** Verify submodule exists, no uncommitted changes, record current version.
2. **Preserve:** Verify features/, .purlin/PURLIN_OVERRIDES.md, config, tests all intact (NOT touched).
3. **Remove submodule:** `git submodule deinit -f`, `git rm -f`, clean `.git/modules/`.
4. **Clean stale artifacts:** Delete pl-run.sh, pl-init.sh, .claude/commands/pl-*.md, .claude/agents/*.md, hooks from settings.json, .purlin/.upstream_sha, init-installed MCP servers.
5. **Declare plugin:** Add inline marketplace + enabledPlugins to .claude/settings.json.
6. **Migrate config:** Remove tools_root, models array, deprecated agent entries from .purlin/config.json.
7. **Update CLAUDE.md:** Replace purlin:resume/end block with plugin instructions.
8. **Update .gitignore:** Remove submodule-specific entries.
9. **Verify:** Validate JSON files, check features/ intact, test MCP server tools.
10. **Commit:** `chore(purlin): migrate from submodule to plugin distribution`

Supports `--dry-run` to preview without changes. Pre-upgrade git commit provides rollback.

---

## 15. Risk Assessment

| Rank | Risk | Severity | Mitigation |
|---|---|---|---|
| 1 | **Plugin system instability** -- APIs/hooks could change, breaking all users simultaneously | CRITICAL | Pin versions, maintain submodule as fallback for 2-3 months, test against Claude Code betas |
| 2 | **PermissionRequest hook may not fire for subagent dialogs** -- breaks parallel builds | CRITICAL | Test FIRST in Phase 5; users start with --dangerously-skip-permissions for parallel build sessions |
| 3 | **MCP server reliability** -- scan, classify, mode state all route through it; crash = degraded | HIGH | Auto-restart on crash, JSON file fallback for mode guard, stdlib-only to minimize crash surface |
| 4 | **Prompt assembly coherence** -- agent def + CLAUDE.md = two injection points that may conflict | HIGH | Base rules in agent def (highest authority), overrides only in CLAUDE.md, test priority in Phase 5 |
| 5 | **Consumer upgrade failures** -- multi-step migration leaves project inconsistent if interrupted | HIGH | Pre-upgrade git commit as snapshot, --dry-run preview, step-by-step logging, git checkout . rollback |
