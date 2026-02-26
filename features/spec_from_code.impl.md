# Implementation Notes: Spec From Code

*   **Command file location:** `.claude/commands/pl-spec-from-code.md` — a markdown command file that instructs the Architect agent through a 5-phase workflow (Phase 0: Initialization, Phase 1: Codebase Survey, Phase 2: Taxonomy Review, Phase 3: Feature Generation, Phase 4: Finalization).
*   **Role gating:** First two lines: `**Purlin command owner: Architect**` + redirect message. Matches the pattern used by `/pl-spec`, `/pl-anchor`, and other Architect-owned commands.
*   **State management:** Cross-session resume via `.purlin/cache/sfc_state.json`. State tracks current phase, status, directory choices, and `completed_categories` array for Phase 3 resume. State file is committed to git for durability.
*   **Context management:** Phase 1 delegates heavy file reading to 3 parallel Explore sub-agents (Structure, Domain, Comments & Docs). Phase 3 uses per-category Explore sub-agents for categories spanning >5 source files. All phases produce durable artifacts committed to git.
*   **Template references:** Feature files use `tools/feature_templates/_feature.md`; anchor nodes use `tools/feature_templates/_anchor.md`. Both templates are read at generation time, not hardcoded into the command.
*   **Commit discipline:** Phase 0-2 each have a single commit. Phase 3 commits anchor nodes individually and feature categories as batches. Phase 4 commits cleanup.
*   **Test approach:** Shell script (`tools/test_spec_from_code.sh`) verifies command file structure, role gating, phase coverage, template references, state file schema, and recommended next steps. 35 assertions covering all automated scenarios from the spec.
