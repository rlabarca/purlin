# Feature: Init New Project Mode

> Label: "Tool: Init New Project Mode"
> Category: "Install, Update & Scripts"
> Prerequisite: features/project_init.md
> Prerequisite: features/init_preflight_checks.md

## 1. Overview

The `--new <name>` flag for `tools/init.sh` creates a complete Purlin project from scratch in a single command. It creates the project directory, initializes git, adds Purlin as a submodule, runs the standard initialization, and auto-commits. This reduces the five-command project creation sequence (`git init`, `git submodule add`, `git submodule update`, `init.sh`, `git commit`) to one command.

---

## 2. Requirements

### 2.1 Flag Syntax

- `tools/init.sh` MUST accept `--new <name>` where `<name>` is the project directory name.
- `<name>` MUST be validated: allow alphanumeric characters, hyphens, and underscores only. Reject names containing spaces, dots, slashes, or other special characters with a clear error message listing the allowed characters.
- `--new` MUST be rejected when combined with `--quiet` (the narrative output is essential for first-time users).
- `--new` MUST be rejected if the script detects it is already inside a consumer project (the standalone-mode guard still applies).

### 2.2 Project Creation Sequence

- The script MUST create the directory `<name>` relative to the caller's current working directory.
- The script MUST run `git init` inside the new directory.
- The script MUST detect its own upstream remote URL from the Purlin repo's git config (`git remote get-url origin`) and use it for `git submodule add`.
- If the Purlin repo has no remote configured (local-only clone), the script MUST add the submodule using the absolute filesystem path to the Purlin repo.
- The script MUST run `git submodule update --init` inside the new project.
- After submodule setup, the script MUST execute the standard full-init flow by re-invoking itself from within the new project context.
- The script MUST auto-commit all staged files with the message "init purlin".

### 2.3 Error Handling

- If the target directory already exists, the script MUST print an error and exit without modifying anything.
- If `git submodule add` fails (e.g., network unreachable, auth failure), the script MUST remove the created directory and exit with a clear error message.
- If any step after directory creation fails, the script MUST remove the created directory (clean slate on failure).
- Preflight checks MUST run before any directory creation.

### 2.4 Post-Creation Output

- The script MUST print the absolute path of the created project.
- The script MUST print `cd <name>` as an explicit next step.
- The post-init narrative from init_preflight_checks MUST appear after the auto-commit.
- The output MUST NOT suggest `git commit` (it was already done automatically).

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Create new project successfully

    Given git and claude are installed
    And no directory named "my-app" exists in the current directory
    When the user runs init.sh --new my-app
    Then a directory "my-app" is created
    And "my-app/.git" exists (it is a git repository)
    And "my-app/purlin" is a git submodule with a .gitmodules entry
    And "my-app/.purlin/" exists with config.json
    And "my-app/pl-run-pm.sh" exists and is executable
    And "my-app/pl-run-architect.sh" exists and is executable
    And "my-app/pl-run-builder.sh" exists and is executable
    And "my-app/pl-run-qa.sh" exists and is executable
    And "my-app/features/" directory exists
    And the git log inside "my-app" shows an "init purlin" commit
    And the output includes "cd my-app" as a next step

#### Scenario: Directory already exists

    Given a directory named "my-app" exists in the current directory
    When the user runs init.sh --new my-app
    Then the output includes "already exists"
    And the script exits with a non-zero code
    And the existing directory is not modified

#### Scenario: Invalid project name with spaces

    Given the user runs init.sh --new "my app"
    Then the output explains the name is invalid
    And the output lists allowed characters (alphanumeric, hyphens, underscores)
    And the script exits with a non-zero code
    And no directory is created

#### Scenario: Invalid project name with dots

    Given the user runs init.sh --new "my.app"
    Then the output explains the name is invalid
    And the script exits with a non-zero code

#### Scenario: Remote URL detection from cloned Purlin repo

    Given the Purlin repo was cloned from a remote URL
    When the user runs init.sh --new my-app
    Then the submodule in my-app is added using the same remote URL
    And "my-app/.gitmodules" contains the detected remote URL

#### Scenario: Local filesystem path fallback when no remote

    Given the Purlin repo has no remote configured
    When the user runs init.sh --new my-app
    Then the submodule is added using the absolute filesystem path to the Purlin repo
    And "my-app/.gitmodules" contains a filesystem path

#### Scenario: Preflight runs before directory creation

    Given git is not installed
    When the user runs init.sh --new my-app
    Then the preflight check fails with install instructions
    And no "my-app" directory is created

#### Scenario: Cleanup on submodule add failure

    Given git is installed
    And the Purlin remote URL is unreachable
    When the user runs init.sh --new my-app
    Then the output includes an error about submodule setup
    And the "my-app" directory does not exist (cleaned up)
    And the script exits with a non-zero code

#### Scenario: Cleanup on init failure after submodule

    Given git is installed and the remote is reachable
    And the full-init flow fails for any reason after submodule setup
    When the user runs init.sh --new my-app
    Then the "my-app" directory does not exist (cleaned up)
    And the script exits with a non-zero code

#### Scenario: Auto-commit includes all init artifacts

    Given the new project is created successfully
    When checking the git status inside my-app
    Then the working tree is clean (nothing unstaged or untracked from init)
    And the commit includes .purlin/, .claude/, .gitignore, launchers, and pl-init.sh

#### Scenario: Output omits git commit instruction

    Given the new project is created successfully
    Then the post-init narrative does NOT include "git commit" as a next step
    And the narrative starts with "cd my-app"

### Manual Scenarios (Human Verification Required)

None.
