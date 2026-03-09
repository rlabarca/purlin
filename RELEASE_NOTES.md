# Release Notes

### v0.7.5 — 2026-02-26

**Runtime Port Override**
- `-p <port>` CLI flag for `start.sh` to override CDD Dashboard port at runtime
- `CDD_PORT` env var support in `serve.py` for multi-project and collaboration scenarios

**Upstream Sync Modernization**
- `/pl-update-purlin` agent skill replaces the old `sync_upstream.sh` script
- Intelligent submodule update with semantic analysis and conflict resolution
- Removed deprecated `sync_upstream.sh`

### v0.7.0 — 2026-02-26

**Remote Collaboration**
- Remote multi-machine collaboration via collab sessions (`collab/<name>` branches)
- Dashboard section with session management, sync badges (AHEAD/BEHIND/SAME/DIVERGED), and per-session controls
- `/pl-remote-push` and `/pl-remote-pull` commands for collab branch sync with remote
- Session delete with confirmation modal

**Spec Map Enhancements**
- Inter-category topological layer ordering with edge arrows
- Dynamic label sizing and two-level category packing layout

**Critic Enhancements**
- Targeted scope completeness audit
- Delivery plan scope reset on plan completion

**Upstream Sync**
- Auto-fetch and update prompt — script now fetches from remote and prompts before updating, eliminating the manual `git pull` prerequisite (script subsequently replaced by `/pl-update-purlin` agent skill)

**Instruction Fixes**
- Corrected stale launcher script names in HOW_WE_WORK_BASE
- Fixed contradictory companion file wording in BUILDER_BASE

**Process**
- `/pl-spec-from-code` command for reverse-engineering feature specs from existing codebases (experimental)
- Renamed collaboration commands to `/pl-remote-push`/`pull`
- Normalized label naming across CDD Dashboard and Agent Skills categories

### v0.6.0 — 2026-02-24

**Isolated Teams**
- Named git worktrees for concurrent agent sessions (`tools/collab/create_isolation.sh`, `tools/collab/kill_isolation.sh`)
- Dashboard section with per-isolation state tracking (AHEAD/BEHIND/SAME/DIVERGED), file change summary, and create/kill controls
- `/pl-isolated-push` and `/pl-isolated-pull` commands for merge-before-proceed workflow
- Agent config propagation to active worktrees

**Agent Configuration**
- Dashboard panel for per-agent model, effort, permissions, and startup behavior settings
- `/pl-agent-config` skill for worktree-safe config modification from agent sessions
- Per-agent `startup_sequence` and `recommend_next_actions` startup control flags (expert mode: both false)

**Spec Map (renamed from Software Map)**
- Interactive dependency graph with node position persistence and conditional zoom/pan preservation
- Recenter Graph button and inactivity timeout for auto-redraw

**Critic Enhancements**
- Language-agnostic test file discovery with tiered extraction (Python, JS/TS, shell, generic fallback)
- Companion `.impl.md` file detection in section completeness checks
- Builder Decision Audit extended to scan anchor node companion files
- Visual specification detection supports numbered section headers
- Targeted scope filters QA action items to manual scenarios only
- Structured status detection and RESOLVED discovery pruning signal

**Companion File Convention**
- All implementation notes migrated from inline `## Implementation Notes` to standalone `*.impl.md` companion files
- Feature files no longer contain implementation notes; companion files are standalone (no cross-links)
- Companion file edits exempt from lifecycle status resets

**Process & Documentation**
- File access permissions formalized across all roles (README permissions table)
- Bidirectional spec-code audit (`/pl-spec-code-audit`) shared between Architect and Builder
- `/pl-status` uncommitted changes check added to Architect protocol
- Complete QA verification pass across all 31 features

**Getting started:**

This is tested to be started with a new project right now. You can ask the architect to scan your code and build an initial feature map but the behavior will be undefined. It would be an interesting experiment though!

**Known limitations:**

- Built exclusively for Claude Code. Supporting additional models is a goal but model feature disparity makes that non-trivial.
- The release checklist is long enough to stress context windows. For now, the checklist can be interrupted and resumed with: `/pl-release-run start with step X, steps 1 through X-1 have passed`. Modularizing the checklist to reduce token cost is a planned improvement.

### v0.5.0 — 2026-02-22

- Initial release of Purlin: Collaborative Design-Driven Agentic Development Framework
- CDD Dashboard with role-based status columns, release checklist UI, and software map
- Critic coordination engine with dual-gate validation, regression scoping, and role-specific action items
- Release checklist system with global and local steps, config-driven ordering
- Phased delivery protocol for multi-session builder workflows
- Submodule bootstrap and upstream sync tooling
- Visual specification convention for UI features
- Layered instruction architecture (base + project override layers)
- Tombstone protocol for structured feature retirement

**Known limitations:**

- Built exclusively for Claude Code. Supporting additional models is a goal but model feature disparity makes that non-trivial.
- Local concurrent collaboration is supported via Isolated Teams (named worktrees). Cross-machine and remote worker support is a planned future direction.
- The release checklist is long enough to stress context windows. For now, the checklist can be interrupted and resumed with: `/pl-release-run start with step X, steps 1 through X-1 have passed`. Modularizing the checklist to reduce token cost is a planned improvement.
