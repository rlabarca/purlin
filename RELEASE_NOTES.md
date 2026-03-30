# Release Notes

### v0.8.6 — 2026-03-29

**Purlin Is Now a Claude Code Plugin**
Install with one command, enable per-project. No more submodule management, launcher scripts, or path configuration. Just `claude` and go.

- **Zero-friction install** — Add the plugin once and it works in every project you enable it for. No submodule cloning, no symlinks, no shell scripts to maintain
- **Automatic session recovery** — Purlin restores your context on every launch. No need to manually run a resume command after context clears or terminal restarts
- **Hard mode boundaries** — Write-access rules are now mechanically enforced. Engineer can't accidentally write specs, PM can't accidentally write code. Violations are blocked before they happen, not caught after
- **Skills renamed** — All commands changed from `/pl-*` to `purlin:*` (e.g., `purlin:build`, `purlin:spec`, `purlin:verify`). Tab-completion works out of the box
- **Instant status checks** — The MCP server keeps scan results warm in memory. `purlin:status`, `purlin:graph`, and `purlin:scan` respond immediately instead of re-scanning every time
- **Invariant system** — Import externally-owned constraints (architecture standards, design systems, compliance policies, operational mandates) from git repos or Figma. Invariants are immutable locally — only the source owner can change them. `purlin:invariant add <repo>` to import, `purlin:invariant sync` to pull updates. Global invariants auto-apply to every feature; scoped invariants attach via prerequisite links. FORBIDDEN patterns block builds at preflight, and features automatically cascade-reset when an invariant updates
- **YOLO mode** — `purlin:config yolo on` auto-approves permission prompts so you can stay in flow during trusted sessions
- **New `purlin:update` skill** — Migrates existing v0.8.5 projects to the plugin format automatically. Handles config, file moves, and artifact cleanup
- **Feature specs organized by category** — Specs now live in `features/<category>/` subfolders. Navigation and filtering are faster on large projects
- **Credentials in keychain** — API tokens (Figma, Confluence, deploy) stored in macOS keychain instead of plain-text config files

**Removed**
- `pl-run.sh` launcher (504 lines) — replaced by plugin hooks
- `pl-init.sh` setup script (808 lines) — replaced by `purlin:init`
- `purlin/` submodule directory — plugin lives in Claude Code's cache
- `.claude/commands/pl-*.md` (36 files) — replaced by `skills/*/SKILL.md`
- `instructions/` and `tools/` directories — consolidated into `agents/`, `references/`, `scripts/`

### v0.8.5 — 2026-03-26

**Unified Agent**
- One agent, three modes. `purlin:mode pm|engineer|qa` replaces the four separate launchers (`pl-run-architect.sh`, `pl-run-builder.sh`, `pl-run-qa.sh`, `pl-run-pm.sh`). `purlin:resume` handles session recovery after context clears
- Automated migration from v0.8.4: run `purlin:update` and the migration module handles config consolidation, file renames, and artifact cleanup
- Strict write boundaries enforced per mode -- open mode (no mode active) blocks all file writes until a mode is activated

**CDD Dashboard & Critic Retired**
- The CDD Dashboard server and Critic coordination engine have been fully removed. The scan engine and `purlin:status` now handle all project state assessment directly
- Simpler, faster feedback loop -- no background server to manage

**Agentic Toolbox**
- The old release checklist is replaced by independent, reusable tools that run in any order at any time
- Ships with two built-in Purlin tools (Spec Check, Spec Map) and four project tools (Record Version Notes, Docs Update, Push to Bitbucket, Push to GitHub)
- Create your own tools, share them via git repos, or copy and customize Purlin's built-ins
- `purlin:toolbox list|run|create|edit|copy|delete|add|pull|push`

**Spec-Code Audit**
- `purlin:spec-code-audit` now detects circular dependencies in the prerequisite graph and recommends which link to break
- Spec Check tool provides a comprehensive integrity scan: stale references, naming consistency, category grouping

**QA Improvements**
- `purlin:verify` adds an auto-fix iteration loop -- QA finds a bug, internal mode switch lets Engineer fix it, QA re-verifies, repeat until clean
- Strategy menu for verification: choose targeted, full, or regression-only verification runs
- QA mode now speaks like Michelangelo from Teenage Mutant Ninja Turtles -- same technical accuracy, surfer-dude delivery

**Worktree Management**
- `purlin:worktree` for listing, creating, and cleaning up isolated git worktrees
- Session locks prevent concurrent agents from colliding in the same worktree
- Merge serialization via lock file prevents race conditions between parallel merges
- Automatic merge-back on session exit (SessionEnd hook)

**Session & Terminal**
- Terminal badge always includes branch context: `Engineer (main)`, `QA (feature-xyz)`, `PM (W1)` for worktrees
- PID-scoped checkpoint files so concurrent terminals never collide
- Session recovery unified into `purlin:resume` -- checkpoint save, merge recovery, and restore all in one skill. Not required to start working; invoke any skill directly
- Warp terminal support for tab naming alongside iTerm2 badges

**New & Consolidated Skills**
- `purlin:mode` -- switch modes or check current mode status without arguments
- `purlin:remote` -- consolidates `purlin:remote-push`, `purlin:remote-pull`, and `purlin:remote-add` into one skill
- `purlin:regression` -- consolidates `purlin:regression-author`, `purlin:regression-run`, and `purlin:regression-evaluate`
- `purlin:smoke` -- smoke-first verification gate for QA
- `purlin:whats-different` -- now includes companion staleness detection and mode-aware impact briefing

**Scan Engine**
- Tombstone scanning surfaces retired features in `purlin:status`
- Spec modification detection flags features whose spec changed after completion
- `--only` flag for focused output (e.g., `purlin:status --only engineer`)
- Exemption tags (`[Migration]`) suppress false positives during bulk operations

**Documentation**
- All documentation rewritten for the unified agent model
- Clear upgrade path from v0.8.4 with step-by-step instructions in README

**Removed**
- CDD Dashboard (server, tests, all related specs and code)
- Critic coordination engine (replaced by scan engine)
- Four legacy agent launchers (replaced by `purlin:resume`)
- Release checklist system (replaced by Agentic Toolbox)
- 17 legacy feature specs tombstoned

### v0.8.4 — 2026-03-24

**Extended Context Models**
- Agents can now use Opus 4.6 with a 1M token context window -- select it in config or at startup
- A one-time cost warning prevents surprise charges on Pro plans; once acknowledged, it won't ask again

**Parallel Feature Building**
- Engineer implements multiple features at the same time using isolated git worktrees, so large backlogs finish faster
- Delivery plans group independent features into execution groups that build in parallel and merge automatically

**QA Improvements**
- Smoke testing gate -- classify features by priority tier (smoke, standard, full-only) and QA verifies the most critical ones first
- "Just smoke" mode lets you run only the critical checks when you need a fast confidence pass
- Agent behaviors can now be regression-tested so you know when a change breaks something that used to work
- Three new commands (`purlin:regression-author`, `purlin:regression-run`, `purlin:regression-evaluate`) cover the full regression author-run-review cycle
- QA cannot mark a feature complete while regressions are failing -- broken behavior blocks the release

**Engineer Escalation Path**
- Builders can propose spec or anchor node changes directly with `purlin:propose` instead of waiting for the PM
- The Critic automatically surfaces unacknowledged proposals as high-priority PM action items

**Spec-Code Audit**
- `purlin:spec-code-audit` now finds code that has no matching spec, not just specs missing code
- A scope confirmation step lets you choose which features to audit before it starts

**CDD Dashboard**
- Delivery plan progress shows execution groups and parallel build state at a glance

**Delivery Plans**
- Phase sizing automatically adjusts based on your model's context window so phases don't exceed capacity
- Execution groups let you combine phases that can run in parallel, cutting total delivery time

**Documentation**
- Five new guides ship with the framework: PM Agent, Critic & CDD, Installation, Testing Workflow, and Parallel Execution
- Docs are auto-refreshed and cross-linked during every release -- no more stale references

**New Commands**
- `purlin:purlin-issue` -- Report a framework bug or feature request directly from any agent session
- `purlin:remote` -- Set up a git remote for collaboration directly from any agent session

**Test Fixtures**
- Fixture repos can be pushed to a remote so every team member starts from the same test state

**Config & Infrastructure**
- Named sessions so Claude Code's remote control can target each role individually
- Automatic Claude Code version check if the installed version is below the minimum required
- When Purlin adds new models upstream, your local config overrides are preserved instead of replaced
- Tools now correctly detect the project root when Purlin is nested as a submodule inside a larger repository

**Workflow**
- STALE web test verdicts automatically record as PM-routed discoveries -- no manual Engineer triage needed
- The PM silently resolves routine Critic items (untracked files, straightforward acknowledgments) and summarizes what it did

**Known Issues**
- QA process is still not optimal. Gaps in workflow to be addressed.

### v0.8.3 — 2026-03-19

**New Commands**
- `purlin:web-test` -- Playwright-based web verification, replaces `purlin:aft-web`
- `purlin:whats-different` -- Compare your current branch against main to see what changed
- `purlin:regression` -- Structured regression test pipeline with declarative scenario harness [ALPHA - basic plumbing only]

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
- `purlin:update` -- Now shows MCP manifest diffs when updating the submodule
- `purlin:remote-push` / `purlin:remote-pull` -- Work gracefully without a remote configured
- `purlin:help` -- Now discovers CLI scripts alongside slash commands
- Continuous Phase Engineer -- Parallel worktree execution with inter-phase Critic integration [ALPHA - UNSTABLE]

### v0.8.2 — 2026-03-17

**PM Agent Role**
- Full PM role with launcher, Critic/CDD column, command routing, and PM-first agent ordering

**Figma Design Pipeline**
- Figma MCP integration for design ingest and audit with Token Map + brief.json pipeline
- Identity token auto-detection and annotation extraction during ingestion
- Code Connect and Dev Mode lifecycle integration

**Continuous Phase Engineer (initial implementation -- needs testing and improvement)**
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
- Claude Code hook on `/clear` event reminds the agent to run `purlin:resume` on next prompt

**Fixes**
- Critic: NameError fix, circular prerequisite fix, requirements-section change detection
- CDD: JS/Python f-string escaping, PM-first column alignment, modal overflow fix
- Instructions: strengthened zero-code mandates, fixed PM sidecar contradiction
- Overrides: updated stale submodule reference paths

**Engineer Quality**
- Critic now enforces that tests must break when the behavior they cover is removed -- tests that pass without their implementation are flagged

**Architecture**
- Unified role status model in `critic_role_status.md`
- Deep spec-code audit: remediated 11 features and 7 anchors
- SPEC_DISPUTE routing with PM/PM handoff
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
- `purlin:remote-push` and `purlin:remote-pull` work with any branch. Pushes fetch first and block if behind. Pulls merge to preserve shared history.

**Removed: Isolated Teams**
- The worktree-based isolated teams system (`purlin:push`, `purlin:pull`, CDD Isolated Teams panel, Handoff Checklist, and the Isolated Agent Collaboration policy) has been fully retired. Branch collaboration covers the same use cases with less complexity.

**Web Verify (`purlin:web-verify`)** *(renamed to `purlin:aft-web` -- see AFT below)*
- New Playwright-based automated verification for features with web UIs. Any feature with a `> Web Testable: <url>` metadata tag can have its manual scenarios and visual specification checklist items verified automatically in a real browser.
- Supports `> Web Port File:` for dynamic ports and `> Web Start:` for auto-starting servers.
- Screenshots saved to `.purlin/runtime/web-verify/` for post-run review.

**Automated Feedback Tests (AFT)**
- Introduced the AFT pattern as an architectural anchor node (`arch_automated_feedback_tests.md`). AFTs are tools that script interactions with a target system, observe results, and report structured pass/fail with evidence.
- `purlin:web-verify` renamed to `purlin:aft-web` as the first AFT implementation. Metadata tags renamed: `> Web Testable:` -> `> AFT Web:`, `> Web Start:` -> `> AFT Start:`, `> Web Port File:` removed (port resolution is now internal to the tool).
- Engineer now owns all automated verification (AFT:Web, AFT:TestOnly, AFT:Skip). QA only sees manual items.
- New B1/B2/B3 sub-phase protocol for phased delivery: Build, Test (cross-feature regression), Fix (analyze-first).

**Test Fixtures (`purlin:fixture`)**
- New test fixture system for scenarios that need controlled project state (specific git history, config values, branch topologies). Each fixture is an immutable git tag in a dedicated fixture repo -- no complex setup code needed.
- `tools/fixtures/setup_fixture_repo.sh` ships with 74 pre-built fixture tags covering CDD lifecycle, branch collaboration, agent configuration, and more.
- Convention-over-configuration: the fixture repo lives at `tests/fixtures/fixture-repo/` and is auto-created on first test run.
- `purlin:fixture` skill available to all roles for managing fixtures.

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
- Running `pl-init.sh` on an existing project refreshes commands without overwriting config.
- `purlin:update` provides intelligent submodule updates with semantic change analysis and conflict resolution for `.purlin/` customizations.

### v0.7.5 — 2026-02-26

**Runtime Port Override**
- `-p <port>` flag lets you override the CDD Dashboard port at runtime -- useful for running multiple projects on the same machine

**Upstream Sync Modernization**
- `purlin:update` replaces the old `sync_upstream.sh` script with semantic analysis and conflict resolution

### v0.7.0 — 2026-02-26

**Remote Collaboration**
- Multi-machine collaboration via collab sessions (`collab/<name>` branches on a hosted remote)
- Dashboard section with session management and sync badges
- `purlin:remote-push` and `purlin:remote-pull` for collab branch sync

**Other Highlights**
- Spec Map: inter-category topological ordering with edge arrows and dynamic label sizing
- Critic: targeted scope completeness audit and delivery plan scope reset
- `purlin:spec-from-code` for reverse-engineering specs from existing codebases (experimental)

### v0.6.0 — 2026-02-24

**Isolated Teams**
- Named git worktrees for concurrent agent sessions with dashboard state tracking
- `purlin:push` and `purlin:pull` for merge-before-proceed workflow

**Agent Configuration**
- Dashboard panel for per-agent model, effort, permissions, and startup settings

**Other Highlights**
- Spec Map (renamed from Software Map): interactive dependency graph with position persistence
- Implementation notes migrated to standalone `*.impl.md` companion files
- File access permissions formalized across all roles
- Bidirectional spec-code audit (`purlin:spec-code-audit`) shared between PM and Engineer
- Complete QA verification pass across all 31 features

### v0.5.0 — 2026-02-22

- Initial release of Purlin: Collaborative Design-Driven Agentic Development Framework
- CDD Dashboard with role-based status columns, release checklist UI, and software map
- Critic coordination engine with dual-gate validation, regression scoping, and role-specific action items
- Layered instruction architecture (base + project override layers)
- Submodule bootstrap and upstream sync tooling

**Known limitations:**
- Built exclusively for Claude Code. Supporting additional models is a goal but model feature disparity makes that non-trivial.
- The release checklist can stress context windows. Interrupt and resume with: `purlin:release-run start with step X, steps 1 through X-1 have passed`.
