# Feature: Agent Config Skill

> Label: "/pl-agent-config: Agent Configuration"
> Category: "Agent Skills"
> Prerequisite: features/policy_collaboration.md
> Prerequisite: features/cdd_agent_configuration.md
> Prerequisite: features/config_layering.md

[TODO]

## 1. Overview

The `/pl-agent-config` skill provides the ONLY sanctioned way for agents to modify agent configuration. It writes to `.purlin/config.local.json` (the gitignored local config), never to the committed `config.json`. Because the local config is gitignored, no git commit is made after changes.

When invoked from inside an isolated worktree, all changes are applied to the MAIN project's `config.local.json` (not the worktree's ephemeral copy), and the user is shown an explicit warning before proceeding.

This skill eliminates the "accidental config commit" problem entirely. The local config file is gitignored, so changes never appear in git status or get committed. In worktree sessions, configs are ephemeral by design -- created by `create_isolation.sh` as snapshots of MAIN config at creation time and discarded when `kill_isolation.sh` removes the worktree. The skill routes all changes to the MAIN project's local config for persistence.

---

## 2. Requirements

### 2.1 Command Interface

```
/pl-agent-config [<role>] <key> <value>
```

- **role** (optional): `architect`, `builder`, or `qa`. If omitted, the current agent infers its own role from instruction context.
- **key**: A dot-path key within the role's config block (e.g., `startup_sequence`, `model`, `effort`, `bypass_permissions`, `recommend_next_actions`).
- **value**: The new value. Booleans are accepted as `true`/`false`. String values are accepted as-is.

**Examples:**
```
/pl-agent-config startup_sequence false           # sets for current role
/pl-agent-config architect model claude-opus-4-6
/pl-agent-config builder startup_sequence true
/pl-agent-config effort high                      # sets for current role
```

### 2.2 Routing Invariant

Config changes MUST ALWAYS be applied to the MAIN project's `.purlin/config.local.json`, never to the current session's worktree copy. This invariant holds regardless of whether the skill is invoked from:

- A non-isolated session (normal case: the main local config IS the only local config)
- An isolated worktree session (routing required: must target the main checkout's local config)

### 2.3 Worktree Context Detection

The skill detects worktree context using:

```bash
git rev-parse --abbrev-ref HEAD
```

If the result starts with `isolated/`, the session is in an isolated worktree. The isolation name is the substring after `isolated/`.

When in a worktree, the MAIN project root is located by parsing `git worktree list --porcelain` and finding the entry whose `branch` field is `refs/heads/main` (or the first worktree entry). This is the same detection logic used by `/pl-isolated-push`.

### 2.4 Explicit Worktree Warning

When invoked inside an isolated worktree, the skill MUST display this confirmation prompt before applying any change:

```
⚠  Worktree context: isolated/<name>

Config changes are ALWAYS applied to the MAIN project local config:
  <PROJECT_ROOT>/.purlin/config.local.json

The current worktree's config is ephemeral -- it will be discarded
when this team is killed. Your change will take effect the next time
an isolated team is created from main.

Continue? [y/N]
```

If the user responds `N` or any non-affirmative input, the skill aborts without making any changes.

### 2.5 Key Validation

The skill MUST reject unknown keys with a clear error. Valid keys for any role are:

- `model` — must match an `id` in the `models` array in config
- `effort` — must be one of `low`, `medium`, `high`
- `startup_sequence` — must be `true` or `false`
- `recommend_next_actions` — must be `true` or `false`
- `bypass_permissions` — must be `true` or `false`

### 2.6 Atomic Write

The skill writes config changes atomically:

1. Read the current config JSON from the target path (MAIN local config).
2. Update the specified key within the role's block.
3. Write to a temp file first, then rename to final path.

### 2.7 No Commit (Gitignored File)

Because `config.local.json` is gitignored, no git commit is made after writing. The skill confirms the change with a status message but does not invoke any git commands.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Config Change Applied to Local Config in Non-Isolated Session

    Given the current branch is main (not an isolated worktree)
    And .purlin/config.local.json has startup_sequence true for builder
    When /pl-agent-config builder startup_sequence false is invoked
    Then .purlin/config.local.json has startup_sequence false for builder
    And .purlin/config.json is unchanged
    And no git commit is made

#### Scenario: Worktree Warning Displayed in Isolated Session

    Given the current branch is isolated/feat1
    When /pl-agent-config startup_sequence false is invoked
    Then the warning is displayed showing the main local config path
    And the user is prompted to confirm before proceeding

#### Scenario: Worktree Change Applied to MAIN Local Config

    Given the current branch is isolated/feat1
    And the main checkout is at /project/
    And /project/.purlin/config.local.json has startup_sequence true for builder
    When /pl-agent-config builder startup_sequence false is invoked
    And the user confirms the warning
    Then /project/.purlin/config.local.json has startup_sequence false for builder
    And the worktree's .purlin/config.local.json is UNCHANGED
    And no git commit is made

#### Scenario: Worktree Change Aborted on User Denial

    Given the current branch is isolated/feat1
    When /pl-agent-config startup_sequence false is invoked
    And the user responds N to the warning prompt
    Then no config file is modified
    And no git commit is made

#### Scenario: Invalid Key Rejected

    Given a valid .purlin/config.json exists at the project root
    When /pl-agent-config builder unknown_key value is invoked
    Then the skill exits with an error listing valid keys
    And no config file is modified

#### Scenario: Invalid Model Value Rejected

    Given the config models array contains only claude-sonnet-4-6 and claude-haiku-4-5
    When /pl-agent-config architect model claude-gpt-5 is invoked
    Then the skill exits with an error listing valid model IDs
    And no config file is modified

### Manual Scenarios (Human Verification Required)

None.

---

## 4. Implementation Notes

**Routing logic:** The skill uses the same MAIN checkout detection as `/pl-isolated-push`: check `PURLIN_PROJECT_ROOT` env var if set, otherwise parse `git worktree list --porcelain` to find the main checkout path (the entry whose `branch` field is `refs/heads/main`).

**Why not update the worktree config?** Worktree configs are intentionally ephemeral -- created by `create_isolation.sh` as snapshots of MAIN config at creation time and discarded when `kill_isolation.sh` removes the worktree. There is no mechanism to sync worktree config changes back to MAIN. An agent that modifies only the worktree config gets a "lost update" -- the change vanishes at kill time. The skill prevents this by routing all changes to MAIN.

**No commit needed:** Because `config.local.json` is gitignored, the previous `git add + git commit` step is eliminated. The skill simply writes the file and confirms the change to the user.

**Role inference:** When no role argument is given, the agent uses its own role (e.g., the Architect sets `architect` keys by default). The role must be validated against `[architect, builder, qa]`.
