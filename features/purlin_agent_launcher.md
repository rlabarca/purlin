# Feature: Purlin Unified Agent Launcher

> Label: "Tool: Purlin Unified Agent Launcher"
> Category: "Install, Update & Scripts"
> Prerequisite: features/agent_launchers_common.md

## 1. Overview

The Purlin unified agent replaces four separate role-specific agent sessions (PM, Engineer, QA, PM) with a single session that uses three operating modes (Engineer, PM, QA) activated by skill invocations. The launcher (`pl-run.sh`) provides CLI arguments for model selection, mode entry, auto-start, and worktree isolation. In consumer projects, `init.sh` generates `pl-run.sh` via `generate_purlin_launcher()`. In the Purlin framework repo itself, `pl-run.sh` is hand-written (same pattern as the existing role-specific launchers). Old role-specific launchers continue to function with deprecation warnings during the transition period.

---

## 2. Requirements

### 2.1 Launcher Structure

- `pl-run.sh` MUST exist at the project root as an executable shell script.
- In consumer projects, `tools/init.sh` generates `pl-run.sh` via `generate_purlin_launcher()` during both full init and refresh modes.
- In the Purlin framework repo, `pl-run.sh` is hand-written (committed to git, not generated).
- The launcher MUST load `PURLIN_BASE.md` as the sole base instruction file. Optional override: `PURLIN_OVERRIDES.md` (if exists).
- The launcher MUST export `AGENT_ROLE="purlin"` before invoking Claude.
- The launcher MUST resolve config via `resolve_config.py purlin` with fallback to `agents.builder` if `agents.purlin` is absent.
- The launcher MUST check for Claude Code updates before launching (same as legacy launchers).
- The launcher MUST handle graceful Ctrl+C shutdown with terminal identity cleanup.
- The launcher MUST display and auto-acknowledge model warnings (same as legacy launchers).
- The launcher MUST resolve startup control dependencies and validate the result (see Section 2.8).
- The launcher MUST include `--help` that dynamically lists available options from the script itself.

### 2.2 CLI Arguments

CLI flags fall into two categories: **sticky** flags that persist preferences to `config.local.json` for future runs, and **ephemeral** flags that affect only the current session.

#### 2.2.1 Sticky Flags (Saved Preferences)

Sticky flags write their resolved value to `config.local.json` via `resolve_config.py set_agent_config purlin <key> <value>`. The write happens after name resolution and validation, before launching Claude. When `--no-save` is present, sticky flags still apply to the current session but do NOT write to config.

| Flag | Config key | Description |
|------|-----------|-------------|
| `--model [id]` | `agents.purlin.model` | Set default model. Bare `--model` triggers interactive model+effort selection. With argument (e.g., `--model opus`), selects that model. Short names resolve: `opus` -> `claude-opus-4-6`, `sonnet` -> `claude-sonnet-4-6`, `haiku` -> `claude-haiku-4-5-20251001`. Persists the resolved full model ID. |
| `--effort <level>` | `agents.purlin.effort` | Set default effort level (high, medium). Persists the selected level. |
| `--yolo` | `agents.purlin.bypass_permissions` → `true` | Enable YOLO mode: passes `--dangerously-skip-permissions` to Claude, skipping all permission prompts. Persists to config. |
| `--no-yolo` | `agents.purlin.bypass_permissions` → `false` | Disable YOLO mode: restores normal permission prompts. Persists to config. |
| `--find-work <bool>` | `agents.purlin.find_work` | Set default work discovery (true/false). Persists the value. |

- Sticky flags MUST persist proper JSON types: booleans for `bypass_permissions` and `find_work`, strings for `model` and `effort`. The resolver's `set_agent_config` MUST coerce `"true"`/`"false"` CLI strings to Python booleans for boolean config fields.
- The launcher MUST resolve startup control dependencies and validate the result BEFORE persisting sticky values. Invalid combinations MUST fail without modifying config. See Section 2.8.

#### 2.2.2 Ephemeral Flags (Session-Only)

Ephemeral flags affect only the current session and are never written to config.

- `--mode <pm|engineer|qa>` — Enters a specific mode on startup.
- `--auto-build` — Alias for `--mode engineer --auto-start`.
- `--auto-verify` — Alias for `--mode qa --auto-start`.
- `--pm`, `--qa` — Shorthand for `--mode pm`, `--mode qa`.
- `--verify [feature]` — `--mode qa`, optionally scoped to one feature.
- `--auto-start` — Used with `--mode`: enters the mode and begins executing the work plan immediately without waiting for approval (e.g., `--mode engineer --auto-start`). Has no effect without `--mode`. The `--help` text for this flag MUST communicate the `--mode` dependency and include an example — e.g., "With --mode: begin executing immediately. Example: --mode engineer --auto-start. No effect without --mode." **Config-driven `auto_start`:** When `auto_start: true` is set in the config (not via CLI), it takes effect only when a mode is resolved — either from `default_mode` in config or from `.purlin_session.lock`. If no mode is resolved, `auto_start` is a no-op and the agent waits for mode selection.
- `--worktree` — Runs in an isolated git worktree (see worktree feature).

#### 2.2.3 Meta Flags

- `--help` — Show help and exit.
- `--no-save` — Suppresses persistence for all sticky flags in this invocation. The flag values still apply to the current session but are NOT written to `config.local.json`. Has no effect on ephemeral flags. Has no effect on first-run interactive selection (which always persists). Example: `--no-save --model haiku` uses Haiku this session without changing the stored default.

#### 2.2.4 Help Text Layout

The `--help` output MUST visually separate sticky and ephemeral flags so users understand persistence at a glance. Required layout:

```
Usage: ./pl-run.sh [OPTIONS]

Launch a Purlin agent session.

Saved preferences (written to .purlin/config.local.json):
  --model [id]         Set default model (opus, sonnet, haiku, or full ID).
                       Interactive if no value. Saves to config.
  --effort <level>     Set default effort level (high, medium). Saves to config.
  --yolo               Enable YOLO mode (skip all permission prompts). Saves to config.
  --no-yolo            Disable YOLO mode (restore permission prompts). Saves to config.
  --find-work <bool>   Set default work discovery (true/false). Saves to config.

  Use --no-save to apply any of the above for THIS SESSION ONLY
  without changing your saved config.
  Example: ./pl-run.sh --no-save --model haiku

Session options (this run only, never saved):
  --mode <mode>        Set starting mode (pm, engineer, qa).
  --auto-build         Start in Engineer mode with auto-start.
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
  ./pl-run.sh                           # Interactive session
  ./pl-run.sh --auto-build              # Engineer mode, auto-start
  ./pl-run.sh --model opus              # Use Opus (saved for next time)
  ./pl-run.sh --no-save --model haiku   # Use Haiku just this once
  ./pl-run.sh --yolo                    # YOLO mode on (saved)
  ./pl-run.sh --no-save --yolo          # YOLO just this session
  ./pl-run.sh --verify my_feature       # QA verify a specific feature
```

Requirements:
- Two visually distinct groups with headers: "Saved preferences" and "Session options."
- Every sticky flag description ends with "Saves to config."
- The `--no-save` callout appears inline immediately after the sticky group with an example — not buried at the bottom.
- `--no-save` appears both inline (contextual) and in the "Other" section (completeness).
- Examples include both sticky and `--no-save` variants side by side.
- The existing `sed`-based `# desc:` self-parsing mechanism MUST be replaced or extended to produce grouped output with headers. The implementation mechanism is left to Engineer mode.

### 2.3 First-Run Model Selection

- If `agents.purlin` is absent from `config.local.json`, the launcher MUST prompt interactively for model and effort level.
- The selection MUST be stored in `config.local.json` under `agents.purlin` via `resolve_config.py set_agent_config`. This persistence is NOT affected by `--no-save` — first-run interactive selection is explicitly establishing defaults, not overriding them.
- CLI sticky flags MUST always override stored config (and persist the override, unless `--no-save`).

### 2.4 Terminal Identity and Remote Control Name

The launcher MUST set the iTerm badge, terminal title, and remote control session name before launching Claude. These provide immediate visual context and enable remote session management.

#### 2.4.1 Initial Badge and Title

The launcher sets the badge and title using `set_agent_identity` from `tools/terminal/identity.sh`. The badge MUST include the current git branch to provide useful context immediately:

- **Badge format:** `<mode> (<branch>)` — e.g., `Purlin (main)`, `Engineer (feature-xyz)`.
- **Worktree override:** If running in a worktree (`.purlin_worktree_label` exists), the worktree label replaces the branch — e.g., `Engineer (W1)`.
- **Title format:** `<project> - <badge>` — e.g., `purlin - Purlin (main)`.

The branch is detected via `git rev-parse --abbrev-ref HEAD`. This badge is the user's first visual signal that the agent is starting. `/pl-resume` Step 6 updates the mode name but preserves the branch context — e.g., `Purlin (main)` becomes `PM (main)`, not bare `PM`.

#### 2.4.2 Remote Control Session Name

The launcher MUST set `--name` and `--remote-control` CLI flags on the `claude` invocation. This is the only opportunity to set the session name — it cannot be changed mid-session.

- **Format:** `<project> | <badge>` — e.g., `purlin | Purlin (main)`, `purlin | Engineer (W1)`.
- The session name persists for the lifetime of the session, even if the badge changes later.

#### 2.4.3 Session Overrides File

The launcher MUST write `.purlin/cache/session_overrides.json` with the resolved `find_work` and `auto_start` values before launching Claude. This file bridges ephemeral CLI flags (`--no-save --find-work false`, `--auto-start`) to the agent, which cannot read the launcher's shell variables.

- **Written:** After sticky flag persistence and validation, before launch.
- **Format:** `{"find_work": <bool>, "auto_start": <bool>}` — JSON with boolean values matching the launcher's resolved state.
- **Read by:** `/pl-resume` Step 4 (takes priority over `config.local.json`).
- **Lifetime:** Persists for the terminal session. The launcher's EXIT trap deletes it on session end. `/pl-resume` does NOT delete it (so it survives `/clear`).
- **Absent:** When `/pl-resume` is invoked outside a launcher session (e.g., user types it manually), the file does not exist and the agent falls back to `config.local.json`.

### 2.5 Session Message Encoding

- No `--mode`: `"Begin Purlin session."`
- `--auto-build`: `"Begin Purlin session. Enter Engineer mode. Run /pl-build."`
- `--verify <feature>`: `"Begin Purlin session. Enter QA mode. Run /pl-verify <feature>."`
- `--pm`: `"Begin Purlin session. Enter PM mode."`

### 2.6 Legacy Launcher Deprecation

- Old launchers (`pl-run.sh`, `pl-run.sh`, `pl-run.sh`, `pl-run.sh`) MUST print a visible deprecation warning before launching the agent.
- The warning MUST suggest `./pl-run.sh` with example flags.
- Old launchers MUST continue to function (instruction loading, config resolution, skill gates unchanged).

### 2.7 Config Schema

- `.purlin/config.json` and `purlin-config-sample/config.json` MUST include an `agents.purlin` section with fields: `model`, `effort`, `bypass_permissions`, `find_work`, `auto_start`, `default_mode`.
- `tools/config/resolve_config.py` MUST accept `"purlin"` as a valid role name.
- When resolving `purlin` config, if `agents.purlin` is absent, fall back to `agents.builder`.
- `--yolo`/`--no-yolo` map to the existing `bypass_permissions` field.

### 2.8 Startup Control Resolution

CLI flags that activate `auto_start` (`--auto-start`, `--auto-build`, `--auto-verify`) imply that work discovery is needed. When the saved config has `find_work: false`, the launcher MUST distinguish between an implied dependency and an explicit contradiction.

**Resolution rules (applied after CLI overrides, before validation):**

1. **Implied dependency:** `auto_start` activated via CLI, `find_work` is `false` from saved config, and `--find-work` was NOT passed on the CLI. The launcher MUST temporarily set `find_work=true` for the current session. This override is ephemeral — it MUST NOT be persisted to config and MUST NOT set the `PURLIN_FIND_WORK` variable (which would trigger sticky persistence). Rationale: convenience aliases like `--auto-verify` bundle intent; requiring the user to also pass `--find-work true` to counteract a saved preference defeats the purpose.

2. **Explicit contradiction:** `auto_start` activated via CLI AND `--find-work false` passed explicitly on the same CLI (including interactive selection via bare `--find-work`). The launcher MUST exit with error: `"Error: --find-work false conflicts with --auto-start. Cannot auto-start without work discovery."`

3. **Config-only conflict:** Both `auto_start: true` and `find_work: false` from config, no CLI override for either. The config is in an invalid state. The launcher MUST exit with the existing error message.

**Interactive selection edge case:** When `--find-work` is passed without a value (bare flag), the interactive menu sets `AGENT_FIND_WORK` to the user's choice. After the menu, the `__interactive__` sentinel MUST be replaced with the selected value (not cleared to empty). This preserves the "user explicitly chose this" signal so the dependency resolution treats it the same as `--find-work false`.

**Implementation:** After applying CLI overrides (Section 2.2) and before validation:
- If `PURLIN_AUTO_START` is set (CLI) AND `PURLIN_FIND_WORK` is empty (not from CLI) AND `AGENT_FIND_WORK` is `"false"` (from config): set `AGENT_FIND_WORK="true"`.
- If `PURLIN_AUTO_START` is set (CLI) AND `PURLIN_FIND_WORK` is `"false"` (explicit CLI or interactive selection): exit with the explicit-contradiction error.

**Post-resolution validation:** If `AGENT_FIND_WORK` is still `"false"` and `AGENT_AUTO_START` is `"true"`, exit with error (catches case 3).

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

#### Scenario: Help output separates sticky and ephemeral flags

    Given pl-run.sh exists
    When invoked with --help
    Then the output contains a "Saved preferences" section with --model, --effort, --yolo, --no-yolo, --find-work
    And the output contains a "Session options" section with --mode, --auto-build, --auto-verify, --pm, --qa, --verify, --auto-start, --worktree
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

    Given pl-run.sh is invoked with --model opus
    When the launcher resolves the model name
    Then AGENT_MODEL is set to "claude-opus-4-6"
    And config.local.json contains agents.purlin.model = "claude-opus-4-6"

#### Scenario: --yolo sets bypass_permissions true in config

    Given config.local.json has agents.purlin.bypass_permissions = false
    When pl-run.sh is invoked with --yolo
    Then --dangerously-skip-permissions is passed to Claude
    And config.local.json contains agents.purlin.bypass_permissions = true (boolean, not string)

#### Scenario: --no-yolo sets bypass_permissions false in config

    Given config.local.json has agents.purlin.bypass_permissions = true
    When pl-run.sh is invoked with --no-yolo
    Then --dangerously-skip-permissions is NOT passed to Claude
    And config.local.json contains agents.purlin.bypass_permissions = false (boolean, not string)

#### Scenario: --no-save prevents sticky flag persistence

    Given config.local.json has agents.purlin.model = "claude-opus-4-6"
    When pl-run.sh is invoked with --no-save --model haiku
    Then the session uses model "claude-haiku-4-5-20251001"
    And config.local.json still contains agents.purlin.model = "claude-opus-4-6"

#### Scenario: --no-save with --yolo does not persist bypass_permissions

    Given config.local.json has agents.purlin.bypass_permissions = false
    When pl-run.sh is invoked with --no-save --yolo
    Then --dangerously-skip-permissions is passed to Claude for this session
    And config.local.json still contains agents.purlin.bypass_permissions = false

#### Scenario: --find-work persists to config

    Given pl-run.sh is invoked with --find-work false
    When the launcher processes arguments
    Then config.local.json contains agents.purlin.find_work = false (boolean)

#### Scenario: Multiple sticky flags persist together

    Given pl-run.sh is invoked with --model sonnet --effort medium --yolo
    When the launcher processes arguments
    Then config.local.json contains agents.purlin.model = "claude-sonnet-4-6"
    And config.local.json contains agents.purlin.effort = "medium"
    And config.local.json contains agents.purlin.bypass_permissions = true

#### Scenario: Explicit contradiction exits with error

    Given config.local.json has agents.purlin.find_work = true
    When pl-run.sh is invoked with --find-work false --auto-start --mode engineer
    Then the launcher exits with error "Error: --find-work false conflicts with --auto-start. Cannot auto-start without work discovery."
    And config.local.json still contains agents.purlin.find_work = true (not modified)

#### Scenario: Auto-verify implies find_work when saved config has it false

    Given config.local.json has agents.purlin.find_work = false
    When pl-run.sh is invoked with --auto-verify
    Then AGENT_FIND_WORK is temporarily set to "true" for this session
    And config.local.json still contains agents.purlin.find_work = false (not modified)
    And the session launches successfully with find_work=true and auto_start=true

#### Scenario: Auto-build implies find_work when saved config has it false

    Given config.local.json has agents.purlin.find_work = false
    When pl-run.sh is invoked with --auto-build
    Then AGENT_FIND_WORK is temporarily set to "true" for this session
    And config.local.json still contains agents.purlin.find_work = false (not modified)
    And the session launches successfully with find_work=true and auto_start=true

#### Scenario: Config-only find_work/auto_start conflict exits with error

    Given config.local.json has agents.purlin.find_work = false and agents.purlin.auto_start = true
    When pl-run.sh is invoked with no CLI flags
    Then the launcher exits with error about find_work=false with auto_start=true being invalid

#### Scenario: Interactive --find-work selecting false with --auto-verify exits with error

    Given pl-run.sh is invoked with --find-work --auto-verify (bare --find-work triggers menu)
    When the user selects false in the interactive find-work menu
    Then the launcher exits with error "--find-work false conflicts with --auto-start"
    And the interactive selection is treated as an explicit user choice, not a config default

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

    Given pl-run.sh exists and is invoked
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
    Then the system prompt contains PURLIN_BASE.md content
    And the system prompt contains PURLIN_BASE.md content
    And the system prompt contains PURLIN_OVERRIDES.md content if file exists

#### Scenario: Help output includes yolo and no-save flags @auto

    Given pl-run.sh exists
    When invoked with --help
    Then the output contains "--yolo" and "--no-yolo" in the "Saved preferences" section
    And the output contains "--no-save" in the "Other" section
    And the output contains at least one --no-save example

## Regression Guidance
- Verify init.sh refresh does not delete old role-specific launchers
- Verify pl-run.sh handles missing PURLIN_BASE.md gracefully (during partial setup)
- Verify config.local.json is not corrupted by concurrent model selection writes
- Verify --worktree flag creates worktree directory under .purlin/worktrees/
- Verify sticky flag persistence uses correct JSON types (booleans for bypass_permissions/find_work, not strings)
- Verify --no-save does not suppress first-run interactive persistence
