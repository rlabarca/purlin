**Purlin command: shared (all roles)**

Compare an override file against its corresponding base file to surface contradictions, stale references, and redundant rules. Read-only — no files are modified.

If no argument is provided, default to the calling role's own override file.

**Base/override file pairs:**
- `HOW_WE_WORK_OVERRIDES.md` ↔ `instructions/HOW_WE_WORK_BASE.md`
- `ARCHITECT_OVERRIDES.md` ↔ `instructions/ARCHITECT_BASE.md`
- `BUILDER_OVERRIDES.md` ↔ `instructions/BUILDER_BASE.md`
- `QA_OVERRIDES.md` ↔ `instructions/QA_BASE.md`

**Protocol:**
1. Read both files in full.
2. For each rule or section in the override, classify against the base:
   - **[CONFLICT]** — directly contradicts or negates a base rule. Must be resolved before acting.
   - **[WARNING]** — addresses the same concern as a base rule but not clearly contradictory. Risk of confusion.
   - **[INFO]** — cosmetic overlap, redundant phrasing, or a reference to a renamed/renumbered base section.
3. Present findings grouped: CONFLICT → WARNING → INFO. For each finding cite the override text, the base section, and a brief explanation.
4. Conclude with a count summary.
5. If no findings: "No conflicts or warnings detected. Override file is consistent with the base."
