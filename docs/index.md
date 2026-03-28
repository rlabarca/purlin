<p align="center">
  <img src="../assets/purlin-logo.svg" alt="Purlin" width="400">
</p>

# Purlin Documentation

Purlin is a spec-first framework where one AI agent operates in three modes — PM, Engineer, and QA — to take features from idea to verified implementation. These guides cover how to use each mode, end-to-end workflows, and project setup.

---

## Using the Agent

* [Common Commands Guide](common-commands-guide.md) — Status, mode switching, collaboration, session management, and other commands available in any mode.
* [PM Mode Guide](pm-agent-guide.md) — Write feature specs from ideas, Figma designs, or live web pages.
* [Engineer Mode Guide](engineer-agent-guide.md) — Implement features from specs, write tests, and manage delivery plans.
* [QA Mode Guide](qa-agent-guide.md) — Verify features, classify scenarios, build regression suites, and run smoke tests.

## Workflows

* [Testing Workflow Guide](testing-workflow-guide.md) — The complete journey from idea through spec, implementation, verification, and regression coverage.
* [Testing Lifecycle Reference](../instructions/references/testing_lifecycle.md) — Who defines, implements, runs, and verifies each test type across PM, Engineer, and QA modes. Includes the auto-fix iteration loop and failure routing.
* [Spec-Code Sync Guide](spec-code-sync-guide.md) — How specs and code stay in sync through companion files, decision tags, and enforcement gates.
* [Invariants Guide](invariants-guide.md) — Import external rules (architecture standards, security policies, design systems) and enforce them automatically across all features.
* [Figma Integration Guide](figma-guide.md) — Turn Figma designs into verified implementations with Token Maps, design briefs, and three-source verification.
* [Worktree Guide](worktree-guide.md) — Running multiple agents in parallel with isolated worktrees, merging work back, and recovering from crashes.
* [Parallel Execution Guide](parallel-execution-guide.md) — How the agent builds independent features in parallel using git worktrees.
* [Agentic Toolbox Guide](toolbox-guide.md) — How to use, create, and share project tools.

## What's New

* [What's New in v0.8.5](whats-new-0.8.5.md) — Unified agent, mode switching, Agentic Toolbox, dashboard removal, new launcher, and skill changes.

## Setup & Maintenance

* [Installation Guide](installation-guide.md) — Adding Purlin to a new project, joining an existing team, updating to a newer version, and configuration.
* [Reporting Issues](reporting-issues-guide.md) — How to report bugs in the Purlin framework itself.

---

## Skill Reference

Skills are slash commands that trigger specific workflows. Run `/pl-help` inside any session for the full list.

### All Modes

| Skill | What It Does |
|-------|--------------|
| `/pl-status` | Shows feature states and action items for the current mode. |
| `/pl-mode <pm\|engineer\|qa>` | Switch to a different mode. |
| `/pl-help` | Prints the command table for your current mode. |
| `/pl-find <topic>` | Searches all specs for coverage of a topic. |
| `/pl-resume [save]` | Saves or restores session state across context clears. |
| `/pl-update-purlin [version]` | Updates the Purlin submodule to the latest release tag (or a specified version) and refreshes artifacts. |
| `/pl-remote <cmd>` | Branch collaboration — push, pull, add, or manage remotes. |
| `/pl-override-edit` | Edit PURLIN_OVERRIDES.md sections. |
| `/pl-whats-different` | Compare current branch against main with mode-aware impact briefing. |
| `/pl-session-name [label]` | Update the terminal session display name. |
| `/pl-worktree <cmd>` | Worktree management — list active worktrees or clean up stale ones. |
| `/pl-merge` | Merge a worktree branch back to the source branch. |
| `/pl-purlin-issue` | Report a bug or feature request in the Purlin framework. |

### PM Mode

| Skill | What It Does |
|-------|--------------|
| `/pl-spec <topic>` | Creates or refines a feature spec with guided questions. |
| `/pl-anchor <name>` | Creates or updates a design or policy anchor node. |
| `/pl-design-ingest <source>` | Ingests a Figma URL or live web page into a visual specification. |
| `/pl-design-audit` | Audits design artifacts for consistency with specs and anchors. |
| `/pl-invariant <cmd>` | Imports, syncs, and manages externally-sourced invariant constraints. |

### Engineer Mode

| Skill | What It Does |
|-------|--------------|
| `/pl-build [name]` | Implements features following the build protocol. |
| `/pl-unit-test [name]` | Runs unit tests with the quality rubric. |
| `/pl-web-test [name]` | Runs Playwright visual verification for web features. |
| `/pl-delivery-plan` | Creates a phased delivery plan for multiple features. |
| `/pl-toolbox <cmd>` | Agentic Toolbox — list, run, create, edit, and share project tools. |
| `/pl-server` | Start, stop, or restart the dev server. |
| `/pl-infeasible <name>` | Escalates a feature that cannot be implemented as specified. |
| `/pl-propose <topic>` | Suggests a spec change to PM mode. |
| `/pl-spec-code-audit` | Audits alignment between feature specs and implementation. |
| `/pl-spec-from-code` | Reverse-engineers feature specs from existing code. |
| `/pl-anchor arch_*` | Creates or updates technical architecture anchors. |
| `/pl-tombstone` | Retires a feature with a tombstone record. |

### QA Mode

| Skill | What It Does |
|-------|--------------|
| `/pl-verify [name]` | Runs the verification workflow (automated first, then manual). |
| `/pl-complete <name>` | Marks a verified feature as complete. |
| `/pl-discovery [name]` | Records a structured finding (bug, spec dispute, etc.). |
| `/pl-regression` | Manages regression suites — author, run, or evaluate. |
| `/pl-smoke <feature>` | Promotes a feature to the smoke testing tier. |
| `/pl-qa-report` | Summarizes open discoveries and verification status. |
| `/pl-fixture` | Manages test fixtures — create, list, verify, or push to remote. |
