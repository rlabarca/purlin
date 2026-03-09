# Release Notes

### v0.8.0 — 2026-03-09

**Branch Collaboration (replaces Remote Collaboration)**
- Collaboration now uses plain git branches on your existing remote -- no special `collab/` prefix or session abstraction. Create a branch, push it, and another machine joins by checking it out.
- The CDD Dashboard shows per-branch sync state (SAME, AHEAD, BEHIND, DIVERGED, EMPTY), a contributors table, and last-sync timestamps -- all from locally cached git refs.
- Two-phase join flow with pre-join sync assessment: the dashboard tells you what will happen before you commit to a checkout.
- `/pl-remote-push` and `/pl-remote-pull` work with any branch. Pushes fetch first and block if behind. Pulls merge to preserve shared history.

**Removed: Isolated Teams**
- The worktree-based isolated teams system (`/pl-isolated-push`, `/pl-isolated-pull`, CDD Isolated Teams panel, Handoff Checklist, and the Isolated Agent Collaboration policy) has been fully retired. Branch collaboration covers the same use cases with less complexity.

**Web Verify (`/pl-web-verify`)**
- New Playwright-based automated verification for features with web UIs. Any feature with a `> Web Testable: <url>` metadata tag can have its manual scenarios and visual specification checklist items verified automatically in a real browser.
- Supports `> Web Port File:` for dynamic ports and `> Web Start:` for auto-starting servers.
- Screenshots saved to `.purlin/runtime/web-verify/` for post-run review.

**Test Fixtures (`/pl-fixture`)**
- New test fixture system for scenarios that need controlled project state (specific git history, config values, branch topologies). Each fixture is an immutable git tag in a dedicated fixture repo -- no complex setup code needed.
- `tools/fixtures/setup_fixture_repo.sh` ships with 74 pre-built fixture tags covering CDD lifecycle, branch collaboration, agent configuration, and more.
- Convention-over-configuration: the fixture repo lives at `tests/fixtures/fixture-repo/` and is auto-created on first test run.
- `/pl-fixture` skill available to all roles for managing fixtures.

**Automated Test Expansion**
- 56+ scenarios previously requiring manual QA execution have been reclassified to automated testing, enabled by Web Verify and the fixture system. This covers features across CDD dashboard panels, release checklist steps, agent configuration, and collaboration workflows.
- Per-feature `tests.json` files now include `test_file` paths for structural completeness validation.

**Instruction and Skill Optimization**
- Agent instructions heavily optimized to reduce context window usage. Protocol details (user testing, CDD internals, phased delivery, visual spec convention, feature format) extracted to reference files that are loaded on demand rather than included in every session.
- Skill files trimmed to trigger-and-delegate patterns instead of inlining full protocol text.
- Context guard system retired entirely (replaced by Claude Code's built-in auto-compaction).

**New Install and Update Process**
- `pl-init.sh` replaces the old `init.sh` as the single entry point for both first-time setup and collaborator onboarding. It creates launchers, commands, symlinks, and the `.purlin/` directory.
- Agent launchers renamed from `run_*.sh` to `pl-run-*.sh` for consistency. Running `pl-init.sh` on an existing project repairs missing launchers without overwriting config.
- `--regenerate-launchers` flag removes stale launcher names during upgrades.
- `/pl-update-purlin` provides intelligent submodule updates with semantic change analysis and conflict resolution for `.purlin/` customizations.

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
