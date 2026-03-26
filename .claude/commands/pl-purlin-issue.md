**Purlin command: shared (all roles)**
**Purlin mode: shared**

Available to all agents and modes.

Generate a structured, copy-paste-ready bug report for the Purlin framework. The output is designed to be pasted directly into a Purlin Engineer session as a debugging task prompt.

This command is for reporting issues with the Purlin framework tooling, not for logging project-level bugs (use `/pl-discovery` for that).

## Steps

### 1. Collect Issue Context

If `$ARGUMENTS` is non-empty, use it as the issue description. Otherwise, ask: **"Describe the Purlin framework issue you encountered."**

Then gather the debugging essentials. If any of these are visible in the current conversation, extract them directly and confirm with the user. Otherwise, ask:

1. **Command/skill**: "What command or skill were you running?" (e.g., `/pl-build notifications`, `pl-run.sh --auto-build`)
2. **Error output**: "Paste or describe the error output (traceback, unexpected result, or wrong behavior)." If the error is visible in conversation context, extract it and ask: "Is this the error? [show extracted text]"
3. **Expected behavior**: "What should have happened instead?"

### 2. Gather Automatic Context

Collect all of the following without user input:

**Purlin version:**
1. Check if `.purlin/.upstream_sha` exists at project root (`git rev-parse --show-toplevel`).
2. **Consumer project** (`.upstream_sha` exists):
   - Purlin SHA: `cat <project_root>/.purlin/.upstream_sha`
   - Purlin remote: `git -C <tools_root>/.. remote get-url origin`, fallback "unknown"
   - Version tag: `git -C <tools_root>/.. describe --tags --abbrev=0 HEAD`, fallback "untagged"
   - Deployment: `consumer`
   - Consumer remote: `git remote get-url origin`, fallback "unknown"
   - Consumer branch: `git rev-parse --abbrev-ref HEAD`
   - Consumer HEAD: `git rev-parse --short HEAD`
3. **Standalone** (no `.upstream_sha`):
   - Purlin SHA: `git rev-parse HEAD`
   - Purlin remote: `git remote get-url origin`, fallback "unknown"
   - Version tag: `git describe --tags --abbrev=0 HEAD`, fallback "untagged"
   - Deployment: `standalone`

**Environment:**
- Date: today's date
- OS: `uname -s -r`
- Mode: current Purlin mode from session state (Engineer, PM, QA, or "none")
- `tools_root`: from resolved config

**Config state:**
- Read `.purlin/config.local.json` if it exists, otherwise `.purlin/config.json`
- Include only the `agents.purlin` section (not the full file)

**Relevant files:**
- If the failing command is a `/pl-*` skill, note the skill path: `.claude/commands/pl-<name>.md`
- If a feature was being worked on, note the feature spec path
- If a specific tool/script failed, note its path

**Git state:**
- `git log --oneline -5`
- `git status --short` (first 20 lines)

**Conversation context:**
- Compose a 2-3 sentence summary of what led to the issue: what was being attempted, what mode was active, what sequence of actions preceded the failure. Draw from conversation memory.

### 3. Compose and Present Bug Report

Assemble the report with the Reproduction Block first (what the receiving agent needs to start debugging) and the Environment Snapshot second (reference context).

```
-------- PURLIN ISSUE REPORT (COPY THIS) ---------

## Reproduction

**Command:** <the command/skill that failed>

**Error Output:**
```
<error traceback, unexpected output, or description of wrong behavior>
```

**Expected:** <what should have happened>

**Steps to Reproduce:**
1. <step 1 — include mode, branch, and any setup>
2. <step 2>
3. <step 3>

**Relevant Files:**
- <file path 1> — <why it's relevant>
- <file path 2> — <why it's relevant>

**Context:** <agent-composed summary of what led to the issue>

---

## Environment

| Field | Value |
|-------|-------|
| Date | <date> |
| Mode | <Engineer / PM / QA / none> |
| Branch | <branch> |
| Purlin SHA | <full-sha> |
| Purlin Version | <version-tag> |
| Purlin Remote | <remote-url> |
| Deployment | <consumer / standalone> |
| OS | <os-info> |
| Consumer Project | <consumer-remote or "N/A (standalone)"> |
| Consumer HEAD | <short-sha or "N/A"> |

**Agent Config (`agents.purlin`):**
```json
<agents.purlin section from resolved config>
```

**Recent Git Activity:**
```
<git log --oneline -5>
```

**Working Tree:**
```
<git status --short, or "clean">
```

-------- END PURLIN ISSUE REPORT ---------
```

### 4. User Instructions

After the closing divider, print:

> Copy the text between the dividers and paste it into a Purlin Engineer session. The reproduction block gives the agent everything it needs to find and fix the issue.
