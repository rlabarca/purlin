**Purlin command owner: Architect**

If you are not operating as the Purlin Architect, respond: "This is an Architect command. Ask your Architect agent to run /pl-release-step instead." and stop.

---

Manage local release steps interactively. Operates on `.agentic_devops/release/local_steps.json` and `.agentic_devops/release/config.json` via `tools/release/manage_step.py`.

**Supported operations:** `create`, `modify`, `delete`
**Usage:** `/pl-release-step [create|modify|delete] [<step-id>]`

If no operation argument is provided, present the three operations and ask the user to choose.

---

**create:**

1. Prompt for step ID, friendly name, and description (all required).
2. Ask whether this step has an automation command (`code` field). If yes, prompt for the shell command string.
3. Ask whether this step has agent instructions. If yes, prompt for the text.
4. Run `tools/release/manage_step.py create --dry-run --id "<id>" --name "<name>" --desc "<desc>" [--code "<cmd>"] [--agent-instructions "<text>"]`. Display the dry-run output.
5. Ask for user confirmation.
6. On confirmation: run without `--dry-run`. Commit: `git commit -m "release-step(create): <step-id>"`.

**modify:**

1. If no step ID is provided, read `local_steps.json` and list current steps (ID + friendly name). Ask the user to choose one.
2. Display the full current step definition.
3. Walk through each field (friendly name, description, code, agent instructions) one by one. Show the current value and prompt for a new value; press Enter to keep unchanged. For `code` and `agent_instructions`, also offer a "clear to null" option.
4. If no fields changed, report "No changes made." and stop.
5. Run `tools/release/manage_step.py modify <id> --dry-run [changed fields only]`. Display the dry-run output.
6. Ask for user confirmation.
7. On confirmation: run without `--dry-run`. Commit: `git commit -m "release-step(modify): <step-id>"`.

**delete:**

1. If no step ID is provided, read `local_steps.json` and list current steps. Ask the user to choose one.
2. Display the full step definition to be deleted.
3. Warn: "This will remove the step from both local_steps.json and config.json. Any feature files or documentation referencing this step ID will become stale."
4. Ask the user to confirm by typing the step ID exactly.
5. On confirmation: run `tools/release/manage_step.py delete <id>`. Commit: `git commit -m "release-step(delete): <step-id>"`.

After any successful operation, confirm the outcome to the user and note that the CDD Dashboard will reflect the update on its next refresh cycle.
