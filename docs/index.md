# Purlin Documentation

Purlin is a spec-first framework where one AI agent operates in three modes — PM, Engineer, and QA — to take features from idea to verified implementation. These guides cover how to use each mode, end-to-end workflows, and project setup.

---

## Using the Agent

* [PM Mode Guide](pm-agent-guide.md) — Write feature specs from ideas, Figma designs, or live web pages.
* [Engineer Mode Guide](engineer-agent-guide.md) — Implement features from specs, write tests, and manage delivery plans.
* [QA Mode Guide](qa-agent-guide.md) — Verify features, classify scenarios, build regression suites, and run smoke tests.

## Workflows

* [Testing Workflow Guide](testing-workflow-guide.md) — The complete journey from idea through spec, implementation, verification, and regression coverage.
* [Parallel Execution Guide](parallel-execution-guide.md) — How the agent builds independent features in parallel using git worktrees.

## Setup & Maintenance

* [Installation Guide](installation-guide.md) — Adding Purlin to a new project, joining an existing team, updating to a newer version, and configuration.
* [Reporting Issues](reporting-issues-guide.md) — How to report bugs in the Purlin framework itself.

---

## Skill Reference

Skills are slash commands that trigger specific workflows. Run `/pl-help` inside any session for the full list. Here are the most commonly used ones:

### All Modes

| Skill | What It Does |
|-------|--------------|
| `/pl-status` | Shows feature states and action items for the current mode. |
| `/pl-mode <pm\|engineer\|qa>` | Switch to a different mode. |
| `/pl-help` | Prints the command table for your current mode. |
| `/pl-find <topic>` | Searches all specs for coverage of a topic. |
| `/pl-resume [save]` | Saves or restores session state across context clears. |
| `/pl-update-purlin` | Updates the Purlin submodule and refreshes artifacts. |

### PM Mode

| Skill | What It Does |
|-------|--------------|
| `/pl-spec <topic>` | Creates or refines a feature spec with guided questions. |
| `/pl-anchor <name>` | Creates or updates a design or policy anchor node. |
| `/pl-design-ingest <source>` | Ingests a Figma URL or live web page into a visual specification. |
| `/pl-design-audit` | Audits design artifacts for consistency with specs and anchors. |

### Engineer Mode

| Skill | What It Does |
|-------|--------------|
| `/pl-build [name]` | Implements features following the build protocol. |
| `/pl-unit-test [name]` | Runs unit tests with the quality rubric. |
| `/pl-web-test [name]` | Runs Playwright visual verification for web features. |
| `/pl-delivery-plan` | Creates a phased delivery plan for multiple features. |
| `/pl-infeasible <name>` | Escalates a feature that cannot be implemented as specified. |
| `/pl-propose <topic>` | Suggests a spec change to PM mode. |

### QA Mode

| Skill | What It Does |
|-------|--------------|
| `/pl-verify [name]` | Runs the verification workflow (automated first, then manual). |
| `/pl-complete <name>` | Marks a verified feature as complete. |
| `/pl-discovery [name]` | Records a structured finding (bug, spec dispute, etc.). |
| `/pl-regression` | Manages regression suites — author, run, or evaluate. |
| `/pl-smoke <feature>` | Promotes a feature to the smoke testing tier. |
| `/pl-qa-report` | Summarizes open discoveries and verification status. |
