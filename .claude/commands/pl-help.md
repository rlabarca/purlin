**Purlin mode: shared**

Display the Purlin slash command table for the current role and list available CLI launcher scripts. Invoke this when the user asks "how do I run...", "what commands are available", or needs help with any Purlin command.

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

### 4. List CLI Scripts

1. Determine project root: use `$PURLIN_PROJECT_ROOT` if set, else `git rev-parse --show-toplevel`.
2. Glob `pl-*.sh` in the project root.
3. After the slash command table, print:

```
---

## CLI Scripts (run from terminal)
```

4. List each discovered script by filename (e.g., `pl-run-architect.sh`, `pl-run-builder.sh`). Do NOT attempt to run the scripts or fetch `--help` output.
5. If no `pl-*.sh` scripts were found in the project root, print: `(no CLI scripts found in project root)`
