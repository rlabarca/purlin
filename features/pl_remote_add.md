# Feature: Remote Add

> Label: "/pl-remote-add Remote Add"
> Category: "Agent Skills"
> Prerequisite: features/policy_branch_collab.md

[TODO]

## 1. Overview

The `/pl-remote-add` skill configures a git remote for the project. It serves as the single entry point for adding a new remote or changing an existing remote's URL. Unlike `/pl-remote-push` and `/pl-remote-pull`, it does not perform any branch operations, dirty checks, or branch guards -- it operates purely on git remote configuration. When no remote exists, it provides a guided setup with a help banner showing supported URL formats and hosting-provider hints. When a remote already exists, it displays the current remote(s) and offers to change the URL or add an additional remote. Both `/pl-remote-push` and `/pl-remote-pull` direct the user to this command when no remote is configured.

---

## 2. Requirements

### 2.1 Invocation Syntax

```
/pl-remote-add [<url>] [--name <remote-name>]
```

- `<url>` (optional): If provided, skips the help banner and URL prompt and uses this value directly.
- `--name <remote-name>` (optional): If provided, skips the name prompt and uses this value. Default: `"origin"`.
- Owner: All roles.
- No branch guard. No dirty check. No working tree inspection. This is a configuration-only command.

### 2.2 Help Banner (No Arguments, No Remotes)

When invoked without a `<url>` argument and no git remotes are configured, print a help banner before prompting:

```
/pl-remote-add -- Configure a git remote for this project

This connects your project to a remote repository so you can
use Branch Collaboration in the CDD dashboard.

Supported URL formats:
  git@github.com:user/repo.git     (SSH)
  https://github.com/user/repo.git (HTTPS)
  ssh://git@host/path/repo.git     (SSH URL)
  /path/to/bare/repo.git           (local)
```

If hosting hints are detected (Section 2.4), append them below the format list. When a `<url>` argument IS provided, skip the banner entirely.

### 2.3 Mode 1: No Remotes Configured (Guided Setup)

When `git remote -v` returns empty:

1. If no `<url>` argument was provided, print the help banner (Section 2.2) and run the hosting hints scan (Section 2.4).
2. Prompt for URL (Section 2.5) -- or use the `<url>` argument if provided.
3. Prompt for remote name (Section 2.6) -- or use the `--name` argument if provided.
4. Execute `git remote add <name> <url>` (Section 2.7).
5. Verify connectivity (Section 2.8).
6. Print success output (Section 2.9).

### 2.4 Hosting Hints Scan

Scan for hosting-provider hints that may help the user identify available remotes:

- Check `~/.ssh/config` for configured hosts (e.g., `github.com`, `gitlab.com`, `bitbucket.org`).
- Check git credential helpers via `git config --global --get-regexp credential`.
- Check for hosting CLIs: `gh` (GitHub), `glab` (GitLab).

Present findings as informational suggestions (e.g., "Detected: github.com (SSH key)"). Do not auto-select any host.

### 2.5 URL Prompt and Validation

- If `<url>` argument was provided, skip the prompt and validate directly.
- Otherwise, prompt: "Enter a git remote URL (SSH or HTTPS -- any git-compatible host):"
- If hosting hints were found (Section 2.4), they are already displayed above the prompt as part of the banner.
- Accept any valid git URL format: `git@host:user/repo.git`, `https://host/user/repo.git`, `ssh://...`, or local paths.

### 2.6 Remote Name Prompt

- If `--name` argument was provided, skip the prompt.
- Otherwise, prompt for the remote name with default `"origin"`.

### 2.7 Mode 2: Remote(s) Already Configured (Change or Add)

When `git remote -v` returns one or more remotes:

1. Display current remote(s): name and URL for each configured remote.
2. If both `<url>` and `--name` arguments are provided:
   - If the named remote already exists: execute `git remote set-url <name> <url>`.
   - If the named remote does not exist: execute `git remote add <name> <url>`.
3. If arguments are not provided, present options:
   - **Change URL of existing remote:** Ask which remote to update (default: the first or only remote), then prompt for new URL. Execute `git remote set-url <name> <new-url>`.
   - **Add additional remote:** Prompt for a new remote name (must not conflict with existing names) and URL. Execute `git remote add <name> <url>`.
4. Verify connectivity (Section 2.8).
5. Print success output (Section 2.9).

### 2.8 Connectivity Verification

- Run `git ls-remote <name>`.
- On success: proceed to success output.
- On failure: report the error and offer the user a chance to correct the URL. If the user provides a corrected URL, execute `git remote set-url <name> <corrected-url>` and re-verify. If the user declines to correct, remove the just-added remote (`git remote remove <name>`) and exit with code 1.

### 2.9 Success Output

Print a summary:

```
Remote configured:
  Name:   <name>
  URL:    <url>
  Status: Connected

Branch collaboration features are now available in the CDD dashboard.
```

### 2.10 FORBIDDEN Pattern Enforcement

- MUST NOT execute any push or pull operations. This is a configuration-only command.
- MUST NOT delete existing remotes unless rolling back a failed add (Section 2.8 failure recovery only).
- User-provided remote names and URLs MUST be validated against shell injection before passing to git commands.

---

## 3. Scenarios

### Unit Tests

#### Scenario: pl-remote-add Prints Help Banner When No Args And No Remote

    Given no git remotes are configured
    When /pl-remote-add is invoked with no arguments
    Then the command prints a help banner containing "Configure a git remote"
    And the banner lists supported URL formats including SSH and HTTPS examples
    And the command prompts for a git remote URL

#### Scenario: pl-remote-add Guides Setup When No Remote Exists

    Given no git remotes are configured
    And the user provides URL "git@github.com:user/repo.git" when prompted
    And the user accepts the default remote name "origin"
    When /pl-remote-add completes the guided setup
    Then git remote add origin git@github.com:user/repo.git is executed
    And git ls-remote origin is executed to verify connectivity
    And the command prints "Remote configured" with name "origin" and the URL

#### Scenario: pl-remote-add Shows Hosting Hints When Available

    Given no git remotes are configured
    And ~/.ssh/config contains a Host entry for github.com
    When /pl-remote-add is invoked with no arguments
    Then the command displays "Detected: github.com (SSH key)" as an informational hint
    And does not auto-select any host

#### Scenario: pl-remote-add Skips Banner When URL Argument Provided

    Given no git remotes are configured
    When /pl-remote-add git@github.com:user/repo.git is invoked
    Then the command does not print the help banner
    And prompts for remote name (default "origin")
    And executes git remote add with the provided URL

#### Scenario: pl-remote-add Accepts Both URL And Name Arguments

    Given no git remotes are configured
    When /pl-remote-add git@github.com:user/repo.git --name upstream is invoked
    Then the command skips both prompts
    And executes git remote add upstream git@github.com:user/repo.git
    And verifies connectivity via git ls-remote upstream

#### Scenario: pl-remote-add Shows Existing Remotes When Remote Already Configured

    Given a remote "origin" is configured with URL "git@github.com:user/repo.git"
    When /pl-remote-add is invoked with no arguments
    Then the command displays the existing remote name "origin" and its URL
    And offers to change the URL or add an additional remote

#### Scenario: pl-remote-add Changes URL When Named Remote Exists And URL Provided

    Given a remote "origin" is configured with URL "git@github.com:user/old-repo.git"
    When /pl-remote-add git@github.com:user/new-repo.git --name origin is invoked
    Then the command executes git remote set-url origin git@github.com:user/new-repo.git
    And verifies connectivity via git ls-remote origin
    And prints "Remote configured" with the new URL

#### Scenario: pl-remote-add Adds New Remote When Named Remote Does Not Exist

    Given a remote "origin" is configured
    When /pl-remote-add git@github.com:user/fork.git --name upstream is invoked
    Then the command executes git remote add upstream git@github.com:user/fork.git
    And verifies connectivity via git ls-remote upstream

#### Scenario: pl-remote-add Reports Connectivity Failure

    Given no git remotes are configured
    And the user provides an unreachable URL
    When the remote is added via git remote add
    Then git ls-remote fails
    And the command reports the connectivity error
    And offers the user a chance to correct the URL

#### Scenario: pl-remote-add Does Not Require Branch Guard

    Given an active branch "feature/auth" in .purlin/runtime/active_branch
    And the current branch is main
    When /pl-remote-add is invoked
    Then the command does not check the current branch
    And proceeds with remote configuration

#### Scenario: pl-remote-add Does Not Require Clean Working Tree

    Given the working tree has uncommitted changes
    When /pl-remote-add is invoked
    Then the command does not check working tree status
    And proceeds with remote configuration

#### Scenario: pl-remote-add Does Not Push Or Pull

    Given no git remotes are configured
    When /pl-remote-add is invoked and the remote is successfully added
    Then no git push or git pull is executed
    And the command exits after printing the success summary

### QA Scenarios

None.
