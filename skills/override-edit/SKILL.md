---
name: override-edit
description: Available to all agents and modes
---

**Purlin command: shared (all roles, all sections)**
**Purlin mode: shared**

Available to all agents and modes.

Any active mode (Engineer, PM, QA) may edit any section of `.purlin/PURLIN_OVERRIDES.md`. There is no per-section role restriction.

## Path Resolution

> Scripts at `${CLAUDE_PLUGIN_ROOT}/scripts/`. References at `${CLAUDE_PLUGIN_ROOT}/references/`.
> **Output standards:** See `${CLAUDE_PLUGIN_ROOT}/references/output_standards.md`.

**Mode:** If invoked with `--scan-only`, execute steps 1-3 only (conflict scan), then stop. No edits are made.

---

**Base/override file pair:**
- `PURLIN_OVERRIDES.md` ↔ `instructions/PURLIN_BASE.md`

---

**Protocol:**

1. Read the target override file in full.
2. Read the corresponding base file (use the pairs above).
3. **Conflict and consistency scan:** For each rule or section in the override, classify against the base:
   - **[CONFLICT]** — directly contradicts or negates a base rule. Must be resolved before acting.
   - **[WARNING]** — addresses the same concern as a base rule but not clearly contradictory. Risk of confusion. Also: terminology mismatches where the override uses a term the base has renamed or deprecated.
   - **[INFO]** — cosmetic overlap, redundant phrasing, stale path references (file paths in the override that no longer resolve to existing files or sections), or a reference to a renamed/renumbered base section.

   Additionally check:
   - **Stale path references:** Verify that file paths mentioned in the override actually exist on disk. Report missing paths as [INFO].
   - **Terminology mismatches:** Compare key terms against the base file's vocabulary. Flag cases where the override uses a different name for the same concept as [WARNING].

   Present findings grouped: CONFLICT → WARNING → INFO. For each finding cite the override text, the base section, and a brief explanation. Conclude with a count summary.

   If no findings: "No conflicts or warnings detected. Override file is consistent with the base."

   **If in `--scan-only` mode, stop here.**

4. **Content guidance:** Override files carry two types of content:
   *   **Project-specific bright-line rules** -- tech stack constraints, deployment restrictions, submodule prohibitions, domain-specific mandates.
   *   **Domain context** -- project architecture, environment details, team conventions the agent needs always-on.

   Override files do NOT carry: workflow procedures, multi-step protocols, format templates, or response processing patterns. Those belong in skill files (`.claude/commands/pl-*.md`). If the proposed content is a step-by-step procedure, advise putting it in a skill instead.

5. Apply the proposed change with these constraints:
   - Additive only -- append, do not delete or restructure existing content.
   - No contradictions with the base file.
   - No code, scripts, JSON config, or executable content of any kind.
6. Show the proposed edit and ask for user confirmation before writing.
7. After approval, apply and commit: `git commit -m "override(<role>): <brief description>"`
