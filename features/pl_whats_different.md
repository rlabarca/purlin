# Feature: /pl-whats-different Command

> Label: "Agent Skills: /pl-whats-different"
> Category: "Agent Skills"
> Prerequisite: features/collab_whats_different.md

[TODO]

## 1. Overview

The `/pl-whats-different` agent command generates a plain-English summary of what's different between local main and the remote collab branch. It is a standalone command usable by any role from the main checkout. The generation pipeline (extraction tool, LLM synthesis, output file) is defined in `features/collab_whats_different.md`; this spec covers only the agent command interface.

---

## 2. Requirements

### 2.1 Main Branch Guard

- The command checks the current branch via `git rev-parse --abbrev-ref HEAD`.
- If the branch is not `main`, the command aborts with an error message indicating the current branch and instructing the user to run from main.

### 2.2 Session Guard

- The command reads `.purlin/runtime/active_remote_session`.
- If the file is absent or empty, the command aborts with a message directing the user to start or join a remote collab session via the CDD dashboard.
- The session name is extracted from the file contents (single line, trimmed).

### 2.3 Config, Fetch, and Sync State

- The command reads `remote_collab.remote` from `.purlin/config.json`, defaulting to `"origin"`.
- It fetches the remote collab branch: `git fetch <remote> collab/<session>`.
- It determines sync state (SAME, AHEAD, BEHIND, DIVERGED) via range queries.
- If SAME, the command prints an in-sync message and exits without generating.

### 2.4 Generation

- The command executes `tools/collab/generate_whats_different.sh <session>`.
- The script runs the extraction tool and invokes the LLM to produce the digest.
- Output is written to `features/digests/whats-different.md`.

### 2.5 Output

- The command reads and displays the contents of `features/digests/whats-different.md` inline.
- A note is appended: "This summary is also available via the 'What's Different?' button in the CDD dashboard."

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Exits When Branch Is Not Main

    Given the current branch is "isolated/feat1"
    When the agent runs /pl-whats-different
    Then the command aborts with an error containing "only valid from the main checkout"
    And no generation script is executed

#### Scenario: Exits When No Active Session

    Given the current branch is "main"
    And no file exists at .purlin/runtime/active_remote_session
    When the agent runs /pl-whats-different
    Then the command aborts with a message containing "No active remote session"
    And no generation script is executed

#### Scenario: Prints In-Sync Message When SAME

    Given the current branch is "main"
    And an active session "v0.6-sprint" is set
    And local main and origin/collab/v0.6-sprint are at the same commit
    When the agent runs /pl-whats-different
    Then the command prints a message containing "in sync"
    And no generation script is executed

#### Scenario: Generates and Displays Digest When BEHIND

    Given the current branch is "main"
    And an active session "v0.6-sprint" is set
    And origin/collab/v0.6-sprint has 2 commits not in local main
    When the agent runs /pl-whats-different
    Then the generation script is executed with "v0.6-sprint" as argument
    And features/digests/whats-different.md is written to disk
    And the digest content is displayed inline

### Manual Scenarios (Human Verification Required)

#### Scenario: End-to-End Generation via Agent Command

    Given the agent is on the main branch
    And an active session exists in BEHIND state
    When the agent runs /pl-whats-different
    Then the generated digest is displayed inline
    And features/digests/whats-different.md is written to disk
