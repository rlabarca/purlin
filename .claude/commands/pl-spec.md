**Purlin command owner: PM, Architect**

If you are not operating as the Purlin PM or Architect, respond: "This is a PM/Architect command. Ask your PM or Architect agent to run /pl-spec instead." and stop.

---

Given the topic provided as an argument:

0. Read `instructions/references/feature_format.md` for heading format rules, Critic parser requirements, and **category/label naming conventions** before creating or editing a feature file. If the feature has or needs a `## Visual Specification` section, also read `instructions/references/visual_spec_convention.md`.
1. Run `/pl-find <topic>` logic first to determine if a spec already exists or needs updating.
2. If updating: open the existing feature file, review its current state, identify gaps, and propose targeted additions or revisions. Apply changes after user confirmation.
3. If creating:
   a. **Scan existing categories and labels:** Read `.purlin/cache/dependency_graph.json` and extract all unique `category` and `label` values. Identify the naming patterns in use (see `instructions/references/feature_format.md` "Category and Label Consistency" section). Choose the category and label that best fit the existing conventions — do NOT invent a new category when an existing one applies.
   b. Scaffold a new feature file in `features/` with the canonical Purlin structure (label, category, prerequisite links, requirements sections, Gherkin scenarios, Implementation Notes stub). Identify appropriate prerequisite anchor nodes and include them as `> Prerequisite:` links.
4. After editing, commit the change and run `tools/cdd/status.sh` to regenerate the Critic report.
