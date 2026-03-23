# Purlin Documentation

Purlin is an agentic development framework that coordinates four AI agents -- PM, Architect, Builder, and QA -- through structured specs, automated critics, and a real-time dashboard. These guides cover agent interaction, dashboard features, end-to-end workflows, and multi-machine collaboration.

---

## Agent Use

* [PM Agent Guide](pm-agent-guide.md) -- Practical guide for product managers using the PM agent to create feature specs from ideas, Figma designs, and live pages.
* [Architect Agent Guide](architect-agent-guide.md) -- How the Architect agent designs specs, manages anchor nodes, and runs release processes.
* [Builder Agent Guide](builder-agent-guide.md) -- How the Builder agent implements features from specs, writes tests, and verifies visual specifications.
* [QA Agent Guide](qa-agent-guide.md) -- How the QA agent verifies features, classifies scenarios, and authors regression suites.
* [Parallel Execution in the Builder](parallel-execution-guide.md) -- How the Builder agent parallelizes independent features within a delivery plan phase using git worktrees.

## CDD Dashboard

* [CDD Dashboard Guide](cdd-dashboard-guide.md) -- Overview of the CDD Dashboard panels, navigation, and real-time project status visualization.
* [Reading the CDD Status Grid](status-grid-guide.md) -- How to read the status grid showing every feature's current state across all four roles.
* [Spec Map Guide](spec-map-guide.md) -- Interactive dependency graph that visualizes feature prerequisites and category groupings.
* [Agent Configuration Guide](agent-configuration-guide.md) -- Dashboard panel for controlling each agent's model, optimization effort, permissions, and auto-start behavior.

## Workflow & Process

* [Installing and Updating Purlin](installation-guide.md) -- Adding Purlin to a new project, joining an existing team, and updating to a newer version.
* [The Critic and CDD](critic-and-cdd-guide.md) -- How the Critic coordination engine and CDD Monitor work together to direct agents and inform humans.
* [Purlin Testing Workflow Guide](testing-workflow-guide.md) -- Taking a feature from idea through spec, implementation, and verified automated regression coverage.
* [Reporting Purlin Issues](reporting-issues-guide.md) -- How to report bugs in the Purlin framework using `/pl-purlin-issue`.

## Collaboration

* [Branch Collaboration Guide](branch-collaboration-guide.md) -- Multi-machine workflow for sharing branches between a PM and engineer through a shared remote repository.

---

## Skill Reference

Skills are slash commands you type (or the agent invokes automatically) to trigger specific workflows. Each skill loads a full protocol -- the agent knows exactly what to do when a skill is invoked.

**Caller column:** "You" means you typically type the command. "Agent" means the agent calls it during its workflow. "Either" means both are common.

### Common Skills (All Roles)

#### Status & Navigation

| Skill | Caller | What It Does |
|-------|--------|--------------|
| `/pl-status` | You | Runs the Critic and shows the current state of every feature with role-specific action items. |
| `/pl-help` | You | Prints the command table for your current role and lists available launcher scripts. |
| `/pl-find <topic>` | You | Searches all specs for coverage of a topic. Reports which features discuss it and whether a new spec is needed. |
| `/pl-cdd` | You | Starts, stops, or restarts the CDD Dashboard web server. Prints the URL on start. |

#### Session & Configuration

| Skill | Caller | What It Does |
|-------|--------|--------------|
| `/pl-resume [save\|role]` | You | Saves your current session state or restores a previous one after a context clear. |
| `/pl-override-edit` | You | Opens your role's override file for guided editing with automatic conflict scanning against base instructions. |
| `/pl-update-purlin` | You | Updates the Purlin submodule to the latest version, refreshes artifacts, and resolves conflicts in locally modified files. |

#### Collaboration & Git

| Skill | Caller | What It Does |
|-------|--------|--------------|
| `/pl-remote-push` | You | Pushes your local collaboration branch to the remote. Blocks if the remote is ahead -- pull first. |
| `/pl-remote-pull` | You | Pulls the remote collaboration branch into your current branch. Shows a "What's Different?" digest after merge. |
| `/pl-whats-different` | You | Compares your current branch to the remote and generates a plain-English summary of what changed. Main checkout only. |

#### Testing & Diagnostics

| Skill | Caller | What It Does |
|-------|--------|--------------|
| `/pl-fixture` | Either | Reference for the test fixture system. Explains how to create, list, and manage immutable git tag fixtures. |
| `/pl-purlin-issue` | You | Generates a structured bug report for the Purlin framework itself. Auto-collects version, environment, and git state. |

---

### PM Skills

#### Specification & Design

| Skill | Caller | What It Does |
|-------|--------|--------------|
| `/pl-spec <topic>` | You | Creates a new feature spec (with probing questions) or refines an existing one. Shared with Architect. |
| `/pl-anchor <topic>` | You | Creates or updates a `design_*` or `policy_*` anchor node. PM cannot create `arch_*` nodes. Shared with Architect. |
| `/pl-design-ingest <source>` | You | Ingests a Figma URL, live web page, or local image into a feature's Visual Specification. Generates Token Map and brief.json. |
| `/pl-design-audit` | Either | Audits all design artifacts for integrity, staleness, and consistency with anchor nodes and Figma. Shared with Architect. |

---

### Architect Skills

#### Specification & Design

| Skill | Caller | What It Does |
|-------|--------|--------------|
| `/pl-spec <topic>` | You | Creates a new feature spec or refines an existing one. Runs gap analysis and probing questions. Shared with PM. |
| `/pl-anchor <topic>` | You | Creates or updates any anchor node (`arch_*`, `design_*`, or `policy_*`). Defines shared constraints for dependent features. |
| `/pl-tombstone <name>` | You | Retires a feature by creating a tombstone file that tells the Builder exactly what code to delete. |
| `/pl-spec-from-code` | You | Scans an existing codebase and reverse-engineers feature specs, anchor nodes, and companion files. For adopting Purlin on established projects. |
| `/pl-spec-code-audit` | You | Runs a bidirectional audit between specs and code. Architect fixes spec gaps; code gaps are escalated to the Builder. Shared with Builder. |

#### Release Process

| Skill | Caller | What It Does |
|-------|--------|--------------|
| `/pl-release-check` | You | Walks through the full release checklist step by step: zero-queue check, instruction audit, dependency integrity, docs, version notes, push. |
| `/pl-release-run [step]` | You | Runs a single release step by name without executing the full checklist sequence. |
| `/pl-release-step` | You | Creates, modifies, or deletes a release step definition in the checklist configuration. |

#### Framework Maintenance

| Skill | Caller | What It Does |
|-------|--------|--------------|
| `/pl-edit-base` | You | Modifies base instruction files. Only available inside the Purlin framework repository itself -- not in consumer projects. |

---

### Builder Skills

#### Implementation

| Skill | Caller | What It Does |
|-------|--------|--------------|
| `/pl-build [name]` | Either | Implements pending features or a specific feature. Follows the 4-step protocol: pre-flight, plan, implement, verify. |
| `/pl-delivery-plan` | Either | Creates or reviews a phased delivery plan when multiple features need implementation. Sizes phases and tracks progress. |
| `/pl-server` | Agent | Manages dev server processes (start, stop, port selection) during web test verification. Shared with QA. |

#### Testing

| Skill | Caller | What It Does |
|-------|--------|--------------|
| `/pl-unit-test [name]` | Agent | Runs unit tests against the 6-point quality rubric. Checks for anti-patterns. Produces `tests.json` results. |
| `/pl-web-test [name]` | Agent | Runs Playwright-based visual verification for features with web test metadata and Visual Specifications. Shared with QA. |
| `/pl-spec-code-audit` | You | Runs a bidirectional audit between specs and code. Builder fixes code gaps; spec gaps are escalated to the Architect. Shared with Architect. |

#### Communication

| Skill | Caller | What It Does |
|-------|--------|--------------|
| `/pl-infeasible <name>` | Agent | Records that a feature cannot be implemented as specified. Halts work and creates a CRITICAL escalation to the Architect. |
| `/pl-propose <topic>` | Agent | Suggests a spec change or new anchor node to the Architect. Records a `[SPEC_PROPOSAL]` in the companion file. |

---

### QA Skills

#### Verification

| Skill | Caller | What It Does |
|-------|--------|--------------|
| `/pl-verify [name]` | Either | Runs the full verification workflow: automated scenarios first (Phase A), then a manual checklist (Phase B). |
| `/pl-complete <name>` | Agent | Marks a verified feature as complete. Checks all gates: TESTING state, zero discoveries, delivery plan clearance. |
| `/pl-web-test [name]` | Agent | Runs Playwright visual verification during QA's Phase A visual smoke check. Shared with Builder. |
| `/pl-server` | Agent | Manages dev server processes during web test verification. Shared with Builder. |

#### Discoveries & Reporting

| Skill | Caller | What It Does |
|-------|--------|--------------|
| `/pl-discovery [name]` | Either | Records a structured finding (BUG, DISCOVERY, INTENT_DRIFT, or SPEC_DISPUTE) in the feature's discovery sidecar file. |
| `/pl-qa-report` | You | Generates a summary of all TESTING features, open discoveries, completion blockers, and effort estimates. |

#### Regression Testing

| Skill | Caller | What It Does |
|-------|--------|--------------|
| `/pl-regression-author` | Agent | Authors regression scenario JSON files for features that need automated test coverage. |
| `/pl-regression-run` | You | Composes a copy-pasteable command to run regression scenarios. You execute it in a separate terminal. |
| `/pl-regression-evaluate` | Agent | Reads regression test results, creates BUG discoveries for failures, and reports assertion tier distribution. |
