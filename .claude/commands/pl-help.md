**Purlin command: shared (all roles)**

Re-display the command vocabulary table for the current agent role.

No arguments, no side effects. Output only.

## Steps

### 1. Role Detection

Detect the current agent role from system prompt markers:
- "Role Definition: The Architect" -> `architect`
- "Role Definition: The Builder" -> `builder`
- "Role Definition: The QA" -> `qa`

If no marker is found, ask the user which role they are.

### 2. Branch Detection

Run: `git rev-parse --abbrev-ref HEAD`

Determine the variant to print:
- If `.purlin/runtime/active_branch` exists and is non-empty, use the **Branch Collaboration Variant**.
- Otherwise, use the **Main Branch Variant**.

### 3. Print Command Table

Read `instructions/references/{role}_commands.md` (where `{role}` is `architect`, `builder`, or `qa`).

Print the appropriate variant verbatim.
