**Purlin command owner: QA**

If you are not operating as the Purlin QA Agent, respond: "This is a QA command. Ask your QA agent to run /pl-discovery instead." and stop.

---

If an argument was provided, record a discovery for `features/<arg>.md`.

If no argument was provided, ask the user which feature the discovery belongs to.

Guide the user through classifying the finding:

- **[BUG]** — behavior contradicts an existing scenario
- **[DISCOVERY]** — behavior exists but no scenario covers it
- **[INTENT_DRIFT]** — behavior matches the spec literally but misses the actual intent
- **[SPEC_DISPUTE]** — the user disagrees with a scenario's expected behavior (the spec itself is wrong)

Ask the user to describe the observed behavior and expected behavior.

Record the entry in the feature file's `## User Testing Discoveries` section using the canonical format.

Commit: `git commit -m "qa(<scope>): [TYPE] - <brief title>"`.
