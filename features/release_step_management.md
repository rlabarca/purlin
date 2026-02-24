# Feature: Local Release Step Management

> Label: "Local Release Step Management: /pl-release-step"
> Category: "Release Process"
> Prerequisite: features/policy_release.md
> Prerequisite: features/release_checklist_core.md

## 1. Overview

This feature defines the CLI tool and Architect slash command for creating, modifying, and deleting local release steps. The tool enforces schema correctness and namespace safety before writing to `.purlin/release/local_steps.json` and `.purlin/release/config.json`, preventing the malformed states that manual JSON editing can introduce.

## 2. Requirements

### 2.1 CLI Tool

A CLI tool at `tools/release/manage_step.py` accepts three sub-commands: `create`, `modify`, and `delete`.

**Shared behavior across all sub-commands:**

*   Tool locates the project root using `PURLIN_PROJECT_ROOT` first, then directory-climbing fallback (per the submodule safety contract in `submodule_bootstrap.md`).
*   Target files are `.purlin/release/local_steps.json` and `.purlin/release/config.json`.
*   If `local_steps.json` does not exist, treat it as `{"steps": []}`. Do NOT error on absence.
*   If `config.json` does not exist, treat it as `{"steps": []}`. Do NOT error on absence.
*   Writes are atomic: write to a temp file, then rename into place to prevent partial-write corruption.
*   `--dry-run` flag: print the proposed JSON output for the affected file(s) without writing. Exit code 0 on valid input, non-zero on validation failure, regardless of dry-run mode.

**`create` sub-command:**

```
manage_step.py create --id <id> --name <friendly_name> --desc <description>
                      [--code <shell_command>] [--agent-instructions <text>]
                      [--dry-run]
```

On success: appends the new step object to `local_steps.json` and appends `{"id": "<id>", "enabled": true}` to the steps array in `config.json`.

**`modify` sub-command:**

```
manage_step.py modify <id> [--name <friendly_name>] [--desc <description>]
                           [--code <shell_command>] [--agent-instructions <text>]
                           [--clear-code] [--clear-agent-instructions]
                           [--dry-run]
```

At least one field flag must be provided; `--clear-code` and `--clear-agent-instructions` each count as a field flag. `--clear-code` sets `code` to `null`; `--clear-agent-instructions` sets `agent_instructions` to `null`. It is an error to specify both `--code` and `--clear-code` in the same invocation, or both `--agent-instructions` and `--clear-agent-instructions`.

On success: updates the matching step object in `local_steps.json`. `config.json` is not modified (ordering and enabled state are preserved).

**`delete` sub-command:**

```
manage_step.py delete <id> [--dry-run]
```

On success: removes the step with the given ID from `local_steps.json` and removes the corresponding entry from `config.json`.

### 2.2 Validation Rules

| Rule | Sub-command(s) | Behavior on failure |
|------|----------------|---------------------|
| `id` must not start with `purlin.` | create | Exit code 1; error message identifying the reserved prefix. |
| `id` must not be empty | create | Exit code 1. |
| `friendly_name` must be non-empty | create | Exit code 1. |
| `description` must be non-empty | create | Exit code 1. |
| `id` must not already exist in `local_steps.json` | create | Exit code 1; error identifies conflict as "local". |
| `id` must not already exist in `global_steps.json` | create | Exit code 1; error identifies conflict as "global". |
| `id` must exist in `local_steps.json` | modify, delete | Exit code 1: "step not found: `<id>`". |
| At least one field flag required | modify | Exit code 1: usage message. |
| `--code` and `--clear-code` are mutually exclusive | modify | Exit code 1. |
| `--agent-instructions` and `--clear-agent-instructions` are mutually exclusive | modify | Exit code 1. |

Validation errors print a human-readable message to stderr. No files are modified.

### 2.3 Output Format

**On success (without `--dry-run`):**

```
Created step 'my_step' in local_steps.json and config.json.
Updated step 'my_step' in local_steps.json.
Deleted step 'my_step' from local_steps.json and config.json.
```

**On `--dry-run`:**

The tool prints a `[DRY RUN]` header followed by the full proposed JSON for each file that would be modified:

```
[DRY RUN] local_steps.json would be written as:
{
  "steps": [...]
}

[DRY RUN] config.json would be written as:
{
  "steps": [...]
}
```

### 2.4 Slash Command: /pl-release-step

The Architect slash command `/pl-release-step [create|modify|delete] [<step-id>]` provides a guided, interactive interface over the CLI tool. If no operation argument is given, the command presents the three operations and prompts the user to choose.

**Operation: create**

1.  Prompt for: step ID, friendly name, description (all required).
2.  Ask whether this step has an automation command (`code` field). If yes, prompt for the shell command string.
3.  Ask whether this step has agent instructions. If yes, prompt for the text.
4.  Run `tools/release/manage_step.py create --dry-run ...` with all gathered values. Display the dry-run output.
5.  Ask for user confirmation before proceeding.
6.  On confirmation: run without `--dry-run`. Commit: `git commit -m "release-step(create): <step-id>"`.

**Operation: modify**

1.  If no step ID is provided, list current local steps by ID and friendly name, and ask the user to choose one.
2.  Display the full current step definition.
3.  Walk through each field (friendly name, description, code, agent instructions), showing the current value and prompting for a new value. Pressing Enter keeps the existing value. For `code` and `agent_instructions`, also offer a "clear to null" option.
4.  If no fields changed, report "No changes made." and stop.
5.  Run `tools/release/manage_step.py modify <id> --dry-run [changed fields only]`. Display the dry-run output.
6.  Ask for user confirmation.
7.  On confirmation: run without `--dry-run`. Commit: `git commit -m "release-step(modify): <step-id>"`.

**Operation: delete**

1.  If no step ID is provided, list current local steps and ask the user to choose one.
2.  Display the step definition to be deleted.
3.  Warn: "This will remove the step from both local_steps.json and config.json. Any feature files or documentation referencing this step ID will become stale."
4.  Ask the user to confirm by typing the step ID exactly.
5.  On confirmation: run `tools/release/manage_step.py delete <id>`. Commit: `git commit -m "release-step(delete): <step-id>"`.

After any successful operation, confirm the outcome and note that the CDD Dashboard will reflect the update on its next refresh cycle.

## 3. Scenarios

### Automated Scenarios

#### Scenario: Create valid local step
Given `local_steps.json` is absent and `config.json` is absent,
When `manage_step.py create --id "my_step" --name "My Step" --desc "Does something"` is run,
Then the tool exits with code 0,
And `local_steps.json` contains one step with `id: "my_step"`, `friendly_name: "My Step"`, `description: "Does something"`, `code: null`, `agent_instructions: null`,
And `config.json` contains `{"id": "my_step", "enabled": true}` in the steps array.

#### Scenario: Reject purlin. prefix on create
Given `local_steps.json` is absent,
When `manage_step.py create --id "purlin.custom" --name "Custom" --desc "Custom step"` is run,
Then the tool exits with code 1,
And stderr contains a message identifying the reserved `purlin.` prefix,
And no files are created or modified.

#### Scenario: Reject duplicate local ID on create
Given `local_steps.json` contains a step with `id: "existing_step"`,
When `manage_step.py create --id "existing_step" --name "Dupe" --desc "Duplicate"` is run,
Then the tool exits with code 1,
And stderr identifies `existing_step` as already existing in local steps,
And `local_steps.json` is unchanged.

#### Scenario: Reject duplicate global ID on create
Given `global_steps.json` contains a step with `id: "purlin.push_to_remote"`,
When `manage_step.py create --id "purlin.push_to_remote" --name "Push" --desc "Custom push"` is run,
Then the tool exits with code 1,
And stderr identifies the conflict (the `purlin.` prefix check fires first in this case),
And no files are modified.

#### Scenario: Modify existing step name
Given `local_steps.json` contains a step with `id: "my_step"`, `friendly_name: "Old Name"`, and `description: "Desc"`,
And `config.json` contains `{"id": "my_step", "enabled": false}`,
When `manage_step.py modify my_step --name "New Name"` is run,
Then the tool exits with code 0,
And `local_steps.json` contains the step with `friendly_name: "New Name"`,
And all other fields of the step are unchanged,
And `config.json` is unchanged (enabled state and order preserved).

#### Scenario: Modify clears optional field
Given `local_steps.json` contains a step with `id: "my_step"` and `code: "echo hello"`,
When `manage_step.py modify my_step --clear-code` is run,
Then the tool exits with code 0,
And `local_steps.json` contains the step with `code: null`,
And all other fields of the step are unchanged.

#### Scenario: Delete step removes from both files
Given `local_steps.json` contains a step with `id: "my_step"`,
And `config.json` contains `{"id": "my_step", "enabled": true}` in the steps array,
When `manage_step.py delete my_step` is run,
Then the tool exits with code 0,
And `local_steps.json` no longer contains a step with `id: "my_step"`,
And `config.json` no longer contains an entry with `id: "my_step"`.

#### Scenario: Modify non-existent step
Given `local_steps.json` does not contain a step with `id: "ghost_step"`,
When `manage_step.py modify ghost_step --name "New Name"` is run,
Then the tool exits with code 1,
And stderr contains "step not found: ghost_step".

#### Scenario: Dry-run does not modify files
Given `local_steps.json` is absent,
When `manage_step.py create --id "my_step" --name "My Step" --desc "Desc" --dry-run` is run,
Then the tool exits with code 0,
And `local_steps.json` is not created,
And stdout contains `[DRY RUN]` followed by the proposed JSON.

#### Scenario: Modify with no field flags fails
Given `local_steps.json` contains a step with `id: "my_step"`,
When `manage_step.py modify my_step` is run with no field flags,
Then the tool exits with code 1,
And stderr contains a usage message.

#### Scenario: Mutually exclusive flags rejected
Given `local_steps.json` contains a step with `id: "my_step"` and `code: "echo hi"`,
When `manage_step.py modify my_step --code "echo bye" --clear-code` is run,
Then the tool exits with code 1,
And stderr identifies `--code` and `--clear-code` as mutually exclusive.

### Manual Scenarios
None. All verification is automated.

## Implementation Notes

See [release_step_management.impl.md](release_step_management.impl.md) for implementation knowledge, builder decisions, and tribal knowledge.
