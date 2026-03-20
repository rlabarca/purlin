# Feature: Submodule Command Path Resolution

> Label: "Tool: Submodule Command Path Resolution"
> Category: "Install, Update & Scripts"
> Prerequisite: features/policy_critic.md

## 1. Overview

When Purlin is consumed as a git submodule, command files (`.claude/commands/*.md`) reference `tools/cdd/status.sh`, `tools/critic/run.sh`, and similar paths that do not exist at the consumer project root. The correct path is `<tools_root>/cdd/status.sh` where `tools_root` is read from `.purlin/config.json` (default: `tools`). This feature updates all command files to use `{tools_root}/` notation with an explicit resolution step, matching the pattern already established in `pl-spec-code-audit.md` and `pl-cdd.md`.

---

## 2. Requirements

### 2.1 Command File Path Resolution

- Every `.claude/commands/pl-*.md` file that references `tools/` subdirectories MUST use `{tools_root}/` notation instead of hardcoded `tools/` paths.
- Each command file that references tool paths MUST include a resolution preamble: read `.purlin/config.json`, extract `tools_root` (default: `"tools"`), resolve to absolute path, and substitute into all `{tools_root}/` references.
- The resolution preamble MUST match the pattern already used in `pl-spec-code-audit.md` and `pl-cdd.md` (read config, extract key, set variable).

### 2.2 Specific Path Conversions

- `tools/cdd/` references become `{tools_root}/cdd/`
- `tools/critic/` references become `{tools_root}/critic/`
- `tools/release/` references become `{tools_root}/release/`
- `tools/delivery/` references become `{tools_root}/delivery/`
- `tools/test_support/` references become `{tools_root}/test_support/`
- `tools/feature_templates/` references become `{tools_root}/feature_templates/`
- `tools/collab/` references become `{tools_root}/collab/`

### 2.3 Resume Command Update

- `/pl-resume` Step 5 MUST use `{tools_root}/cdd/status.sh --startup <role>` instead of the hardcoded `tools/cdd/status.sh --startup <role>`. The resolution step reads `tools_root` from `.purlin/config.json` (default: `"tools"`).

### 2.4 Build Command Web Test Gate

- `/pl-build` Step 4 (Status Tag Commit) MUST include a pre-check: if the feature has `> Web Test:` or `> AFT Web:` metadata, confirm `/pl-web-test` passed with zero BUG/DRIFT verdicts this session before proceeding with the status tag commit. If the feature has `## Visual Specification` but no web test metadata, confirm a DISCOVERY has been logged in the companion file.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Command Files Use tools_root Notation

    Given any `.claude/commands/pl-*.md` file
    When it references a tool subdirectory path
    Then the path uses `{tools_root}/` notation instead of hardcoded `tools/`
    And the file includes a tools_root resolution step or defers to the calling context's resolution

#### Scenario: Resume Command Resolves tools_root

    Given the `/pl-resume` command is invoked in a consumer project with `tools_root: "purlin/tools"`
    When Step 5 runs the startup briefing
    Then the command resolves to `purlin/tools/cdd/status.sh --startup <role>`
    And the startup briefing succeeds

#### Scenario: Build Command Enforces Web Test Gate

    Given a feature with `> Web Test: http://localhost:9086` metadata
    When the Builder reaches Step 4 (Status Tag Commit) in `/pl-build`
    Then the Builder verifies `/pl-web-test` passed this session before proceeding
    And the status tag commit is blocked if web test has not been run

#### Scenario: Build Command Flags Missing Web Test Metadata

    Given a feature with `## Visual Specification` but no `> Web Test:` metadata
    When the Builder reaches Step 4 (Status Tag Commit) in `/pl-build`
    Then the Builder verifies a DISCOVERY about missing web test URL has been logged
    And the status tag commit is blocked until the DISCOVERY is recorded

### Manual Scenarios (Human Verification Required)

None.
