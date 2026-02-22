**Purlin command: role-scoped (Builder: own file only; QA: own file only; Architect: any file)**

If you are the Builder: you may edit ONLY `.agentic_devops/BUILDER_OVERRIDES.md`. Decline any other target and name its owner.
If you are QA: you may edit ONLY `.agentic_devops/QA_OVERRIDES.md`. Decline any other target and name its owner.
If you are the Architect: you may edit any `*_OVERRIDES.md` file.

If no argument is provided, default to the calling role's own override file (Builder → BUILDER_OVERRIDES.md, QA → QA_OVERRIDES.md, Architect → ask).

---

**Protocol:**

1. Read the target override file in full.
2. Read the corresponding base file (`BUILDER_OVERRIDES.md` ↔ `BUILDER_BASE.md`, etc.).
3. Run the `/pl-override-conflicts` analysis on the current override content. Present findings before proceeding.
4. Apply the proposed change with these constraints:
   - Additive only — append, do not delete or restructure existing content.
   - No contradictions with the base file.
   - No code, scripts, JSON config, or executable content of any kind.
5. Show the proposed edit and ask for user confirmation before writing.
6. After approval, apply and commit: `git commit -m "override(<role>): <brief description>"`
