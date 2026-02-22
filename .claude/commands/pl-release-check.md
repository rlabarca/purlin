**Purlin command owner: Architect**

If you are not operating as the Purlin Architect, respond: "This is an Architect command. Ask your Architect agent to run /pl-release-check instead." and stop.

---

Execute the CDD release checklist step by step:

1. Run `tools/cdd/status.sh` to confirm current project state.
2. Verify the Zero-Queue Mandate: every feature must have `architect: "DONE"`, `builder: "DONE"`, and `qa` as `"CLEAN"` or `"N/A"`. List any blocking features.
3. Check the dependency graph for cycles via `.purlin/cache/dependency_graph.json`.
4. Verify the active release spec (`features/release_*.md`) is marked `[Complete]`.
5. Consult `.purlin/release/config.json` for the project-specific release step sequence and work through each enabled step in order.

Present each step's status and ask for confirmation before proceeding to the next.
