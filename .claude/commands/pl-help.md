**Purlin command: shared (all roles)**

Display all Purlin help: slash commands for the current role AND user-facing CLI scripts with their flags. Invoke this when the user asks "how do I run...", "what flags does... accept", or needs help with any Purlin command or script.

No side effects. Output only.

## Steps

### 1. Role Detection

Detect the current agent role from system prompt markers:
- "Role Definition: The Architect" -> `architect`
- "Role Definition: The Builder" -> `builder`
- "Role Definition: The QA" -> `qa`
- "Role Definition: The PM" -> `pm`

If no marker is found, ask the user which role they are.

### 2. Branch Detection

Run: `git rev-parse --abbrev-ref HEAD`

Determine the variant to print:
- If `.purlin/runtime/active_branch` exists and is non-empty, use the **Branch Collaboration Variant**.
- Otherwise, use the **Main Branch Variant**.

### 3. Print Command Table

Read `instructions/references/{role}_commands.md` (where `{role}` is `architect`, `builder`, `qa`, or `pm`).

Print the appropriate variant verbatim.

### 4. Discover CLI Scripts

1. Determine project root: use `$PURLIN_PROJECT_ROOT` if set, else `git rev-parse --show-toplevel`.
2. Glob `pl-*.sh` in the project root.
3. For each script found, run: `timeout 3 bash "<script>" --help 2>/dev/null`
4. If the command exits 0 and produces non-empty output, collect that output.
5. If the command exits non-zero or produces no output, record: `(no help -- run pl-init.sh to refresh)`

### 5. Print CLI Scripts Section

After the slash command table, print:

```
---

## CLI Scripts (run from terminal)
```

Then for each discovered script, print its collected help output (or the refresh note), separated by blank lines.

If no `pl-*.sh` scripts were found in the project root, print: `(no CLI scripts found in project root)`
