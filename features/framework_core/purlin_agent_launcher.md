# Feature: Purlin Unified Agent Session Entry Point

> Label: "Tool: Purlin Unified Agent Session Entry Point"
> Category: "Framework Core"
> Prerequisite: agent_launchers_common.md

## 1. Overview

The Purlin unified agent replaces four separate role-specific agent sessions (PM, Engineer, QA, PM) with a single session that uses three operating modes (Engineer, PM, QA) activated by skill invocations. The session entry point (`purlin:resume`) provides flags for model selection, mode entry, auto-start, and worktree isolation. Users start sessions by running `claude` (the Purlin plugin auto-activates), and the `purlin:resume` skill handles session initialization. Old role-specific launchers have been retired.

---

## 2. Requirements

### 2.1 Session Entry Point Structure

- `purlin:resume` MUST be available as a skill within the Purlin plugin, invoked inside Claude Code.
- Users start sessions by running `claude` from the project root; the plugin auto-activates.
- The `purlin:resume` skill MUST load `PURLIN_BASE.md` as the sole base instruction file. Optional override: `PURLIN_OVERRIDES.md` (if exists).
- The session entry point MUST export `AGENT_ROLE="purlin"` before initialization.
- The session entry point MUST resolve config via `resolve_config.py purlin` with fallback to `agents.builder` if `agents.purlin` is absent.
- The session entry point MUST handle graceful shutdown with terminal identity cleanup (via plugin hooks).
- The session entry point MUST resolve startup control dependencies and validate the result (see Section 2.8).

### 2.2 CLI Arguments

CLI flags fall into two categories: **sticky** flags that persist preferences to `config.local.json` for future runs, and **ephemeral** flags that affect only the current session.

#### 2.2.1 Sticky Flags (Saved Preferences)

Sticky flags write their resolved value to `config.local.json` via `resolve_config.py set_agent_config purlin <key> <value>`. The write happens after name resolution and validation, before session initialization. When `--no-save` is present, sticky flags still apply to the current session but do NOT write to config.

| Flag | Config key | Description |
|------|-----------|-------------|
| `--model [id]` | `agents.purlin.model` | Set default model. Bare `--model` triggers interactive model+effort selection. With argument (e.g., `--model opus`), selects that model. Short names resolve: `opus` -> `claude-opus-4-6`, `sonnet` -> `claude-sonnet-4-6`, `haiku` -> `claude-haiku-4-5-20251001`. Persists the resolved full model ID. |
| `--effort <level>` | `agents.purlin.effort` | Set default effort level (high, medium). Persists the selected level. |
| `--yolo` | `agents.purlin.bypass_permissions` -> `true` | Enable YOLO mode: passes `--dangerously-skip-permissions` to Claude, skipping all permission prompts. Persists to config. |
| `--no-yolo` | `agents.purlin.bypass_permissions` -> `false` | Disable YOLO mode: restores normal permission prompts. Persists to config. |
| `--find-work <bool>` | `agents.purlin.find_work` | Set default work discovery (true/false). Persists the value. |

- Sticky flags MUST persist proper JSON types: booleans for `bypass_permissions` and `find_work`, strings for `model` and `effort`. The resolver's `set_agent_config` MUST coerce `"true"`/`"false"` CLI strings to Python booleans for boolean config fields.
- The session entry point MUST resolve startup control dependencies and validate the result BEFORE persisting sticky values. Invalid combinations MUST fail without modifying config. See Section 2.8.

#### 2.2.2 Ephemeral Flags (Session-Only)

Ephemeral flags affect only the current session and are never written to config.

- `--mode <pm|engineer|qa>` — Enters a specific mode on startup.
- `--build` — Alias for `--mode engineer --auto-start`.
- `--auto-verify` — Alias for `--mode qa --auto-start`.
- `--pm`, `--qa` — Shorthand for `--mode pm`, `--mode qa`.
- `--verify [feature]` — `--mode qa`, optionally scoped to one feature.
- `--auto-start` — Used with `--mode`: enters the mode and begins executing the work plan immediately without waiting for approval (e.g., `--mode engineer --auto-start`). Has no effect without `--mode`. **Config-driven `auto_start`:** When `auto_start: true` is set in the config (not via CLI), it takes effect only when a mode is resolved — either from `default_mode` in config or from `.purlin_session.lock`. If no mode is resolved, `auto_start` is a no-op and the agent waits for mode selection.
- `--worktree` — Runs in an isolated git worktree (see worktree feature).

#### 2.2.3 Meta Flags

- `--help` — Show help and exit.
- `--no-save` — Suppresses persistence for all sticky flags in this invocation. The flag values still apply to the current session but are NOT written to `config.local.json`. Has no effect on ephemeral flags. Has no effect on first-run interactive selection (which always persists). Example: `purlin:resume --no-save --model haiku` uses Haiku this session without changing the stored default.

#### 2.2.4 Help Text Layout

The `--help` output MUST visually separate sticky and ephemeral flags so users understand persistence at a glance. Required layout:

```
Usage: purlin:resume [OPTIONS]

Start a Purlin agent session.

Saved preferences (written to .purlin/config.local.json):
  --model [id]         Set default model (opus, sonnet, haiku, or full ID).
                       Interactive if no value. Saves to config.
  --effort <level>     Set default effort level (high, medium). Saves to config.
  --yolo               Enable YOLO mode (skip all permission prompts). Saves to config.
  --no-yolo            Disable YOLO mode (restore permission prompts). Saves to config.
  --find-work <bool>   Set default work discovery (true/false). Saves to config.

  Use --no-save to apply any of the above for THIS SESSION ONLY
  without changing your saved config.
  Example: purlin:resume --no-save --model haiku

Session options (this run only, never saved):
  --mode <mode>        Set starting mode (pm, engineer, qa).
  --build              Start in Engineer mode with auto-start.
  --auto-verify        Start in QA mode with auto-start.
  --pm                 Start in PM mode.
  --qa                 Start in QA mode.
  --verify [feature]   Start QA mode. Optional: feature name to verify.
  --auto-start         With --mode: begin executing immediately.
  --worktree           Run in an isolated git worktree.

Other:
  --no-save            Don't save preferences to config (use with flags above).
  --help               Show this help message and exit.

Examples:
  purlin:resume                              # Interactive session
  purlin:resume --build                      # Engineer mode, auto-start
  purlin:resume --model opus                 # Use Opus (saved for next time)
  purlin:resume --no-save --model haiku      # Use Haiku just this once
  purlin:resume --yolo                       # YOLO mode on (saved)
  purlin:resume --no-save --yolo             # YOLO just this session
  purlin:resume --verify my_feature          # QA verify a specific feature
```

Requirements:
- Two visually distinct groups with headers: "Saved preferences" and "Session options."
- Every sticky flag description ends with "Saves to config."
- The `--no-save` callout appears inline immediately after the sticky group with an example — not buried at the bottom.
- `--no-save` appears both inline (contextual) and in the "Other" section (completeness).
- Examples include both sticky and `--no-save` variants side by side.

### 2.3 First-Run Model Selection

- If `agents.purlin` is absent from `config.local.json`, the session entry point MUST prompt interactively for model and effort level.
- The selection MUST be stored in `config.local.json` under `agents.purlin` via `resolve_config.py set_agent_config`. This persistence is NOT affected by `--no-save` — first-run interactive selection is explicitly establishing defaults, not overriding them.
- CLI sticky flags MUST always override stored config (and persist the override, unless `--no-save`).

### 2.4 Terminal Identity and Remote Control Name

The `purlin:resume` skill MUST set the iTerm badge, terminal title, and remote control session name during session initialization. These provide immediate visual context and enable remote session management.

#### 2.4.1 Initial Badge and Title

The session entry point sets all terminal environments using `update_session_identity` from `tools/terminal/identity.sh`. The unified format MUST include the current git branch:

- **Unified format (badge, title, remote — all identical):** `<short_mode>(<context>) | <label>` — e.g., `Purlin(main) | purlin`, `Eng(feature-xyz) | purlin`.
- **Worktree override:** If running in a worktree (`.purlin_worktree_label` exists), the worktree label replaces the branch — e.g., `Eng(W1) | purlin`.
- **Mode shortening:** `Engineer` -> `Eng`; `PM`, `QA`, `Purlin` unchanged.

The branch is detected via `git rev-parse --abbrev-ref HEAD`. This is the user's first visual signal that the agent is starting. `purlin:resume` Step 11 updates the mode name but preserves the branch context — e.g., `Purlin(main) | purlin` becomes `PM(main) | purlin`.

#### 2.4.2 Remote Control Session Name

The `purlin:resume` skill MUST configure the session name via the `/rename` command or equivalent mechanism. This sets the session name visible in claude.ai/code and the mobile app.

- **Format:** `<project> | <badge>` — e.g., `purlin | Purlin (main)`, `purlin | Engineer (W1)`.
- The session name persists for the lifetime of the session, even if the badge changes later.

#### 2.4.3 Session Overrides File

The `purlin:resume` skill MUST write `.purlin/cache/session_overrides.json` with the resolved `find_work` and `auto_start` values during session initialization. This file bridges ephemeral CLI flags (`--no-save --find-work false`, `--auto-start`) to the agent.

- **Written:** After sticky flag persistence and validation, before mode activation.
- **Format:** `{"find_work": <bool>, "auto_start": <bool>}` — JSON with boolean values matching the resolved state.
- **Read by:** `purlin:resume` Step 9 (takes priority over `config.local.json`).
- **Lifetime:** Persists for the terminal session. The SessionEnd hook deletes it on session end. `purlin:resume` does NOT delete it (so it survives `/clear`).
- **Absent:** When `purlin:resume` is invoked outside a launcher session (e.g., user types it manually after `/clear`), the file does not exist and the agent falls back to `config.local.json`.

### 2.5 Session Message Encoding

- No `--mode`: `"Begin Purlin session."`
- `--build`: `"Begin Purlin session. Enter Engineer mode. Run purlin:build."`
- `--verify <feature>`: `"Begin Purlin session. Enter QA mode. Run purlin:verify <feature>."`
- `--pm`: `"Begin Purlin session. Enter PM mode."`

### [RETIRED] 2.6 Legacy Launcher Deprecation

This section described the deprecation period for old role-specific shell launchers (`pl-run-architect.sh`, `pl-run-builder.sh`, `pl-run-qa.sh`, `pl-run-pm.sh`). These launchers have been fully retired and replaced by the `purlin:resume` skill. Users now start sessions with `claude` and the plugin auto-activates.

### 2.7 Config Schema

- `.purlin/config.json` and `purlin-config-sample/config.json` MUST include an `agents.purlin` section with fields: `model`, `effort`, `bypass_permissions`, `find_work`, `auto_start`, `default_mode`.
- `tools/config/resolve_config.py` MUST accept `"purlin"` as a valid role name.
- When resolving `purlin` config, if `agents.purlin` is absent, fall back to `agents.builder`.
- `--yolo`/`--no-yolo` map to the existing `bypass_permissions` field.

### 2.8 Startup Control Resolution

CLI flags that activate `auto_start` (`--auto-start`, `--build`, `--auto-verify`) imply that work discovery is needed. When the saved config has `find_work: false`, the session entry point MUST distinguish between an implied dependency and an explicit contradiction.

**Resolution rules (applied after CLI overrides, before validation):**

1. **Implied dependency:** `auto_start` activated via CLI, `find_work` is `false` from saved config, and `--find-work` was NOT passed on the CLI. The session entry point MUST temporarily set `find_work=true` for the current session. This override is ephemeral — it MUST NOT be persisted to config. Rationale: convenience aliases like `--auto-verify` bundle intent; requiring the user to also pass `--find-work true` to counteract a saved preference defeats the purpose.

2. **Explicit contradiction:** `auto_start` activated via CLI AND `--find-work false` passed explicitly on the same CLI (including interactive selection via bare `--find-work`). The session entry point MUST exit with error: `"Error: --find-work false conflicts with --auto-start. Cannot auto-start without work discovery."`

3. **Config-only conflict:** Both `auto_start: true` and `find_work: false` from config, no CLI override for either. The config is in an invalid state. The session entry point MUST exit with the existing error message.

**Interactive selection edge case:** When `--find-work` is passed without a value (bare flag), the interactive menu sets the find_work value to the user's choice. After the menu, the sentinel MUST be replaced with the selected value (not cleared to empty). This preserves the "user explicitly chose this" signal so the dependency resolution treats it the same as `--find-work false`.

**Post-resolution validation:** If `find_work` is still `false` and `auto_start` is `true`, exit with error (catches case 3).

---

## 3. Scenarios

### Unit Tests

#### Scenario: purlin:resume skill is available

    Given the Purlin plugin is installed
    When checking available skills
    Then purlin:resume is available
    And can be invoked within a Claude Code session

#### Scenario: Consumer project initialization

    Given a consumer project using Purlin as a submodule
    When init.sh runs a full initialization
    Then the Purlin plugin is configured
    And purlin:resume is available via the plugin

#### Scenario: Help output separates sticky and ephemeral flags

    Given purlin:resume is available
    When invoked with --help
    Then the output contains a "Saved preferences" section with --model, --effort, --yolo, --no-yolo, --find-work
    And the output contains a "Session options" section with --mode, --build, --auto-verify, --pm, --qa, --verify, --auto-start, --worktree
    And the output contains --no-save with an inline explanation after the sticky group
    And every sticky flag description includes "Saves to config"
    And the Examples section shows both sticky and --no-save variants

#### Scenario: Config resolver accepts purlin role

    Given a config.json with agents.purlin section
    When resolve_config.py is called with "purlin" as role argument
    Then it outputs AGENT_MODEL from agents.purlin
    And it outputs AGENT_EFFORT from agents.purlin

#### Scenario: Config resolver falls back to builder

    Given a config.json without agents.purlin but with agents.builder
    When resolve_config.py is called with "purlin" as role argument
    Then it outputs AGENT_MODEL from agents.builder

#### Scenario: CLI model short name resolution and persistence

    Given purlin:resume is invoked with --model opus
    When the session entry point resolves the model name
    Then AGENT_MODEL is set to "claude-opus-4-6"
    And config.local.json contains agents.purlin.model = "claude-opus-4-6"

#### Scenario: --yolo sets bypass_permissions true in config

    Given config.local.json has agents.purlin.bypass_permissions = false
    When purlin:resume is invoked with --yolo
    Then --dangerously-skip-permissions is passed to Claude
    And config.local.json contains agents.purlin.bypass_permissions = true (boolean, not string)

#### Scenario: --no-yolo sets bypass_permissions false in config

    Given config.local.json has agents.purlin.bypass_permissions = true
    When purlin:resume is invoked with --no-yolo
    Then --dangerously-skip-permissions is NOT passed to Claude
    And config.local.json contains agents.purlin.bypass_permissions = false (boolean, not string)

#### Scenario: --no-save prevents sticky flag persistence

    Given config.local.json has agents.purlin.model = "claude-opus-4-6"
    When purlin:resume is invoked with --no-save --model haiku
    Then the session uses model "claude-haiku-4-5-20251001"
    And config.local.json still contains agents.purlin.model = "claude-opus-4-6"

#### Scenario: --no-save with --yolo does not persist bypass_permissions

    Given config.local.json has agents.purlin.bypass_permissions = false
    When purlin:resume is invoked with --no-save --yolo
    Then --dangerously-skip-permissions is passed to Claude for this session
    And config.local.json still contains agents.purlin.bypass_permissions = false

#### Scenario: --find-work persists to config

    Given purlin:resume is invoked with --find-work false
    When the session entry point processes arguments
    Then config.local.json contains agents.purlin.find_work = false (boolean)

#### Scenario: Multiple sticky flags persist together

    Given purlin:resume is invoked with --model sonnet --effort medium --yolo
    When the session entry point processes arguments
    Then config.local.json contains agents.purlin.model = "claude-sonnet-4-6"
    And config.local.json contains agents.purlin.effort = "medium"
    And config.local.json contains agents.purlin.bypass_permissions = true

#### Scenario: Explicit contradiction exits with error

    Given config.local.json has agents.purlin.find_work = true
    When purlin:resume is invoked with --find-work false --auto-start --mode engineer
    Then the session entry point exits with error "Error: --find-work false conflicts with --auto-start. Cannot auto-start without work discovery."
    And config.local.json still contains agents.purlin.find_work = true (not modified)

#### Scenario: Auto-verify implies find_work when saved config has it false

    Given config.local.json has agents.purlin.find_work = false
    When purlin:resume is invoked with --auto-verify
    Then find_work is temporarily set to true for this session
    And config.local.json still contains agents.purlin.find_work = false (not modified)
    And the session launches successfully with find_work=true and auto_start=true

#### Scenario: --build implies find_work when saved config has it false

    Given config.local.json has agents.purlin.find_work = false
    When purlin:resume is invoked with --build
    Then find_work is temporarily set to true for this session
    And config.local.json still contains agents.purlin.find_work = false (not modified)
    And the session launches successfully with find_work=true and auto_start=true

#### Scenario: Config-only find_work/auto_start conflict exits with error

    Given config.local.json has agents.purlin.find_work = false and agents.purlin.auto_start = true
    When purlin:resume is invoked with no CLI flags
    Then the session entry point exits with error about find_work=false with auto_start=true being invalid

#### Scenario: Interactive --find-work selecting false with --auto-verify exits with error

    Given purlin:resume is invoked with --find-work --auto-verify (bare --find-work triggers menu)
    When the user selects false in the interactive find-work menu
    Then the session entry point exits with error "--find-work false conflicts with --auto-start"
    And the interactive selection is treated as an explicit user choice, not a config default

#### Scenario: CLI --build alias

    Given purlin:resume is invoked with --build
    When the session entry point parses arguments
    Then mode is "engineer"
    And auto_start is true
    And the session message contains "Enter Engineer mode"

#### Scenario: Session message for QA verify with feature

    Given purlin:resume is invoked with --verify notifications
    When the session entry point constructs the session message
    Then the message contains "Enter QA mode"
    And the message contains "Run purlin:verify notifications"

### QA Scenarios

#### Scenario: First-run interactive model selection @manual

    Given no agents.purlin in config.local.json
    When purlin:resume is invoked without --model
    Then the session entry point prompts for model selection
    And the session entry point prompts for effort selection
    And the selection is stored in config.local.json

#### Scenario: Instruction stack assembly @auto

    Given PURLIN_BASE.md exists in instructions/
    When purlin:resume initializes the session
    Then the system prompt contains PURLIN_BASE.md content
    And the system prompt contains PURLIN_OVERRIDES.md content if file exists

#### Scenario: Help output includes yolo and no-save flags @auto

    Given purlin:resume is available
    When invoked with --help
    Then the output contains "--yolo" and "--no-yolo" in the "Saved preferences" section
    And the output contains "--no-save" in the "Other" section
    And the output contains at least one --no-save example

## Regression Guidance
- Verify purlin:resume handles missing PURLIN_BASE.md gracefully (during partial setup)
- Verify config.local.json is not corrupted by concurrent model selection writes
- Verify --worktree flag creates worktree directory under .purlin/worktrees/
- Verify sticky flag persistence uses correct JSON types (booleans for bypass_permissions/find_work, not strings)
- Verify --no-save does not suppress first-run interactive persistence
