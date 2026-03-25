# Feature: Purlin Unified Agent Launcher

> Label: "Install, Update & Scripts: Purlin Unified Agent Launcher"
> Category: "Install, Update & Scripts"
> Prerequisite: features/agent_launchers_common.md

## 1. Overview

The Purlin unified agent replaces four separate role-specific agent sessions (Architect, Builder, QA, PM) with a single session that uses three operating modes (Engineer, PM, QA) activated by skill invocations. The launcher (`pl-run.sh`) provides CLI arguments for model selection, mode entry, auto-start, and worktree isolation. In consumer projects, `init.sh` generates `pl-run.sh` via `generate_purlin_launcher()`. In the Purlin framework repo itself, `pl-run.sh` is hand-written (same pattern as the existing role-specific launchers). Old role-specific launchers continue to function with deprecation warnings during the transition period.

---

## 2. Requirements

### 2.1 Launcher Structure

- `pl-run.sh` MUST exist at the project root as an executable shell script.
- In consumer projects, `tools/init.sh` generates `pl-run.sh` via `generate_purlin_launcher()` during both full init and refresh modes.
- In the Purlin framework repo, `pl-run.sh` is hand-written (committed to git, not generated).
- The launcher MUST load `PURLIN_BASE.md` as the sole instruction file (HOW_WE_WORK content is merged in). It MUST NOT load `HOW_WE_WORK_BASE.md` separately. Optional override: `PURLIN_OVERRIDES.md` (if exists).
- The launcher MUST export `AGENT_ROLE="purlin"` before invoking Claude.
- The launcher MUST resolve config via `resolve_config.py purlin` with fallback to `agents.builder` if `agents.purlin` is absent.
- The launcher MUST check for Claude Code updates before launching (same as legacy launchers).
- The launcher MUST handle graceful Ctrl+C shutdown with terminal identity cleanup.
- The launcher MUST display and auto-acknowledge model warnings (same as legacy launchers).
- The launcher MUST validate startup controls (find_work=false + auto_start=true is invalid).
- The launcher MUST include `--help` that dynamically lists available options from the script itself.

### 2.2 CLI Arguments

- `--model [id]` — Bare `--model` triggers interactive model+effort selection. With argument (e.g., `--model opus`), selects that model. Short names resolve: `opus` -> `claude-opus-4-6`, `sonnet` -> `claude-sonnet-4-6`, `haiku` -> `claude-haiku-4-5-20251001`.
- `--effort <level>` — Overrides effort level (low, medium, high).
- `--mode <pm|engineer|qa>` — Enters a specific mode on startup.
- `--auto-build` — Alias for `--mode engineer --auto-start`.
- `--auto-verify` — Alias for `--mode qa --auto-start`.
- `--pm`, `--qa` — Shorthand for `--mode pm`, `--mode qa`.
- `--verify [feature]` — `--mode qa`, optionally scoped to one feature.
- `--auto-start` — Used with `--mode`: enters the mode and begins executing the work plan immediately without waiting for approval (e.g., `--mode engineer --auto-start`). Has no effect without `--mode`. The `--help` text for this flag MUST communicate the `--mode` dependency and include an example — e.g., "With --mode: begin executing immediately. Example: --mode engineer --auto-start. No effect without --mode."
- `--find-work false` — Disables work discovery.
- `--worktree` — Runs in an isolated git worktree (see worktree feature).

### 2.3 First-Run Model Selection

- If `agents.purlin` is absent from `config.local.json`, the launcher MUST prompt interactively for model and effort level.
- The selection MUST be stored in `config.local.json` under `agents.purlin`.
- CLI arguments MUST always override stored config.

### 2.4 Session Message Encoding

- No `--mode`: `"Begin Purlin session."`
- `--auto-build`: `"Begin Purlin session. Enter Engineer mode. Run /pl-build."`
- `--verify <feature>`: `"Begin Purlin session. Enter QA mode. Run /pl-verify <feature>."`
- `--pm`: `"Begin Purlin session. Enter PM mode."`

### 2.5 Legacy Launcher Deprecation

- Old launchers (`pl-run-architect.sh`, `pl-run-builder.sh`, `pl-run-qa.sh`, `pl-run-pm.sh`) MUST print a visible deprecation warning before launching the agent.
- The warning MUST suggest `./pl-run.sh` with example flags.
- Old launchers MUST continue to function (instruction loading, config resolution, skill gates unchanged).

### 2.6 Config Schema

- `.purlin/config.json` and `purlin-config-sample/config.json` MUST include an `agents.purlin` section with fields: `model`, `effort`, `bypass_permissions`, `find_work`, `auto_start`, `default_mode`.
- `tools/config/resolve_config.py` MUST accept `"purlin"` as a valid role name.
- When resolving `purlin` config, if `agents.purlin` is absent, fall back to `agents.builder`.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Launcher exists and is executable

    Given the project root directory
    When checking for pl-run.sh
    Then pl-run.sh exists
    And pl-run.sh is executable

#### Scenario: Consumer project launcher generation on init

    Given a consumer project using Purlin as a submodule
    When init.sh runs a full initialization
    Then pl-run.sh is generated at the project root
    And pl-run.sh is executable

#### Scenario: Help flag lists all options dynamically

    Given pl-run.sh exists
    When invoked with --help
    Then all CLI options are listed with descriptions
    And the help text is generated from the script itself (not hardcoded)

#### Scenario: Config resolver accepts purlin role

    Given a config.json with agents.purlin section
    When resolve_config.py is called with "purlin" as role argument
    Then it outputs AGENT_MODEL from agents.purlin
    And it outputs AGENT_EFFORT from agents.purlin

#### Scenario: Config resolver falls back to builder

    Given a config.json without agents.purlin but with agents.builder
    When resolve_config.py is called with "purlin" as role argument
    Then it outputs AGENT_MODEL from agents.builder

#### Scenario: CLI model short name resolution

    Given pl-run.sh is invoked with --model opus
    When the launcher resolves the model name
    Then AGENT_MODEL is set to "claude-opus-4-6"

#### Scenario: CLI auto-build alias

    Given pl-run.sh is invoked with --auto-build
    When the launcher parses arguments
    Then PURLIN_MODE is "engineer"
    And PURLIN_AUTO_START is "true"
    And the session message contains "Enter Engineer mode"

#### Scenario: Session message for QA verify with feature

    Given pl-run.sh is invoked with --verify notifications
    When the launcher constructs the session message
    Then the message contains "Enter QA mode"
    And the message contains "Run /pl-verify notifications"

### QA Scenarios

#### Scenario: Deprecation warning on old launcher @auto

    Given pl-run-builder.sh exists and is invoked
    When the launcher starts
    Then it prints a deprecation warning mentioning pl-run.sh
    And the agent session starts after the warning

#### Scenario: First-run interactive model selection @manual

    Given no agents.purlin in config.local.json
    When pl-run.sh is invoked without --model
    Then the launcher prompts for model selection
    And the launcher prompts for effort selection
    And the selection is stored in config.local.json

#### Scenario: Instruction stack assembly @auto

    Given PURLIN_BASE.md exists in instructions/
    When pl-run.sh launches the agent
    Then the system prompt contains HOW_WE_WORK_BASE.md content
    And the system prompt contains PURLIN_BASE.md content
    And the system prompt contains PURLIN_OVERRIDES.md content if file exists

## Regression Guidance
- Verify init.sh refresh does not delete old role-specific launchers
- Verify pl-run.sh handles missing PURLIN_BASE.md gracefully (during partial setup)
- Verify config.local.json is not corrupted by concurrent model selection writes
- Verify --worktree flag creates worktree directory under .purlin/worktrees/
