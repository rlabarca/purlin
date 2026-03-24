# Architect Agent Guide

A practical guide for using the Architect agent in Purlin.

---

## 1. Overview

The Architect is Purlin's specification and process manager. It designs feature specs, defines architectural constraints, validates the [dependency graph](spec-map-guide.md), and owns the release process. The Architect communicates entirely through feature files -- it never writes code or delegates work through chat.

The Architect agent:

- **Creates feature specifications** with Gherkin scenarios that define expected behavior.
- **Creates [anchor nodes](critic-and-cdd-guide.md)** that establish shared constraints (architecture, design, governance).
- **Validates specs** against the Critic's Spec Gate to ensure completeness.
- **Manages the release process** through a structured checklist.
- **Retires features** via the tombstone protocol when they are no longer needed.
- **Never writes code.** Not scripts, not tests, not config files. If code needs to change, the Architect writes a spec -- the Builder discovers it at startup and implements it.

The guiding philosophy: "Code is disposable." The specifications in `features/` are the single source of truth. If all code were deleted, a fresh Builder session could rebuild the entire application from the specs.

---

## 2. Getting Started

### Launching an Architect Session

From your project root, run:

```bash
./pl-run-architect.sh
```

This launches a Claude Code session with the Architect's instructions, tools, and permissions pre-loaded.

### What Happens at Startup

The Architect prints a command table, then checks its startup configuration:

- **Find Work enabled** (default): The Architect runs the Critic, reads the report, and presents a prioritized work plan. It asks for your approval before starting.
- **Find Work disabled**: The Architect prints `"find_work disabled -- awaiting instruction."` and waits for you to tell it what to do.
- **Auto Start enabled**: The Architect begins executing its work plan immediately after presenting it.

The startup work plan groups action items by feature and sorts them by priority (CRITICAL and HIGH first). You can approve the plan, adjust the order, or give it a completely different task.

---

## 3. The Zero-Code Mandate

This is the Architect's defining constraint. The Architect's write access is limited to:

- Feature specs: `features/*.md`
- Companion file bootstrap: `features/*.impl.md`
- Tombstones: `features/tombstones/*.md`
- Instructions and overrides: `instructions/*.md`, `.purlin/*.md`
- Prose docs: `README.md` and similar
- Process config: `.gitignore`, `.purlin/release/*.json`, `.purlin/config.json`

Everything else -- application code, scripts, tests, app-level config -- belongs to the Builder. If you ask the Architect to "fix this bug," it will write a spec that describes the correct behavior. The Builder picks it up from there.

---

## 4. Key Workflows

### Creating a Feature Spec

```
/pl-spec user-authentication
```

The Architect checks if a spec already exists. If not, it runs a structured probing protocol:

1. **Scope** -- What screens, data, and user goals are involved?
2. **Edge Cases** -- What happens on failure, loading, responsive layouts?
3. **Behavior** -- What are the interactions, state management, navigation?
4. **Design** -- Do Figma designs exist? What is the visual priority?
5. **Constraints** -- Performance budgets? Platform targets? Simplest useful version?

After gathering answers, the Architect drafts the spec with Gherkin scenarios (Given/When/Then), declares prerequisites to anchor nodes, and commits.

If a spec already exists, the Architect reads it, identifies gaps, and proposes targeted refinements. Specs are always edited in place -- never versioned as v2/v3 files.

### Creating an Anchor Node

```
/pl-anchor api-conventions
```

Anchor nodes define constraints that multiple features share. There are three types:

| Prefix | Domain | Who Cares |
|--------|--------|-----------|
| `arch_*.md` | Technical architecture, code patterns, API contracts | Developers |
| `design_*.md` | Visual language, typography, spacing, accessibility | Designers |
| `policy_*.md` | Security baselines, compliance, process rules | Compliance officers |

When you create or edit an anchor node, all features that depend on it reset to TODO status. This cascade is intentional -- it triggers re-validation across every affected feature.

### Retiring a Feature

```
/pl-tombstone old-api
```

When a feature is no longer needed, the Architect creates a tombstone file in `features/tombstones/` that tells the Builder exactly what to delete:

- Which files and directories to remove.
- Which dependencies to check.
- Why the feature was retired.

The tombstone appears as a Builder action item. After the Builder deletes the code and the tombstone, the feature clears from the dashboard.

### Running a Release

```
/pl-release-check
```

This walks through the release checklist step by step:

1. **Zero-Queue Check** -- Every feature must have Architect=DONE, Builder=DONE, QA=CLEAN or N/A.
2. **Instruction Audit** -- Override files are consistent with base instructions.
3. **Dependency Integrity** -- The feature graph is acyclic with no broken links.
4. **Documentation Consistency** -- README and docs match the current feature set.
5. **Version Notes** -- Record the release version and notes in `README.md`.
6. **Push** -- Push commits and tags to the remote.

Each step presents its status and asks for confirmation before proceeding.

### Responding to Critic Action Items

When you run `/pl-status`, the Critic generates action items. Common ones:

- **Spec Gate FAIL** -- The spec is missing required sections, has malformed scenarios, or lacks prerequisite declarations. Fix the spec.
- **Unacknowledged [DEVIATION]** -- The Builder diverged from the spec and documented why in a companion file. Read the rationale and add "Acknowledged" to the entry.
- **[SPEC_DISPUTE]** -- QA or the Builder disagrees with a scenario. Either update the spec or confirm it is correct. Route design-related disputes to the PM.
- **Untracked files** -- Files in the working directory that are not git-tracked. Add generated artifacts to `.gitignore`; commit Architect-owned files.
- **[INFEASIBLE]** -- The Builder says the feature cannot be implemented as specified. Revise the spec to make it feasible.

### Spec-Code Audit

```
/pl-spec-code-audit
```

This performs a bidirectional consistency check between specs and code. The Architect fixes spec-side gaps (missing scenarios, undeclared prerequisites) and escalates code-side gaps to the Builder via companion file entries.

### Reverse-Engineering Specs from Code

```
/pl-spec-from-code
```

For existing codebases without specs, this command scans the project and auto-generates feature specs, anchor nodes, and companion files. Useful when adopting Purlin on an established project.

---

## 5. Anchor Node Design

### When to Create One

Create an anchor node when two or more features need the same constraint. Ask yourself: "Who would object if this constraint were violated?"

- A developer reviewing code quality --> `arch_*`
- A designer reviewing the UI --> `design_*`
- A compliance officer or security auditor --> `policy_*`

### What Goes in an Anchor Node

Each anchor defines:

- **Purpose** -- What invariants it enforces and why.
- **Invariants** -- The specific rules that dependent features must follow.
- **FORBIDDEN patterns** (optional) -- Grepable code patterns that the Critic checks for violations.

Anchor nodes do not have scenarios. They are constraint definitions, not implementable features.

### The Cascade Effect

When you edit an anchor node, every feature that declares it as a prerequisite resets to TODO. This triggers:

1. The Critic flags the dependent features as needing re-validation.
2. The Builder re-implements any features where the constraint change affects behavior.
3. QA re-verifies features that were previously complete.

This is by design. It ensures that constraint changes propagate through the entire system.

---

## 6. Working with Companion Files

Companion files (`features/<name>.impl.md`) store implementation knowledge alongside specs. The Builder creates them during implementation; the Architect reads them to understand decisions.

**When to read them:**
- Before refining a spec -- understand what the Builder learned.
- When processing `[DEVIATION]` tags -- these represent deliberate design divergences.
- When processing `[DISCOVERY]` tags -- these represent gaps the Builder found.

**Builder decision tags you will encounter:**

| Tag | Severity | What It Means |
|-----|----------|---------------|
| `[CLARIFICATION]` | INFO | Builder interpreted ambiguous spec language |
| `[AUTONOMOUS]` | WARN | Spec was silent; Builder filled the gap |
| `[DEVIATION]` | HIGH | Builder intentionally diverged from spec |
| `[DISCOVERY]` | HIGH | Builder found an unstated requirement |
| `[INFEASIBLE]` | CRITICAL | Builder says the feature cannot be built as specified |
| `[SPEC_PROPOSAL]` | HIGH | Builder proposes a new anchor node or spec change |

HIGH and CRITICAL entries block completion until you acknowledge them.

---

## 7. Day-to-Day Tips

### Finding Where a Topic Lives

```
/pl-find error-handling
```

Searches across all specs to find where a topic is discussed. Useful before creating a new spec to avoid duplicating requirements.

### Checking Project Status

```
/pl-status
```

Runs the Critic and shows the current state of all features with role-specific action items. This is your primary orientation command.

### Commit Discipline

Commit immediately after each discrete change. Do not batch work until session end. After committing changes to specs or anchor nodes, run `/pl-status` to regenerate the Critic report for the next agent.

### Handling Design vs. Architecture Disputes

When a SPEC_DISPUTE involves visual design, Token Maps, or Figma artifacts, route it to the PM by setting `Action Required: PM` in the discovery sidecar entry. The Architect resolves behavioral and architectural disputes directly.

### Override Files

```
/pl-override-edit
```

Edit `.purlin/ARCHITECT_OVERRIDES.md` to add project-specific rules. This file is concatenated with the base instructions at session start. Use it for tech stack constraints, domain conventions, and team-specific mandates.

---

## 8. Command Reference

| Command | Description |
|---------|-------------|
| `/pl-spec <topic>` | Create or refine a feature spec. Runs probing questions for new specs. |
| `/pl-anchor <topic>` | Create or update an anchor node (arch\_, design\_, or policy\_). |
| `/pl-tombstone <name>` | Retire a feature and create a deletion guide for the Builder. |
| `/pl-spec-code-audit` | Bidirectional spec-code consistency audit. |
| `/pl-spec-from-code` | Reverse-engineer specs from an existing codebase. |
| `/pl-release-check` | Execute the release checklist step by step. |
| `/pl-release-run <step>` | Run a single release step by name. |
| `/pl-release-step` | Create, modify, or delete a release step definition. |
| `/pl-status` | Check CDD status and Critic action items. |
| `/pl-find <topic>` | Search specs for where a topic is discussed. |
| `/pl-fixture` | Test fixture convention and workflow reference. |
| `/pl-cdd` | Start, stop, or restart the [CDD Dashboard](status-grid-guide.md). |
| `/pl-agent-config` | View or modify agent model and startup settings. |
| `/pl-override-edit` | Edit ARCHITECT_OVERRIDES.md with conflict scanning. |
| `/pl-whats-different` | Compare branches (main checkout only). |
| `/pl-remote-push` | Push [collaboration branch](branch-collaboration-guide.md) to remote. |
| `/pl-remote-pull` | Pull remote into current branch. |
| `/pl-help` | Display the full command list. |
| `/pl-resume [save\|role]` | Save or restore session state. |
| `/pl-update-purlin` | Update the Purlin submodule with conflict handling. |
