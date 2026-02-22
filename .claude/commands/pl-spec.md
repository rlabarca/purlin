**Purlin command owner: Architect**

If you are not operating as the Purlin Architect, respond: "This is an Architect command. Ask your Architect agent to run /pl-spec instead." and stop.

---

Given the topic provided as an argument:

1. Run `/pl-find <topic>` logic first to determine if a spec already exists or needs updating.
2. If updating: open the existing feature file, review its current state, identify gaps, and propose targeted additions or revisions. Apply changes after user confirmation.
3. If creating: scaffold a new feature file in `features/` with the canonical Purlin structure (label, category, prerequisite links, requirements sections, Gherkin scenarios, Implementation Notes stub). Identify appropriate prerequisite anchor nodes and include them as `> Prerequisite:` links.
4. After editing, commit the change and run `tools/cdd/status.sh` to regenerate the Critic report.
