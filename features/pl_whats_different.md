# Feature: /pl-whats-different Command

> Label: "Agent Skills: Common: /pl-whats-different What's Different"
> Category: "Agent Skills: Common"

[TODO]

## 1. Overview

The `/pl-whats-different` agent command generates a plain-English summary of what's different between local main and the remote collab branch. It is a standalone command usable by any role from the main checkout. When invoked with an active Purlin mode (PM, Engineer, or QA), it produces a **role-specific briefing** that answers what the reader specifically needs to care about, followed by the standard file-level digest.

This spec owns the full pipeline: the agent command interface, the extraction tool (`scripts/collab/extract_whats_different.py`), the generation script (`scripts/collab/generate_whats_different.sh`), and the digest output format.

---

## 2. Requirements

### 2.1 Main Branch Guard

- The command checks the current branch via `git rev-parse --abbrev-ref HEAD`.
- If the branch is not `main`, the command aborts with an error message indicating the current branch and instructing the user to run from main.

### 2.2 Session Guard

- The command reads `.purlin/runtime/active_branch`.
- If the file is absent or empty, the command aborts with a message directing the user to create or join a collaboration branch via `/pl-remote branch create <name>` or `/pl-remote branch join <name>`.
- The branch name is extracted from the file contents (single line, trimmed).

### 2.3 Config, Fetch, and Sync State

- The command reads the remote name from `.purlin/config.json`: check `branch_collab.remote` first, fall back to `remote_collab.remote`, default to `"origin"` if both absent.
- It fetches the remote collab branch: `git fetch <remote> <branch>`.
- It determines sync state (SAME, AHEAD, BEHIND, DIVERGED) via range queries.
- If SAME, the command prints an in-sync message and exits without generating.

### 2.4 Generation

- The command executes `scripts/collab/generate_whats_different.sh <branch>` with an optional `--role <mode>` parameter.
- When the agent has an active Purlin mode (PM, Engineer, or QA), it passes `--role <mode>` to produce a role-specific briefing prepended to the standard digest.
- When no mode is active, it runs without `--role` (standard digest only).
- The script runs the extraction tool and invokes the LLM to produce the digest.
- Output is written to `features/digests/whats-different.md`.

### 2.5 Output

- The command reads and displays the contents of `features/digests/whats-different.md` inline.

### 2.6 Role-Aware Briefing

When `--role` is provided, the output has two sections:

1. **Role briefing** — A plain-language summary of what matters to this role, with numbered IDs on each item.
2. **Standard digest** — The full file-level digest (Spec Changes / Code Changes / Purlin Changes), unchanged.

A horizontal rule separates the two sections.

The role briefing is LLM-only. If Claude CLI is unavailable, the command produces only the standard digest without a role briefing section.

### 2.7 Companion Staleness Signal

The extraction tool cross-references code changes against companion file updates to detect features where the engineer may have skipped documentation. This is a deterministic check — no LLM needed — included in every digest regardless of mode.

#### 2.7.1 Feature Inference from Code Changes

For each direction (local/collab), the extraction tool infers which features were touched by code changes using two heuristics:

1. **Commit scope parsing:** Purlin commits follow `mode(scope): message`. The scope field often contains one or more feature stems (comma-separated). The extraction tool parses commit subjects with the pattern `^\w+\(([^)]+)\):` and splits the captured group on `,` to extract feature stems.
2. **Test directory mapping:** Changed files under `tests/<stem>/` map to feature `features/<stem>.md`.

Both heuristics are best-effort. Features that cannot be inferred from either source are not flagged — no false positives from guessing.

#### 2.7.2 Cross-Reference Logic

For each inferred feature stem:

1. Check whether `features/<stem>.impl.md` exists on disk (not just in the diff — the companion may pre-exist without changes).
2. Check whether the companion appears in the changed companion files for this direction.
3. **Flag condition:** The feature had code changes, a companion file exists on disk, but the companion was NOT updated in this range. "Code changes" means changes to any tracked file outside `.purlin/` and `features/` directories (includes `tools/`, `dev/`, `.claude/commands/`, but excludes feature specs and runtime state). This means the engineer touched code for a feature that has a companion file but didn't record anything new in it.

Features without an existing companion file are not flagged — the companion mandate only applies when the engineer has already established one. New features that have never had a companion are a separate concern (handled by the pre-switch gate in §4.2 of PURLIN_BASE.md).

#### 2.7.3 Output

The extraction JSON includes a new `companion_staleness` field per direction:

```json
{
  "companion_staleness": [
    {
      "feature": "foo_bar.md",
      "companion": "foo_bar.impl.md",
      "code_files_changed": 3,
      "inferred_via": "commit_scope"
    }
  ]
}
```

The digest renders this as a **Companion Check** subsection (after Sync Check):

```
### Companion Check
- **foo_bar**: 3 code files changed, companion not updated — review for undocumented deviations
```

When empty, the subsection is omitted.

#### 2.7.4 Performance

No new git operations. The check uses data already collected by the extraction tool:
- Commit subjects (already parsed for lifecycle transitions)
- Changed file categories (already computed)
- One `glob` for existing companion files on disk (single filesystem call)

### 2.8 ID Drill-Down

After displaying the briefing, the agent is prepared for the user to reply with a numeric ID (e.g., "3", "#3", "tell me about 3"). When this happens:

1. The agent identifies the corresponding item from the most recent briefing.
2. Reads the relevant source files (feature spec, companion file, discovery sidecar, git diff).
3. Provides a detailed explanation in the same plain-language tone: what the original state was, what changed, the full context, and recommended next steps.

This is conversational — no script or endpoint is needed. The IDs make it easy for the user to request detail without typing file paths or feature names.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Exits When Branch Is Not Main

    Given the current branch is "feature/auth"
    When the agent runs /pl-whats-different
    Then the command aborts with an error containing "only valid from the main checkout"
    And no generation script is executed

#### Scenario: Exits When No Active Session

    Given the current branch is "main"
    And no file exists at .purlin/runtime/active_branch
    When the agent runs /pl-whats-different
    Then the command aborts with a message containing "No active collaboration branch"
    And no generation script is executed

#### Scenario: Prints In-Sync Message When SAME

    Given the current branch is "main"
    And an active branch "v0.6-sprint" is set
    And local main and origin/collab/v0.6-sprint are at the same commit
    When the agent runs /pl-whats-different
    Then the command prints a message containing "in sync"
    And no generation script is executed

#### Scenario: Generates and Displays Digest When BEHIND

    Given the current branch is "main"
    And an active branch "v0.6-sprint" is set
    And origin/collab/v0.6-sprint has 2 commits not in local main
    When the agent runs /pl-whats-different
    Then the generation script is executed with "v0.6-sprint" as argument
    And features/digests/whats-different.md is written to disk
    And the digest content is displayed inline

#### Scenario: End-to-End Generation via Agent Command

    Given the agent is on the main branch
    And an active branch exists in BEHIND state
    When the agent runs /pl-whats-different
    Then the generation script is executed with the active branch name as argument
    And features/digests/whats-different.md is written to disk
    And the digest content is displayed inline

#### Scenario: PM Mode Produces PM Briefing

    Given the current branch is "main"
    And an active branch "v0.6-sprint" is set in BEHIND state
    And the agent is in PM mode
    When the agent runs /pl-whats-different
    Then the generation script is executed with --role pm
    And the output begins with a "What's Different — PM Briefing" section
    And the briefing contains a "Decisions Waiting for You" section
    And the briefing contains a "What Was Built" section
    And each actionable item has a sequential numeric ID
    And the briefing ends with "Reply with an ID to learn more, or continue with your work."
    And the standard file-level digest follows below a horizontal rule

#### Scenario: Engineer Mode Produces Engineer Briefing

    Given the current branch is "main"
    And an active branch "v0.6-sprint" is set in BEHIND state
    And the agent is in Engineer mode
    When the agent runs /pl-whats-different
    Then the generation script is executed with --role engineer
    And the output begins with a "What's Different — Engineer Briefing" section
    And the briefing contains a "Specs Changed After You Finished" section if rework signals exist
    And the briefing contains a "Decisions Overruled" section if rejected deviations exist
    And each actionable item has a sequential numeric ID
    And the briefing ends with "Reply with an ID to learn more, or continue with your work."

#### Scenario: QA Mode Produces QA Briefing

    Given the current branch is "main"
    And an active branch "v0.6-sprint" is set in BEHIND state
    And the agent is in QA mode
    When the agent runs /pl-whats-different
    Then the generation script is executed with --role qa
    And the output begins with a "What's Different — QA Briefing" section
    And the briefing contains a "Ready for You to Verify" section if testing queue is non-empty
    And the briefing contains a "What the Engineer Already Tested" section
    And each actionable item has a sequential numeric ID
    And the briefing ends with "Reply with an ID to learn more, or continue with your work."

#### Scenario: No Mode Produces Standard Digest Only

    Given the current branch is "main"
    And an active branch "v0.6-sprint" is set in BEHIND state
    And the agent has no active Purlin mode
    When the agent runs /pl-whats-different
    Then the generation script is executed without --role
    And the output contains the standard file-level digest
    And no role briefing section is present

#### Scenario: Briefing Absent When Claude CLI Unavailable

    Given the current branch is "main"
    And an active branch "v0.6-sprint" is set in BEHIND state
    And the agent is in PM mode
    And Claude CLI is not available
    When the agent runs /pl-whats-different
    Then the output contains only the standard file-level digest
    And no role briefing section is present

#### Scenario: User Drills Down Into Briefing Item by ID

    Given the agent has displayed a PM briefing with items [1] through [4]
    When the user replies with "2"
    Then the agent reads the source files referenced by item [2]
    And provides a detailed plain-language explanation of that item
    And includes what changed, the original state, and recommended next steps

#### Scenario: Companion Staleness Flagged When Code Changed Without Companion Update

    Given the current branch is "main"
    And an active branch "v0.6-sprint" is set in BEHIND state
    And the collab branch has commits scoped to "auth_login" that modify code files
    And features/auth_login.impl.md exists on disk
    And features/auth_login.impl.md was NOT modified in the collab branch commits
    When the agent runs /pl-whats-different
    Then the digest contains a "Companion Check" subsection
    And the subsection flags "auth_login" with a count of changed code files
    And the message suggests reviewing for undocumented deviations

#### Scenario: No Companion Staleness When Companion Was Updated

    Given the current branch is "main"
    And an active branch "v0.6-sprint" is set in BEHIND state
    And the collab branch has commits scoped to "auth_login" that modify code files
    And features/auth_login.impl.md was also modified in the collab branch commits
    When the agent runs /pl-whats-different
    Then the digest does not contain a "Companion Check" subsection for "auth_login"

#### Scenario: No Companion Staleness When No Companion Exists

    Given the current branch is "main"
    And an active branch "v0.6-sprint" is set in BEHIND state
    And the collab branch has commits scoped to "new_feature" that modify code files
    And features/new_feature.impl.md does NOT exist on disk
    When the agent runs /pl-whats-different
    Then the digest does not flag "new_feature" in a Companion Check subsection

#### Scenario: Feature Inferred From Test Directory Change

    Given the current branch is "main"
    And an active branch "v0.6-sprint" is set in BEHIND state
    And the collab branch modifies files under tests/auth_login/
    And features/auth_login.impl.md exists on disk but was not modified
    When the agent runs /pl-whats-different
    Then the digest flags "auth_login" in the Companion Check subsection
    And the inferred_via field is "test_directory"

### Manual Scenarios (Human Verification Required)

None
