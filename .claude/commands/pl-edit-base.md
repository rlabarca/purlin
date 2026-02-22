**Purlin command: Purlin framework Architect only — LOCAL TO THIS REPOSITORY**

> IMPORTANT: This command is local to the Purlin framework repository. It MUST NOT be distributed
> to consumer projects via bootstrap.sh or sync_upstream.sh. Consumer project agents MUST NEVER
> modify base instruction files — use the override layer at `.purlin/` instead.

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
3. Run `/pl-override-conflicts` on all `.purlin/` and `purlin-config-sample/` overrides
   that correspond to the file being changed. If proposed changes would break existing overrides,
   surface them before proceeding.
4. Apply additive-only principle where possible. For revisionary changes (not extensions), state
   explicitly and get explicit user confirmation.
5. Show the proposed edit and ask for user confirmation before writing.
6. After approval, apply and commit:
   `git commit -m "arch(instructions): <brief description of base file change>"`
7. Run `tools/cdd/status.sh` to regenerate the Critic report.
