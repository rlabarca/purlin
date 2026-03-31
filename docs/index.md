<p align="center">
  <img src="../assets/purlin-logo.svg" alt="Purlin" width="400">
</p>

# Purlin Documentation

Purlin is a spec-first development framework. You write specs, build from them, and verify the result — with one AI agent that tracks what's in sync and what's drifted. Three people (or one person wearing three hats) collaborate through specs: **PM**, **Engineer**, and **QA**.

---

## Start Here

* [Quick Start](#quick-start) — Get a project running in 60 seconds.
* [How Collaboration Works](#how-collaboration-works) — PM, Engineer, QA — who does what and how specs connect you.
* [Installation Guide](installation-guide.md) — Full setup: marketplace, plugin install, project init.

## By Role

* [For PMs](#for-pms) — Define what to build. Write specs, import designs, set standards.
* [For Engineers](#for-engineers) — Build from specs. Write code, tests, companion files.
* [For QA](#for-qas) — Verify the work. Classify scenarios, run regressions, record findings.

## Key Concepts

* [Specs and Sync](spec-code-sync-guide.md) — How specs and code stay in sync through companion files and sync tracking.
* [Invariants](invariants-guide.md) — Import external rules (Figma designs, security policies, architecture standards) and enforce them automatically.
* [Design Workflow](design-guide.md) — Local anchors, Figma integration, Token Maps, visual specs, and design audit.
* [Figma Integration](figma-guide.md) — MCP setup, Token Map workflow, design briefs, three-source verification.
* [Testing: Smoke, Auto, Regression](#testing-smoke-auto-regression) — What gets tested when, and why.

## Workflows & Tools

* [Testing Workflow](testing-workflow-guide.md) — The full journey: idea → spec → build → verify → regression.
* [Parallel Execution](parallel-execution-guide.md) — Building multiple features simultaneously with worktrees.
* [Worktrees](worktree-guide.md) — Isolated branches for parallel work, merging, crash recovery.
* [Agentic Toolbox](toolbox-guide.md) — Reusable project tools the agent can run on demand.
* [Configuration](config-guide.md) — YOLO mode, find-work, auto-start, config layering.
* [Credential Storage](credential-storage-guide.md) — Secure API token and deploy key management.

## What's New

* [What's New in v0.8.6](whats-new-0.8.6.md) — Plugin migration, sync tracking replaces modes, MCP server, new install model.
* [What's New in v0.8.5](whats-new-0.8.5.md) — Unified agent, Agentic Toolbox, dashboard removal, new launcher.

## Reference

* [Features Folder](features-folder-guide.md) — How feature files are organized.
* [Skill Reference](#skill-reference) — Every command, grouped by role.
* [Reporting Issues](reporting-issues-guide.md) — How to report Purlin framework bugs.

---

## Quick Start

```bash
# One-time: register the marketplace
claude plugin marketplace add git@bitbucket.org:boomerangdev/purlin.git

# Per-project
cd my-project && git init
claude plugin install purlin@purlin --scope project
claude
```

Inside the session:

```
purlin:init
```

You're ready. Run `purlin:status` to see what needs doing, or jump straight in:

```
purlin:spec login-page          # PM: write a spec
purlin:build login-page         # Engineer: build it
purlin:verify login-page        # QA: verify it
```

---

## How Collaboration Works

Purlin is built for teams where a PM, Engineer, and QA work on the same project — or for a solo developer playing all three roles. The agent doesn't enforce who you are. It tracks what's happening: which specs exist, which code has been written, and where things are out of sync.

```
PM writes the spec → Engineer builds from it → QA verifies the result
         ↑                                            |
         +------------ discoveries flow back ---------+
```

**Specs are the contract.** The PM writes what to build. The Engineer builds it and documents any deviations in a companion file. QA verifies the result against the spec. When QA finds problems, they're routed back to the right person — bugs to Engineer, spec issues to PM.

**Sync tracking keeps everyone honest.** Purlin watches file changes and reports drift: "code changed but the spec didn't" or "spec updated but code hasn't caught up." Run `purlin:status` to see the full picture at any time.

**Invariants protect what matters.** External standards (Figma design systems, security policies, architecture rules) are imported as invariants. They can't be edited locally — only synced from their source. This prevents accidental drift from org-wide standards.

**Everyone reads specs. Everyone benefits.**
- Engineers read specs before building. The spec tells them exactly what to implement.
- QA reads specs to know what to verify. Scenarios are written right in the spec.
- PMs read companion files to see what actually got built vs. what they specified.

---

## For PMs

You define **what** to build. Your main tools:

| What you want to do | Command |
|---|---|
| Write a feature spec | `purlin:spec <topic>` |
| Set project-wide design standards | `purlin:anchor design_<name>` |
| Import a Figma design system | `purlin:invariant add-figma <url>` |
| Import external rules (git repo) | `purlin:invariant add <repo-url> <file>` |
| Sync an invariant after source changes | `purlin:invariant sync <file>` |
| Audit design health across features | `purlin:design-audit` |
| Check what needs your attention | `purlin:status` |

**Start here:** Run `purlin:spec <topic>` to write your first spec. The agent asks structured questions about scope, edge cases, and constraints, then produces a spec with requirements, QA scenarios, and optional visual specifications.

**With Figma:** Import your design system as an invariant first (`purlin:invariant add-figma <url>`), then reference it when writing specs. The agent reads Figma via MCP, extracts tokens and components, and generates a `brief.json` so Engineers don't need Figma access.

**Without Figma:** Describe the feature in plain language. Create local design anchors (`purlin:anchor design_tokens`) for project-wide visual standards.

**Review Engineer deviations:** After a build, check `purlin:status` for companion file entries tagged `[DEVIATION]`, `[AUTONOMOUS]`, or `[DISCOVERY]`. These are places where the implementation diverged from your spec.

See the full [PM Guide](pm-agent-guide.md) and [Design Guide](design-guide.md).

---

## For Engineers

You build **from specs**. Your main tools:

| What you want to do | Command |
|---|---|
| Implement a feature | `purlin:build [name]` |
| Run unit tests | `purlin:unit-test [name]` |
| Run visual tests (Playwright) | `purlin:web-test [name]` |
| Plan delivery for multiple features | `purlin:delivery-plan` |
| Start/stop the dev server | `purlin:server` |
| Flag something you can't build | `purlin:infeasible <name>` |
| Suggest a spec change to PM | `purlin:propose <topic>` |
| Audit spec-code alignment | `purlin:spec-code-audit` |
| Reverse-engineer specs from code | `purlin:spec-from-code` |

**Start here:** Run `purlin:build <name>` to implement a feature. The agent reads the spec, writes code and tests, documents decisions in a companion file, and marks the feature ready for QA.

**Companion files are required.** Every code change gets a companion file entry. At minimum: `[IMPL] Built the thing`. If you deviate from the spec, use `[DEVIATION]` with a reason. This keeps PM in the loop without blocking you.

**Parallel builds:** When a delivery plan has independent features, `purlin:build` spawns worktree sub-agents to build them simultaneously. You don't manage this — it happens automatically.

See the full [Engineer Guide](engineer-agent-guide.md).

---

## For QAs

You verify **what was built matches what was specified**. Your main tools:

| What you want to do | Command |
|---|---|
| Verify features | `purlin:verify [name] [--auto-fix]` |
| Mark a feature complete | `purlin:complete <name>` |
| Record a bug or finding | `purlin:discovery [name]` |
| Manage regression suites | `purlin:regression` |
| Promote a feature to smoke tier | `purlin:smoke <feature>` |
| Get smoke tier suggestions | `purlin:smoke suggest` |
| View verification status | `purlin:qa-report` |
| Manage test fixtures | `purlin:fixture` |

**Start here:** Run `purlin:verify` to verify all features waiting for QA, or `purlin:verify <name>` for a specific one. The agent runs automated scenarios first, then walks you through manual checks.

**Findings route automatically.** Bugs go to Engineer. Spec disputes and intent drift go to PM. Everything is tracked in discovery sidecar files.

**Auto-fix loop:** Use `purlin:verify --auto-fix` and the agent will attempt to fix failing tests inline, then re-verify.

See the full [QA Guide](qa-agent-guide.md).

---

## Testing: Smoke, Auto, Regression

Purlin has three testing tiers. They run in order during verification.

### Smoke Tests — Run First, Every Time

Smoke tests cover your critical path — the 5-15 features users would notice first if broken. They run before anything else during `purlin:verify`.

- **Promote a feature:** `purlin:smoke config-layering`
- **Get suggestions:** `purlin:smoke suggest`
- **If smoke fails:** QA halts and asks whether to stop or continue. Smoke failures are blocking.

### Auto Scenarios — Run After Smoke

Scenarios tagged `@auto` in specs are automatable. During verification, QA classifies new scenarios and runs all existing `@auto` scenarios.

- These are scenario-level tests defined in the spec and executed by the agent.
- QA proposes automation where possible; the rest gets tagged `@manual`.

### Regression Suites — Run After Auto

Regression tests ensure features keep working after future changes. QA authors regression files from spec scenarios and evaluates results.

```
purlin:regression author      # Create regression files from spec scenarios
purlin:regression run         # Execute the suite
purlin:regression evaluate    # Evaluate results, create bug reports for failures
```

- Results go stale when source code or test infrastructure changes.
- Stale features are prioritized for re-testing.
- Cross-feature regression (B2) runs when all features in a verification group finish building.

**The order during verification:**
1. Smoke tests (critical path — blocks on failure)
2. `@auto` regression scenarios (existing automated coverage)
3. New scenario classification (proposes auto vs. manual)
4. Manual verification (human walks through remaining checks)

---

## Skill Reference

Run `purlin:help` inside any session for the full list.

### Available to Everyone

| Skill | What It Does |
|-------|--------------|
| `purlin:status` | Shows feature states, sync status, and action items. |
| `purlin:help` | Prints available commands. |
| `purlin:find <topic>` | Searches all specs for coverage of a topic. |
| `purlin:config [setting] [on\|off]` | View or change settings (yolo, find-work, auto-start). |
| `purlin:resume` | Session recovery after `/clear` or context compaction. |
| `purlin:update` | Update Purlin to the latest release. |
| `purlin:remote <cmd>` | Branch collaboration — push, pull, remotes, branch lifecycle. |
| `purlin:whats-different` | Compare current branch against main. |
| `purlin:worktree <cmd>` | Worktree management — list, cleanup. |
| `purlin:merge` | Merge a worktree branch back to source. |
| `purlin:toolbox <cmd>` | Agentic Toolbox — list, run, create, share tools. |
| `purlin:session-name` | Update terminal session display name. |
| `purlin:init` | Initialize a project for Purlin. |
| `purlin:purlin-issue` | Report a Purlin framework bug. |

### PM Skills

| Skill | What It Does |
|-------|--------------|
| `purlin:spec <topic>` | Create or refine a feature spec. |
| `purlin:anchor <name>` | Create or update a design/policy anchor. |
| `purlin:design-audit` | Audit design artifacts for consistency. |
| `purlin:invariant <cmd>` | Import, sync, and manage invariants. |

### Engineer Skills

| Skill | What It Does |
|-------|--------------|
| `purlin:build [name]` | Implement a feature from its spec. |
| `purlin:unit-test [name]` | Run unit tests with quality rubric. |
| `purlin:web-test [name]` | Run Playwright visual verification. |
| `purlin:delivery-plan` | Create phased delivery for multiple features. |
| `purlin:server` | Start, stop, restart the dev server. |
| `purlin:infeasible <name>` | Escalate a feature that can't be built as specified. |
| `purlin:propose <topic>` | Suggest a spec change to PM. |
| `purlin:spec-code-audit` | Audit alignment between specs and code. |
| `purlin:spec-from-code` | Reverse-engineer specs from existing code. |
| `purlin:anchor arch_*` | Create or update architecture anchors. |
| `purlin:tombstone` | Retire a feature with a tombstone record. |

### QA Skills

| Skill | What It Does |
|-------|--------------|
| `purlin:verify [name]` | Run the verification workflow. |
| `purlin:complete <name>` | Mark a verified feature as complete. |
| `purlin:discovery [name]` | Record a bug, spec dispute, or finding. |
| `purlin:regression` | Author, run, or evaluate regression suites. |
| `purlin:smoke <feature>` | Promote a feature to smoke tier, or suggest candidates. |
| `purlin:qa-report` | Summarize open discoveries and verification status. |
| `purlin:fixture` | Manage test fixtures — create, list, verify, push. |
