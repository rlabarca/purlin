**Purlin mode: shared**

Generate a structured, copy-paste-ready issue report for the Purlin framework itself. Collects Purlin version info, environment context, and workflow state. The report can be pasted directly into a Purlin Architect session for triage.

This command is for reporting issues with the Purlin framework tooling, not for logging project-level bugs (use `/pl-discovery` for that).

## Steps

### 1. Collect Issue Description

If `$ARGUMENTS` is non-empty, use it as the issue description.

Otherwise, ask the user: **"Describe the Purlin framework issue you encountered."** Do not proceed until a description is provided.

### 2. Detect Purlin Version Info

Determine deployment mode and collect version information:

1. Run `git rev-parse --show-toplevel` to get project root.
2. Check if `.purlin/.upstream_sha` exists at project root.

**If `.purlin/.upstream_sha` exists (consumer project):**
- Purlin SHA: `cat <project_root>/.purlin/.upstream_sha`
- Purlin remote: `git -C <tools_root>/.. remote get-url origin`, fallback to reading the `# Repo:` line from `pl-init.sh` in project root, fallback to "unknown"
- Version tag: `git -C <tools_root>/.. describe --tags --abbrev=0 HEAD`, fallback "untagged"
- Deployment: `consumer`
- Consumer project remote: `git remote get-url origin`, fallback "unknown"
- Consumer branch: `git rev-parse --abbrev-ref HEAD`
- Consumer HEAD: `git rev-parse --short HEAD`

**If `.purlin/.upstream_sha` does NOT exist (standalone / inside Purlin repo):**
- Purlin SHA: `git rev-parse HEAD`
- Purlin remote: `git remote get-url origin`, fallback "unknown"
- Version tag: `git describe --tags --abbrev=0 HEAD`, fallback "untagged"
- Deployment: `standalone`
- No consumer project fields (omit from report)

### 3. Gather Environment Context

- Date: today's date from system context
- OS: `uname -s -r`
- Agent role: detect from system prompt markers:
  - "Role Definition: The Architect" -> `Architect`
  - "Role Definition: The Builder" -> `Builder`
  - "Role Definition: The QA" -> `QA`
  - "Role Definition: The PM" -> `PM`
  - If no marker found -> `unknown`
- `tools_root`: read from `.purlin/config.json` (default `"tools"`)

### 4. Gather Workflow Context

- Recent git history: `git log --oneline -5`
- Working tree state: `git status --short` (first 20 lines max)
- If `CRITIC_REPORT.md` exists at project root, extract any CRITICAL or HIGH priority items and summarize them briefly (do not dump the entire file).
- Compose a brief summary (2-5 sentences) of the conversation context that led to the issue -- what the user was trying to do, what agent was running, and what went wrong. Draw this from your own conversation memory, not a tool.

### 5. Compose and Present Bug Report

Assemble all collected information and present between clear dividers. Use the branch from the deployment where the user is working (consumer branch for consumer projects, current branch for standalone).

```
-------- PURLIN ISSUE REPORT (COPY THIS) ---------

## Purlin Issue Report

| Field | Value |
|-------|-------|
| Date | <date> |
| Purlin SHA | <full-sha> |
| Purlin Version | <version-tag> |
| Purlin Remote | <remote-url> |
| Deployment | <consumer / standalone> |
| OS | <os-info> |
| Agent Role | <role> |
| Branch | <branch> |
| Consumer Project | <consumer-remote or "N/A (standalone)"> |
| Consumer HEAD | <short-sha or "N/A"> |

### Issue Description

<user's description>

### Context

<agent-composed summary of what led to the issue>

### Recent Git Activity

```
<git log --oneline -5 output>
```

### Working Tree State

```
<git status --short output, or "clean">
```

### Active Critic Issues

<CRITICAL/HIGH items summary, or "None">

-------- END PURLIN ISSUE REPORT ---------
```

### 6. User Instructions

After the closing divider, print:

> Copy the text between the dividers above and send it to the Purlin developer, or post it to the project's issue tracker. The developer can paste this directly into a Purlin Architect session for triage.
