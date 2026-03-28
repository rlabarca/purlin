---
name: whats-different
description: Available to all agents and modes
---

**Purlin command: shared (all roles) -- from main checkout only**
**Purlin mode: shared**

Available to all agents and modes.

## Path Resolution

> Scripts at `${CLAUDE_PLUGIN_ROOT}/scripts/`. References at `${CLAUDE_PLUGIN_ROOT}/references/`.
> **Companion files:** See `${CLAUDE_PLUGIN_ROOT}/references/active_deviations.md` for deviation format and PM review protocol.

---

Generate a plain-English summary of what's different between the current HEAD and the remote collab branch (`origin/<branch>`). When a Purlin mode is active, produces a role-specific briefing followed by the standard digest.

## Steps

### 0. Main Branch Guard

Run: `git rev-parse --abbrev-ref HEAD`

If the result is not `main`, abort immediately:

```
This command is only valid from the main checkout.
Current branch: <branch>. Run purlin:whats-different from the project root (branch: main).
```

Do NOT proceed to Step 1.

### 1. Branch Guard

Read `.purlin/runtime/active_branch`. If the file is absent or empty, abort:

```
No active collaboration branch. Use purlin:remote branch create <name> to start one, or purlin:remote branch join <name> to join an existing one.
```

Extract the branch name from the file contents (single line, trimmed).

### 2. Load Config

Read remote name from `.purlin/config.json`: check `branch_collab.remote` first, fall back to `remote_collab.remote`, default to `"origin"` if both absent.

Construct the target branch: `<session>`.

### 3. Fetch and Sync State

```
git fetch <remote> <session>
```

Run two range queries:

```
git log origin/<session>..HEAD --oneline
git log HEAD..origin/<session> --oneline
```

Determine state: SAME, AHEAD, BEHIND, or DIVERGED.

If SAME: print "HEAD is in sync with <session>. Nothing to summarize." Exit.

### 4. Run Generation Script

Execute the generation shell script:

```
${CLAUDE_PLUGIN_ROOT}/scripts/collab/generate_whats_different.sh <session> [--role <mode>]
```

- If the agent has an active Purlin mode (PM, Engineer, or QA), pass `--role <mode>` to produce a role-specific briefing prepended to the standard digest.
- If no mode is active (open mode), run without `--role` (standard digest only).

This script runs the extraction tool and invokes the LLM to produce the digest. The output is written to `features/digests/whats-different.md`.

### 5. Display Result

Read and display the contents of `features/digests/whats-different.md`.

When a role briefing is present, the output has two sections separated by a horizontal rule:
1. **Role briefing** — plain-language summary of what matters to this mode, with numbered IDs on each item.
2. **Standard digest** — full file-level digest (Spec Changes / Code Changes / Purlin Changes).

### 6. ID Drill-Down (Conversational)

After displaying the briefing, be prepared for the user to reply with a numeric ID (e.g., "3", "#3", "tell me about 3"). When this happens:

1. Identify the corresponding item from the most recent briefing.
2. Read the relevant source files (feature spec, companion file, discovery sidecar, git diff).
3. Provide a detailed explanation: what the original state was, what changed, the full context, and recommended next steps.

No script or endpoint is needed — this is conversational. The IDs make it easy to request detail without typing file paths.
