# Reporting Purlin Issues

## Overview

When you encounter a bug or unexpected behavior in the Purlin framework
itself -- not in your project's application code -- use `/pl-purlin-issue`
to generate a structured bug report. The command collects version info,
environment context, and workflow state automatically, so you do not need
to gather diagnostics manually.

This guide explains when to use it, what it produces, and where to send
the report.

---

## When to Use This

Use `/pl-purlin-issue` when the problem is with Purlin's tooling:

- The [Critic](critic-and-cdd-guide.md) produces incorrect action items or crashes.
- The [CDD Dashboard](status-grid-guide.md) shows wrong data or fails to start.
- A slash command (`/pl-build`, `/pl-verify`, etc.) behaves incorrectly.
- The init script fails or produces a broken scaffold.
- Agent startup hangs, crashes, or loads the wrong instructions.
- A release step does not work as documented.

**Do not use it for project-level bugs.** If the Builder implemented a
feature incorrectly or QA found a behavioral issue in your application,
use `/pl-discovery` instead. That records the finding in your project's
discovery sidecar files and routes it to the appropriate role.

| Situation | Command |
|-----------|---------|
| Purlin tool is broken | `/pl-purlin-issue` |
| Application behavior is wrong | `/pl-discovery` |

---

## How to Use It

### From Any Agent Session

Run the command with a description of the problem:

```
/pl-purlin-issue The Critic reports Spec Gate FAIL for a feature that has all required sections
```

Or run it without arguments and the agent will ask you to describe the
issue:

```
/pl-purlin-issue
```

The command works from any agent role -- Architect, Builder, QA, or PM.

### What It Collects

The command automatically gathers:

- **Purlin version** -- SHA, version tag, and remote URL of the Purlin
  submodule (or standalone repo).
- **Deployment mode** -- Whether you are running Purlin as a submodule in a
  consumer project or in the Purlin repo itself.
- **Environment** -- OS, agent role, current branch, tools_root path.
- **Recent git history** -- Last 5 commits for context.
- **Working tree state** -- Uncommitted changes that might be relevant.
- **Active Critic issues** -- Any CRITICAL or HIGH priority items from the
  Critic report.
- **Conversation context** -- A brief summary of what you were doing when
  the issue occurred.

### What It Produces

The command outputs a formatted report between clear dividers:

```
-------- PURLIN ISSUE REPORT (COPY THIS) ---------

## Purlin Issue Report

| Field | Value |
|-------|-------|
| Date | 2026-03-23 |
| Purlin SHA | a1b2c3d4e5f6... |
| Purlin Version | v2.1.0 |
| Deployment | consumer |
| OS | Darwin 25.3.0 |
| Agent Role | Builder |
| Branch | main |
| ... | ... |

### Issue Description

The Critic reports Spec Gate FAIL for a feature that has all
required sections present and correctly formatted.

### Context

The Builder was running startup orientation when the Critic
flagged feature_x.md with a Spec Gate FAIL...

### Recent Git Activity

(last 5 commits)

### Working Tree State

(uncommitted changes or "clean")

### Active Critic Issues

(CRITICAL/HIGH items or "None")

-------- END PURLIN ISSUE REPORT ---------
```

---

## Where to Send the Report

Copy the text between the dividers and do one of the following:

1. **Paste it into a Purlin Architect session.** If you have access to the
   Purlin framework repository, start an Architect session there and paste
   the report. The Architect can triage and create a fix.

2. **Post it to the issue tracker.** File an issue at the Purlin project's
   repository with the report as the issue body.

3. **Send it to the Purlin developer.** If you are on a team with a
   framework maintainer, send the report directly. The structured format
   makes it easy to reproduce and diagnose.

The report is self-contained. The recipient does not need to ask follow-up
questions about your environment or version -- it is all in the table.

---

## Tips

- **Run it as soon as you hit the issue.** The command captures your current
  git state and conversation context. If you wait, commits or context
  changes may obscure the problem.
- **Include reproduction steps in your description.** The command collects
  environment data, but only you know the exact sequence of actions that
  triggered the bug.
- **Check for known issues first.** Run `/pl-status` to see if [the Critic](critic-and-cdd-guide.md)
  has already flagged something relevant. The issue may be a known gap
  rather than a bug.
