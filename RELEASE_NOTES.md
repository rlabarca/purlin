# Release Notes

### RC0.8.4 — 2026-03-20

**Extended Context Models**
- Opus 4.6 [1M] available as an agent model -- select it in the CDD Dashboard or launcher scripts
- Cost warning shown once per model ("Extended context uses additional paid credits on Pro plans"), then auto-acknowledged
- CDD Dashboard displays a confirmation modal when selecting a model with a warning

**Builder Escalation Path**
- Builders can now propose spec or anchor node changes with `[SPEC_PROPOSAL]` tags in companion files
- The Critic routes unacknowledged proposals to the Architect as HIGH-priority action items
- `/pl-propose` command for structured escalation of cross-cutting constraints

**Config & Infrastructure**
- Array-aware config merging -- when Purlin adds new models upstream, local config overrides are preserved instead of replaced
- Nested-project disambiguation -- tools now correctly detect the project root when Purlin is a submodule inside a larger repository

**Workflow**
- STALE verdicts from `/pl-web-test` auto-record as PM-routed discovery sidecar entries -- no manual Builder action needed
- Architect auto-resolves routine Critic items (untracked file triage, straightforward acknowledgments) silently, then summarizes

### v0.8.3 — 2026-03-19

**New Commands**
- `/pl-web-test` -- Playwright-based web verification, replaces `/pl-aft-web`
- `/pl-whats-different` -- Compare your current branch against main to see what changed
- `/pl-regression` -- Structured regression test pipeline with declarative scenario harness [ALPHA - basic plumbing only]

**New Features**
- Terminal Identity -- Terminal title shows which agent role is running
- Terminal Badge -- iTerm terminals get a dynamic badge based on the agent that is running
- Quick Start guide -- New README section with copy-paste setup instructions
- Init preflight checks -- `pl-init.sh` now validates prerequisites and tells you what's missing
- PM first-session guide -- PM agent walks new users through their first spec

**Dashboard**
- Spec Map animations -- Smooth zoom/recenter transitions when navigating the graph
- Abbreviated status commits -- Workspace section shows cleaner commit summaries

**Improvements**
- Simpler startup config -- `find_work`/`auto_start` replaces the old `startup_sequence`/`recommend_next_actions` naming
- `/pl-update-purlin` -- Now shows MCP manifest diffs when updating the submodule
- `/pl-remote-push` / `/pl-remote-pull` -- Work gracefully without a remote configured
- `/pl-help` -- Now discovers CLI scripts alongside slash commands
- Continuous Phase Builder -- Parallel worktree execution with inter-phase Critic integration [ALPHA - UNSTABLE]

### v0.8.2 — 2026-03-17

**PM Agent Role**
- Full PM role with launcher, Critic/CDD column, command routing, and PM-first agent ordering

**Figma Design Pipeline**
- Figma MCP integration for design ingest and audit with Token Map + brief.json pipeline
- Identity token auto-detection and annotation extraction during ingestion
- Code Connect and Dev Mode lifecycle integration

**Continuous Phase Builder (initial implementation -- needs testing and improvement)**
- Terminal canvas engine with width-aware rendering and SIGWINCH resize
- Stale IN_PROGRESS reset on startup, log tail activity display, macOS line buffering fallback
- Graceful SIGINT stop, bootstrap session without delivery plan, dynamic plan handling
- Stacked approval table for narrow terminals

**CDD Dashboard**
- Shared text-based modal infrastructure with metadata tag extraction
- PM as fourth role column, delivery phase API with parallel/dynamic phase awareness

**Automated Feedback Tests (AFT)**
- New AFT pattern; `pl-web-verify` renamed to `pl-aft-web`

**Tools**
- Phase Analyzer for delivery plan processing
- `pl-update-purlin` diff-tree speed optimization
- `pl-session-resume` PM support and startup flag awareness
- Per-role launcher specs split with shared common spec
- Claude Code hook on `/clear` event reminds the agent to run `/pl-resume` on next prompt

**Fixes**
- Critic: NameError fix, circular prerequisite fix, requirements-section change detection
- CDD: JS/Python f-string escaping, PM-first column alignment, modal overflow fix
- Instructions: strengthened zero-code mandates, fixed PM sidecar contradiction
- Overrides: updated stale submodule reference paths

**Builder Quality**
- Critic now enforces that tests must break when the behavior they cover is removed -- tests that pass without their implementation are flagged

**Architecture**
- Unified role status model in `critic_role_status.md`
- Deep spec-code audit: remediated 11 features and 7 anchors
- SPEC_DISPUTE routing with PM/Architect handoff
- Owner metadata tag for feature routing

### v0.8.1 — 2026-03-09

**Discovery Sidecar Files**
- User Testing Discoveries moved from inline feature file sections to separate `.discoveries.md` sidecar files. The Critic, impl_notes_companion, CDD status monitor, collab whats_different, and web-verify all updated to read/write discoveries from sidecar files. This prevents discovery edits from resetting feature lifecycle status to TODO.

**QA Verification Integrity (Critic Section 2.16)**
- New Critic invariant that enforces temporal constraints on QA verification. Detects features that bypassed the TESTING phase entirely (jumped straight to COMPLETE) and features whose TESTING-phase status commit predates the most recent spec reset.

**BUG Routing Updates**
- Updated web-verify and collab whats_different extraction tool to correctly record and route BUG discoveries using the new sidecar file format.

### v0.8.0 — 2026-03-09

**Branch Collaboration (replaces Remote Collaboration)**
- Collaboration now uses plain git branches on your existing remote -- no special `collab/` prefix or session abstraction. Create a branch, push it, and another machine joins by checking it out.
- The CDD Dashboard shows per-branch sync state (SAME, AHEAD, BEHIND, DIVERGED, EMPTY), a contributors table, and last-sync timestamps -- all from locally cached git refs.
- Two-phase join flow with pre-join sync assessment: the dashboard tells you what will happen before you commit to a checkout.
- `/pl-remote-push` and `/pl-remote-pull` work with any branch. Pushes fetch first and block if behind. Pulls merge to preserve shared history.

**Removed: Isolated Teams**
- The worktree-based isolated teams system (`/pl-isolated-push`, `/pl-isolated-pull`, CDD Isolated Teams panel, Handoff Checklist, and the Isolated Agent Collaboration policy) has been fully retired. Branch collaboration covers the same use cases with less complexity.

**Web Verify (`/pl-web-verify`)** *(renamed to `/pl-aft-web` -- see AFT below)*
- New Playwright-based automated verification for features with web UIs. Any feature with a `> Web Testable: <url>` metadata tag can have its manual scenarios and visual specification checklist items verified automatically in a real browser.
- Supports `> Web Port File:` for dynamic ports and `> Web Start:` for auto-starting servers.
- Screenshots saved to `.purlin/runtime/web-verify/` for post-run review.

**Automated Feedback Tests (AFT)**
- Introduced the AFT pattern as an architectural anchor node (`arch_automated_feedback_tests.md`). AFTs are tools that script interactions with a target system, observe results, and report structured pass/fail with evidence.
- `/pl-web-verify` renamed to `/pl-aft-web` as the first AFT implementation. Metadata tags renamed: `> Web Testable:` -> `> AFT Web:`, `> Web Start:` -> `> AFT Start:`, `> Web Port File:` removed (port resolution is now internal to the tool).
- Builder now owns all automated verification (AFT:Web, AFT:TestOnly, AFT:Skip). QA only sees manual items.
- New B1/B2/B3 sub-phase protocol for phased delivery: Build, Test (cross-feature regression), Fix (analyze-first).

**Test Fixtures (`/pl-fixture`)**
- New test fixture system for scenarios that need controlled project state (specific git history, config values, branch topologies). Each fixture is an immutable git tag in a dedicated fixture repo -- no complex setup code needed.
- `tools/fixtures/setup_fixture_repo.sh` ships with 74 pre-built fixture tags covering CDD lifecycle, branch collaboration, agent configuration, and more.
- Convention-over-configuration: the fixture repo lives at `tests/fixtures/fixture-repo/` and is auto-created on first test run.
- `/pl-fixture` skill available to all roles for managing fixtures.

**Automated Test Expansion**
- Fixtures and Web Verify work together to simulate real interface testing across different configuration states. A fixture tag sets up the project state (branch topology, config values, feature lifecycle), then Web Verify launches the dashboard against that state and validates the UI in a real browser. This combination makes it possible to automatically test scenarios that previously required a human to manually set up a project, open a browser, and click through the dashboard.
- 56+ scenarios were rewritten with this pattern in mind, moving from manual QA execution to automated testing. This covers CDD dashboard panels, release checklist steps, agent configuration, and collaboration workflows.
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
- Dashboard panel for per-agent model, effort, permissions, and startup settings

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
