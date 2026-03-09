# Release Notes

### v0.8.0 — 2026-03-08

**Documentation Overhaul**
- README rewritten for clarity (430 lines trimmed to ~300)
- Upgrade instructions for both legacy and current users
- NotebookLM knowledge base and audio overview linked for self-service Q&A
- CDD Dashboard screenshots updated to v0.8.0
- Stale command names and path references fixed across all docs

### v0.7.5 — 2026-02-26

**Runtime Port Override**
- `-p <port>` flag lets you override the CDD Dashboard port at runtime -- useful for running multiple projects on the same machine

**Upstream Sync Modernization**
- `/pl-update-purlin` replaces the old `sync_upstream.sh` script with semantic analysis and conflict resolution

### v0.7.0 — 2026-02-26

**Remote Collaboration**
- Multi-machine collaboration via collab sessions (`collab/<name>` branches on a hosted remote)
- Dashboard section with session management and sync badges
- `/pl-remote-push` and `/pl-remote-pull` for collab branch sync

**Other Highlights**
- Spec Map: inter-category topological ordering with edge arrows and dynamic label sizing
- Critic: targeted scope completeness audit and delivery plan scope reset
- `/pl-spec-from-code` for reverse-engineering specs from existing codebases (experimental)

### v0.6.0 — 2026-02-24

**Isolated Teams**
- Named git worktrees for concurrent agent sessions with dashboard state tracking
- `/pl-isolated-push` and `/pl-isolated-pull` for merge-before-proceed workflow

**Agent Configuration**
- Dashboard panel and `/pl-agent-config` for per-agent model, effort, permissions, and startup settings

**Other Highlights**
- Spec Map (renamed from Software Map): interactive dependency graph with position persistence
- Implementation notes migrated to standalone `*.impl.md` companion files
- File access permissions formalized across all roles
- Bidirectional spec-code audit (`/pl-spec-code-audit`) shared between Architect and Builder
- Complete QA verification pass across all 31 features

### v0.5.0 — 2026-02-22

- Initial release of Purlin: Collaborative Design-Driven Agentic Development Framework
- CDD Dashboard with role-based status columns, release checklist UI, and software map
- Critic coordination engine with dual-gate validation, regression scoping, and role-specific action items
- Layered instruction architecture (base + project override layers)
- Submodule bootstrap and upstream sync tooling

**Known limitations:**
- Built exclusively for Claude Code. Supporting additional models is a goal but model feature disparity makes that non-trivial.
- The release checklist can stress context windows. Interrupt and resume with: `/pl-release-run start with step X, steps 1 through X-1 have passed`.
