**Purlin command: shared (all roles) -- from main checkout only**

Generate a plain-English summary of what's different between local main and the remote collab branch.

## Steps

### 0. Main Branch Guard

Run: `git rev-parse --abbrev-ref HEAD`

If the result is not `main`, abort immediately:

```
This command is only valid from the main checkout.
Current branch: <branch>. Run /pl-whats-different from the project root (branch: main).
```

Do NOT proceed to Step 1.

### 1. Session Guard

Read `.purlin/runtime/active_remote_session`. If the file is absent or empty, abort:

```
No active remote session. Use the CDD dashboard to start or join a remote collab session.
```

Extract the session name from the file contents (single line, trimmed).

### 2. Load Config

Read `remote_collab.remote` from `.purlin/config.json`. Default to `"origin"` if the key is absent or the file does not exist.

Construct the target branch: `collab/<session>`.

### 3. Fetch and Sync State

```
git fetch <remote> collab/<session>
```

Run two range queries:

```
git log origin/collab/<session>..main --oneline
git log main..origin/collab/<session> --oneline
```

Determine state: SAME, AHEAD, BEHIND, or DIVERGED.

If SAME: print "Local main is in sync with collab/<session>. Nothing to summarize." Exit.

### 4. Run Generation Script

Execute the generation shell script:

```
tools/collab/generate_whats_different.sh <session>
```

This script runs the extraction tool and invokes the LLM to produce the digest. The output is written to `features/digests/whats-different.md`.

### 5. Display Result

Read and display the contents of `features/digests/whats-different.md`.

Note to the user: "This summary is also available via the 'What's Different?' button in the CDD dashboard."
