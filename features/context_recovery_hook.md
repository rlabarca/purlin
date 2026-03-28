# Feature: Context Recovery After Compaction

> Label: "Tool: Context Recovery Hook"
> Category: "Install, Update & Scripts"
> Prerequisite: features/project_init.md

[TODO]

## 1. Overview

Ensures that role-restricted Purlin agents recover their identity and write-access boundaries after Claude Code context compaction. The primary mechanism is a `compact` matcher on the `SessionStart` hook that echoes role guard rails and a `purlin:resume` directive. A project-root `CLAUDE.md` provides defense-in-depth (always in context, survives all compression). As cleanup, the unused `.purlin/runtime/agent_role` file write is removed from the `purlin:start` skill.

---

## 2. Requirements

### 2.1 Compact Hook (This Repository)

- `.claude/settings.json` MUST contain a `SessionStart` hook entry with `"matcher": "compact"` alongside the existing `"matcher": "clear"` entry.
- The compact hook command MUST echo a message containing: (a) that context was compacted, (b) that this project uses role-restricted Purlin agents, (c) the role boundary summary (PM never write code, Engineer never writes specs, QA never writes app code), and (d) a directive to run `/pl-resume` immediately.

### 2.2 Compact Hook (Consumer Projects via init.sh)

- `install_session_hook()` in `tools/init.sh` MUST install both a `"matcher": "clear"` and a `"matcher": "compact"` entry in `hooks.SessionStart`.
- The merge strategy for the compact matcher MUST follow the same idempotent pattern as the clear matcher: if an entry with `"matcher": "compact"` already exists, leave it unchanged.
- Existing hooks and settings in `.claude/settings.json` MUST NOT be modified or removed.
- The result MUST be validated as valid JSON before writing.

### 2.3 CLAUDE.md Template (Consumer Projects via init.sh)

- A new function `install_claude_md()` MUST be added to `tools/init.sh`.
- The function reads content from `purlin-config-sample/CLAUDE.md.purlin` template.
- Content is wrapped in `<!-- purlin:start -->` / `<!-- purlin:end -->` markers.
- If no `CLAUDE.md` exists at the project root: create it with the marked block.
- If `CLAUDE.md` exists with markers: replace content between markers (preserving user content outside markers).
- If `CLAUDE.md` exists without markers: append the marked block.
- `install_claude_md()` MUST run on both full init AND refresh (so `pl-update-purlin` propagates updates).
- `CLAUDE.md` MUST be staged in the post-init `git add` calls.

### 2.4 CLAUDE.md.purlin Template

- A template file MUST be created at `purlin-config-sample/CLAUDE.md.purlin`.
- The template MUST contain: project identification (Purlin agentic workflow), role boundary summary for all four roles (PM, Engineer, QA, PM), a context recovery directive (run `/pl-resume` if role instructions are missing), and a pointer to `/pl-help`.
- The template MUST NOT contain the `<!-- purlin:start/end -->` markers (those are added by `install_claude_md()`).

### 2.5 agent_role File Removal

- The `purlin:start` skill MUST no longer write `$AGENT_ROLE` to `.purlin/runtime/agent_role`.
- The `generate_launcher()` function in `tools/init.sh` (if it contains agent_role write logic) MUST also be updated to remove the line.
- The `AGENT_ROLE` environment variable export MUST remain unchanged -- it is actively used by config resolution.

### 2.6 Test Scenarios for init.sh

- `tools/test_init.sh` MUST include test scenarios for:
  - Full init creates both `clear` and `compact` hooks in `.claude/settings.json`.
  - Compact hook is idempotent on refresh (not duplicated).
  - `install_claude_md()` creates `CLAUDE.md` on fresh init.
  - `install_claude_md()` replaces marked block when markers exist.
  - `install_claude_md()` appends marked block when no markers exist.
  - `install_claude_md()` preserves user content outside markers.
  - `CLAUDE.md` update is idempotent on refresh.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Compact Hook Present in This Repository

    Given the Purlin repository .claude/settings.json exists
    When inspecting hooks.SessionStart
    Then an entry with matcher "compact" exists
    And the hook command echoes role guard rails and a /pl-resume directive
    And an entry with matcher "clear" also exists (unchanged)

#### Scenario: Consumer Full Init Installs Compact Hook

    Given Purlin is added as a submodule at "purlin/"
    And no .claude/settings.json exists at the project root
    When the user runs "purlin/tools/init.sh"
    Then .claude/settings.json contains a SessionStart hook with matcher "clear"
    And .claude/settings.json contains a SessionStart hook with matcher "compact"
    And the compact hook echoes role guard rails and a /pl-resume directive

#### Scenario: Compact Hook Idempotent on Refresh

    Given .purlin/ already exists at the project root
    And .claude/settings.json already contains SessionStart hooks for both "clear" and "compact"
    When the user runs "purlin/tools/init.sh"
    Then .claude/settings.json contains exactly one entry with matcher "compact" (not duplicated)

#### Scenario: Compact Hook Merges with Existing Hooks

    Given .purlin/ already exists at the project root
    And .claude/settings.json contains a SessionStart hook with matcher "custom"
    When the user runs "purlin/tools/init.sh"
    Then .claude/settings.json contains hooks for "custom", "clear", and "compact"
    And the existing "custom" hook is unchanged

#### Scenario: Full Init Creates CLAUDE.md via Template

    Given Purlin is added as a submodule at "purlin/"
    And no CLAUDE.md exists at the project root
    And purlin-config-sample/CLAUDE.md.purlin exists in the submodule
    When the user runs "purlin/tools/init.sh"
    Then CLAUDE.md exists at the project root
    And CLAUDE.md contains "<!-- purlin:start -->" and "<!-- purlin:end -->" markers
    And the content between markers matches the template
    And CLAUDE.md contains role boundary text for all four roles

#### Scenario: CLAUDE.md Replaces Marked Block on Refresh

    Given .purlin/ already exists at the project root
    And CLAUDE.md exists with purlin markers containing outdated content
    And the user has added custom content outside the markers
    When the user runs "purlin/tools/init.sh"
    Then the content between purlin markers is replaced with the current template
    And the user's custom content outside markers is preserved

#### Scenario: CLAUDE.md Appends Block When No Markers Exist

    Given .purlin/ already exists at the project root
    And CLAUDE.md exists with user-written content but no purlin markers
    When the user runs "purlin/tools/init.sh"
    Then the original CLAUDE.md content is preserved
    And a purlin marked block is appended at the end

#### Scenario: CLAUDE.md Installation Is Idempotent

    Given .purlin/ already exists at the project root
    And CLAUDE.md exists with current purlin markers and no other content
    When the user runs "purlin/tools/init.sh" twice
    Then CLAUDE.md is unchanged after the second run (no duplicate markers)

#### Scenario: CLAUDE.md Is Staged in Post-Init Git Add

    Given Purlin is added as a submodule at "purlin/"
    And no .purlin/ directory exists at the project root
    When the user runs "purlin/tools/init.sh"
    Then CLAUDE.md appears in the git staging area

#### Scenario: purlin:start No Longer Writes agent_role

    Given the purlin:start skill exists
    When inspecting the session initialization logic
    Then it does not write to .purlin/runtime/agent_role
    And AGENT_ROLE is still exported as an environment variable

#### Scenario: Generated Launchers Omit agent_role Write

    Given Purlin is added as a submodule at "purlin/"
    And no .purlin/ directory exists at the project root
    When the user runs "purlin/tools/init.sh"
    Then generated launcher scripts at the project root do not write to .purlin/runtime/agent_role
    And each generated launcher exports AGENT_ROLE

### Manual Scenarios (Human Verification Required)

None.
