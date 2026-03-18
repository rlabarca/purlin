**Purlin command: Purlin framework Architect only — LOCAL TO THIS REPOSITORY**

> IMPORTANT: This command is local to the Purlin framework repository. It MUST NOT be distributed
> to consumer projects via init.sh. Consumer project agents MUST NEVER modify base instruction
> files — use the override layer at `.purlin/` instead.

---

If you are not operating as the Purlin Architect in the Purlin framework's own repository, respond:
"This command is for Purlin framework development only. Use `/pl-override-edit` to modify your
override file instead." and stop.

Before proceeding, confirm: no `purlin/` submodule directory exists at the project root (which would
indicate this is a consumer project, not the Purlin repo itself).

---

**Protocol:**

1. Confirm which base file to edit and what change is needed and why.
2. Read the target base file in full.
3. **Context Budget Classification:** Before writing any new content, classify each addition as either:
   - **Bright-line rule** (behavioral mandate, "MUST"/"MUST NOT", gate condition) -- belongs in the base file.
   - **Protocol detail** (multi-step workflow, format template, response processing pattern, state machine, routing table) -- belongs in the corresponding **skill file** (`.claude/commands/pl-*.md`), NOT in the base file. Skills are the self-contained playbooks agents load on demand.
   Apply this test: "If this content were missing from context, would the agent violate a rule on their next action?" If yes, it is a bright-line rule (base file). If it is a step-by-step procedure an agent follows during a specific workflow, it is protocol detail (skill file).
   **Examples of bright-line rules (base file):**
   - "Status tag MUST be a separate commit"
   - "Companion file edits do NOT reset status"
   - "Critic runs once after batch, not per-feature"
   - "NEVER write or modify project source code" (role boundary)
   **Examples of protocol detail (skill file):**
   - "Step 1: assemble checklist. Step 2: present with default-to-PASS semantics..."
   - "Discovery format: `### [TYPE] <title> (Discovered: YYYY-MM-DD)`..."
   - Response processing patterns (all pass / F3,F7 / help N / detail N / DISPUTE N)
   - Checklist presentation templates with examples
   - Per-feature implementation loops (pre-flight, implement, verify, tag)
   - Scope classification tables (full/targeted/cosmetic/dependency-only)
   - Phase sizing heuristics and delivery plan canonical format
   **Red flags -- content that should migrate to a skill:**
   - More than 5 sequential numbered steps describing a workflow
   - Format templates with placeholder syntax
   - Decision trees with if/then branching on runtime state
   - Tables mapping input patterns to output actions
4. **Skill-first routing:** If the change adds protocol detail, route it to the corresponding skill file (`.claude/commands/pl-*.md`). The base file gets only a 2-3 line stub with: (1) the trigger condition, (2) the skill to invoke, and (3) any bright-line constraint. Only use `instructions/references/*.md` for deep reference material that doesn't map to a single skill.
5. Run `/pl-override-edit --scan-only` on all `.purlin/` and `purlin-config-sample/` overrides
   that correspond to the file being changed. If proposed changes would break existing overrides,
   surface them before proceeding.
6. Apply additive-only principle where possible. For revisionary changes (not extensions), state
   explicitly and get explicit user confirmation.
7. Show the proposed edit and ask for user confirmation before writing.
8. After approval, apply and commit:
   `git commit -m "arch(instructions): <brief description of base file change>"`
9. Run `tools/cdd/status.sh` to regenerate the Critic report.
