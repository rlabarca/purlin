**Purlin command: role-scoped (Builder: own file only; QA: own file only; PM: own file only; Architect: any file)**

If you are the Builder: you may edit ONLY `.purlin/BUILDER_OVERRIDES.md`. Decline any other target and name its owner.
If you are QA: you may edit ONLY `.purlin/QA_OVERRIDES.md`. Decline any other target and name its owner.
If you are the PM: you may edit ONLY `.purlin/PM_OVERRIDES.md`. Decline any other target and name its owner.
If you are the Architect: you may edit any `*_OVERRIDES.md` file.

If no argument is provided, default to the calling role's own override file (Builder → BUILDER_OVERRIDES.md, QA → QA_OVERRIDES.md, PM → PM_OVERRIDES.md, Architect → ask).

**Mode:** If invoked with `--scan-only`, execute steps 1-3 only (conflict scan), then stop. No edits are made.

---

**Base/override file pairs:**
- `HOW_WE_WORK_OVERRIDES.md` ↔ `instructions/HOW_WE_WORK_BASE.md`
- `ARCHITECT_OVERRIDES.md` ↔ `instructions/ARCHITECT_BASE.md`
- `BUILDER_OVERRIDES.md` ↔ `instructions/BUILDER_BASE.md`
- `QA_OVERRIDES.md` ↔ `instructions/QA_BASE.md`
- `PM_OVERRIDES.md` ↔ `instructions/PM_BASE.md`

---

**Protocol:**

1. Read the target override file in full.
2. Read the corresponding base file (use the pairs above).
3. **Conflict scan:** For each rule or section in the override, classify against the base:
   - **[CONFLICT]** — directly contradicts or negates a base rule. Must be resolved before acting.
   - **[WARNING]** — addresses the same concern as a base rule but not clearly contradictory. Risk of confusion.
   - **[INFO]** — cosmetic overlap, redundant phrasing, or a reference to a renamed/renumbered base section.

   Present findings grouped: CONFLICT → WARNING → INFO. For each finding cite the override text, the base section, and a brief explanation. Conclude with a count summary.

   If no findings: "No conflicts or warnings detected. Override file is consistent with the base."

   **If in `--scan-only` mode, stop here.**

4. Apply the proposed change with these constraints:
   - Additive only — append, do not delete or restructure existing content.
   - No contradictions with the base file.
   - No code, scripts, JSON config, or executable content of any kind.
5. Show the proposed edit and ask for user confirmation before writing.
6. After approval, apply and commit: `git commit -m "override(<role>): <brief description>"`
