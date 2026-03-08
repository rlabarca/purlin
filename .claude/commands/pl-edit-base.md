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
   - **Protocol detail** (format spec, state machine, routing table, multi-step procedure, architectural description) -- belongs in a reference file (`instructions/references/*.md`) with a 2-3 line stub in the base file.
   Apply this test: "If this content were missing from context, would the agent violate a rule on their next action?" If yes, it is a bright-line rule. If no, it is protocol detail.
4. **Reference file check:** If the change adds protocol detail, either:
   - Append to an existing reference file that covers the same domain, or
   - Create a new reference file with a clear trigger condition in the stub.
   The stub in the base file MUST include: (1) the trigger condition ("when X happens"), (2) the reference path, and (3) any bright-line constraint that cannot be deferred.
5. Run `/pl-override-edit --scan-only` on all `.purlin/` and `purlin-config-sample/` overrides
   that correspond to the file being changed. If proposed changes would break existing overrides,
   surface them before proceeding.
6. Apply additive-only principle where possible. For revisionary changes (not extensions), state
   explicitly and get explicit user confirmation.
7. Show the proposed edit and ask for user confirmation before writing.
8. After approval, apply and commit:
   `git commit -m "arch(instructions): <brief description of base file change>"`
9. Run `tools/cdd/status.sh` to regenerate the Critic report.
