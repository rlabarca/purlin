**Purlin command owner: Architect**

If you are not operating as the Purlin Architect, respond: "This is an Architect command. Ask your Architect agent to run /pl-release-run instead." and stop.

---

Run a single release step from the project's checklist without executing the full sequence.

**Usage:** `/pl-release-run [<step-name>]`

The `<step-name>` argument matches against a step's `friendly_name` (case-insensitive). Partial matches are accepted; if more than one step matches, list the matches and ask the user to choose.

---

1. **Resolve the checklist.** Load the fully resolved release step list by merging `.purlin/release/config.json` (ordering and enabled state) with step definitions from `tools/release/global_steps.json` and `.purlin/release/local_steps.json`. Apply the auto-discovery algorithm from `release_checklist_core.md` Section 2.5.

2. **Select a step.**
   - If a `<step-name>` argument was provided: match it against all step `friendly_name` values (case-insensitive, partial match allowed).
     - Exactly one match: proceed with that step.
     - Multiple matches: list the matching steps and ask the user to choose one.
     - No match: report "No step found matching '<step-name>'." and stop.
   - If no argument was provided: display all steps in their configured order, numbered. Show friendly name and source (GLOBAL / LOCAL); mark disabled steps with `[disabled]`. Ask the user to choose a step by number.

3. **Display the step definition.** Show: friendly name, source (GLOBAL / LOCAL), description, `code` value (if non-null), and `agent_instructions` (if non-null).

4. **Warn if disabled.** If the step has `enabled: false` in `config.json`, warn: "This step is currently disabled in the release checklist. Proceeding will execute it outside the normal release sequence." Ask for explicit confirmation before continuing.

5. **Execute the step.**
   - If `agent_instructions` is non-null: follow those instructions to complete the step.
   - If `code` is non-null: offer to run the shell command directly, or proceed manually per `agent_instructions` if both are present.
   - If neither field is set: report "This step has no execution instructions. Consult the description above and proceed manually."

6. **Confirm the outcome** to the user after the step's work is complete.
