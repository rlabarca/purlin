<p align="center">
  <img src="../assets/purlin-logo.svg" alt="Purlin" width="400">
</p>

# Purlin Documentation

Purlin is a spec-first framework where one AI agent operates in three modes — PM, Engineer, and QA — to take features from idea to verified implementation. These guides cover how to use each mode, end-to-end workflows, and project setup.

---

## Using the Agent

* [Configuration Guide](config-guide.md) — YOLO mode, find-work, auto-start, and config file layering.
* [Common Commands Guide](common-commands-guide.md) — Status, mode switching, collaboration, session management, and other commands available in any mode.
* [PM Mode Guide](pm-agent-guide.md) — Write feature specs from ideas, Figma designs, or live web pages.
* [Engineer Mode Guide](engineer-agent-guide.md) — Implement features from specs, write tests, and manage delivery plans.
* [QA Mode Guide](qa-agent-guide.md) — Verify features, classify scenarios, build regression suites, and run smoke tests.

## Workflows

* [Testing Workflow Guide](testing-workflow-guide.md) — The complete journey from idea through spec, implementation, verification, and regression coverage.
* [Testing Lifecycle Reference](../references/testing_lifecycle.md) — Who defines, implements, runs, and verifies each test type across PM, Engineer, and QA modes. Includes the auto-fix iteration loop and failure routing.
* [Spec-Code Sync Guide](spec-code-sync-guide.md) — How specs and code stay in sync through companion files, decision tags, and enforcement gates.
* [Design Guide](design-guide.md) — Working with designs and design anchors: local anchors, Figma invariants, Token Maps, visual specifications, and design audit.
* [Figma Integration Guide](figma-guide.md) — Figma MCP setup, Token Map workflow, design briefs, and three-source verification.
* [Invariants Guide](invariants-guide.md) — Import external rules (architecture standards, security policies, design systems) and enforce them automatically across all features.
* [Worktree Guide](worktree-guide.md) — Running multiple agents in parallel with isolated worktrees, merging work back, and recovering from crashes.
* [Parallel Execution Guide](parallel-execution-guide.md) — How the agent builds independent features in parallel using git worktrees.
* [Agentic Toolbox Guide](toolbox-guide.md) — How to use, create, and share project tools.
* [Credential Storage Guide](credential-storage-guide.md) — How Purlin stores and accesses API tokens and deploy keys securely via Claude Code's plugin system.

## What's New

* [What's New in v0.8.6](whats-new-0.8.6.md) — Plugin migration, mechanical mode guard, MCP server, hooks, new install model, skill renaming.
* [What's New in v0.8.5](whats-new-0.8.5.md) — Unified agent, mode switching, Agentic Toolbox, dashboard removal, new launcher, and skill changes.

## Project Structure

* [The Features Folder](features-folder-guide.md) — How feature files are organized into category subfolders, system folders, and file types.

## Setup & Maintenance

* [Installation Guide](installation-guide.md) — Registering the plugin, adding Purlin to a project, joining an existing team, upgrading from submodule, and configuration.
* [Reporting Issues](reporting-issues-guide.md) — How to report bugs in the Purlin framework itself.

---

## Skill Reference

Skills are slash commands that trigger specific workflows. Run `purlin:help` inside any session for the full list.

### All Modes

| Skill | What It Does |
|-------|--------------|
| `purlin:status` | Shows feature states and action items for the current mode. |
| `purlin:mode <pm\|engineer\|qa>` | Switch to a different mode. |
| `purlin:help` | Prints the command table for your current mode. |
| `purlin:find <topic>` | Searches all specs for coverage of a topic. |
| `purlin:config [setting] [on\|off]` | View or change behavior settings (yolo, find-work, auto-start). |
| `purlin:resume [save\|merge-recovery]` | Session recovery after `/clear` or context compaction. Not required to start working — invoke any skill directly instead. |
| `purlin:update [version] [--dry-run] [--auto-approve]` | Updates the Purlin plugin to the latest release tag (or a specified version). |
| `purlin:remote <cmd>` | Branch collaboration — push, pull, add, or manage remotes. |

| `purlin:whats-different` | Compare current branch against main with mode-aware impact briefing. |
| `purlin:session-name [label]` | Update the terminal session display name. |
| `purlin:worktree <cmd>` | Worktree management — list active worktrees or clean up stale ones. |
| `purlin:merge` | Merge a worktree branch back to the source branch. |
| `purlin:purlin-issue` | Report a bug or feature request in the Purlin framework. |
| `purlin:init [--force]` | Initialize a project for Purlin. `--force` re-initializes. |
| `purlin:toolbox <cmd>` | Agentic Toolbox — list, run, create, edit, and share project tools. |

### PM Mode

| Skill | What It Does |
|-------|--------------|
| `purlin:spec <topic>` | Creates or refines a feature spec with guided questions. |
| `purlin:anchor <name>` | Creates or updates a design or policy anchor node. |
| `purlin:design-audit` | Audits design artifacts for consistency with specs and anchors. |
| `purlin:invariant <cmd>` | Imports, syncs, and manages externally-sourced invariant constraints. |

### Engineer Mode

| Skill | What It Does |
|-------|--------------|
| `purlin:build [name]` | Implements features following the build protocol. |
| `purlin:unit-test [name]` | Runs unit tests with the quality rubric. |
| `purlin:web-test [name]` | Runs Playwright visual verification for web features. |
| `purlin:delivery-plan` | Creates a phased delivery plan for multiple features. |
| `purlin:server` | Start, stop, or restart the dev server. |
| `purlin:infeasible <name>` | Escalates a feature that cannot be implemented as specified. |
| `purlin:propose <topic>` | Suggests a spec change to PM mode. |
| `purlin:spec-code-audit [--deep]` | Audits alignment between feature specs and implementation. |
| `purlin:spec-from-code` | Reverse-engineers feature specs from existing code. |
| `purlin:anchor arch_*` | Creates or updates technical architecture anchors. |
| `purlin:tombstone` | Retires a feature with a tombstone record. |

### QA Mode

| Skill | What It Does |
|-------|--------------|
| `purlin:verify [name] [--auto-fix]` | Runs the verification workflow (automated first, then manual). |
| `purlin:complete <name>` | Marks a verified feature as complete. |
| `purlin:discovery [name]` | Records a structured finding (bug, spec dispute, etc.). |
| `purlin:regression` | Manages regression suites — author, run, or evaluate. |
| `purlin:smoke <feature\|suggest>` | Promotes a feature to smoke tier, or suggests candidates. |
| `purlin:qa-report` | Summarizes open discoveries and verification status. |
| `purlin:fixture` | Manages test fixtures — create, list, verify, or push to remote. |
