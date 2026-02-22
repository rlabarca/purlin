**Purlin command owner: Builder**

If you are not operating as the Purlin Builder, respond: "This is a Builder command. Ask your Builder agent to run /pl-delivery-plan instead." and stop.

---

If a delivery plan already exists at `.agentic_devops/cache/delivery_plan.md`:

- Read the plan and display the current phase, completed phases, and remaining phases.
- List features in the current phase with their implementation status (TODO / TESTING / COMPLETE).
- Offer to adjust the plan: collapse remaining phases, re-split, or add new features discovered since the plan was created.

If no delivery plan exists:

- Run `tools/cdd/status.sh` to get current feature status.
- Assess scope: apply the phasing heuristics from `instructions/BUILDER_BASE.md` Section 2.2.1.
- Propose a phase breakdown grouped by dependency order, logical cohesion, and testability gates.
- After user confirmation, create the delivery plan at `.agentic_devops/cache/delivery_plan.md` using the canonical format and commit it.
