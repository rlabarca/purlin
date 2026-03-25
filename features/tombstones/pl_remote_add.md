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

### 2.5 URL Prompt, Normalization, and Validation

- If `<url>` argument was provided, skip the prompt and validate directly.
- Otherwise, prompt: "Enter a git remote URL (SSH or HTTPS -- any git-compatible host). You can paste a browser URL too."
- If hosting hints were found (Section 2.4), they are already displayed above the prompt as part of the banner.
- Accept any valid git URL format: `git@host:user/repo.git`, `https://host/user/repo.git`, `ssh://...`, or local paths.
- **Browser URL normalization:** If the user pastes a browser URL (e.g., `https://bitbucket.org/team/repo/src/main/` or `https://github.com/user/repo/tree/main`), the skill MUST auto-normalize it to a proper git URL:
  1. Strip trailing path segments after the repo name (`/src/main/`, `/tree/main`, `/blob/...`, etc.).
  2. Append `.git` if not present.
  3. Convert to SSH format: `git@<host>:<owner>/<repo>.git`.
  4. Show the normalized URL and ask for confirmation: `"Normalized to: git@bitbucket.org:team/repo.git — use this? [Y/n]"`
  5. If declined, prompt for manual entry.

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
   - **Change URL of existing remote:** Display remotes as a numbered list. Prompt: "Which remote to update?" Default: `"origin"` if it exists, otherwise the first remote from `git remote`. Then prompt for new URL. Execute `git remote set-url <name> <new-url>`.
   - **Add additional remote:** Prompt for a new remote name (must not conflict with existing names) and URL. Execute `git remote add <name> <url>`.
4. Verify connectivity (Section 2.8).
5. Print success output (Section 2.9).

### 2.8 Connectivity Verification

- Run `git ls-remote <name>`.
- On success: proceed to success output.
- On failure:
  1. **Error classification:** Check stderr for auth indicators ("Permission denied", "publickey", "403", "authentication") vs. network indicators ("Could not resolve host", "Network is unreachable"). Tailor guidance accordingly.
  2. **SSH auth failure — automatic key setup (Section 2.8.1):** If the error indicates SSH auth failure and the URL is SSH format, proceed to the SSH key setup flow. The skill does the work — it does NOT print commands for the user to run.
  3. **HTTPS auth failure:** Suggest switching to SSH (offer to convert the URL) or setting up a credential helper. If the user wants SSH, convert the URL and proceed to SSH key setup (Section 2.8.1).
  4. **Network failure:** Offer the user a chance to correct the URL. If the user provides a corrected URL, execute `git remote set-url <name> <corrected-url>` and re-verify.
  5. **Rollback on decline:** If the user declines all correction/setup options:
     - If the remote was **newly added** (`git remote add`): remove it via `git remote remove <name>`.
     - If the remote **already existed** (`git remote set-url`): restore the previous URL via `git remote set-url <name> <old-url>`. The old URL MUST be captured before attempting set-url.
     - Exit with code 1.

### 2.8.1 SSH Key Setup Flow

When SSH authentication fails, the skill MUST handle the entire setup process. The user should only need to copy-paste one public key into their hosting provider's web UI.

**Step 1 — Check for existing keys:**
- Read `~/.ssh/` for existing key files (`id_ed25519`, `id_rsa`, `id_ecdsa`, and their `.pub` counterparts).
- If a suitable key exists, skip to Step 3.

**Step 2 — Generate a new key (if none found):**
- Run: `ssh-keygen -t ed25519 -C "<user.email from git config>" -f ~/.ssh/id_ed25519 -N ""`
- The skill runs this directly — do NOT ask the user to run it. The empty passphrase (`-N ""`) avoids interactive prompts. If the user wants a passphrase, they can add one later.
- If `~/.ssh/` does not exist, create it: `mkdir -p ~/.ssh && chmod 700 ~/.ssh`.

**Step 3 — Ensure the host is in known_hosts:**
- Run: `ssh-keyscan <host> >> ~/.ssh/known_hosts 2>/dev/null`
- This prevents the "authenticity of host" interactive prompt on first connection.

**Step 4 — Display the public key:**
- Read and display the contents of `~/.ssh/id_ed25519.pub` (or whichever key was found/generated).
- Print clear instructions with the hosting-provider-specific URL for adding SSH keys:
  - `github.com` → `https://github.com/settings/keys`
  - `bitbucket.org` → `https://bitbucket.org/account/settings/ssh-keys/`
  - `gitlab.com` → `https://gitlab.com/-/user_settings/ssh_keys`
  - Other hosts → `"Add this public key to your SSH keys on <host>"`
- Format: `"Copy this key and add it at <url>:\n\n<key contents>\n\nPress Enter when done."`

**Step 5 — Wait and re-verify:**
- After the user confirms, re-run `git ls-remote <name>`.
- On success: proceed to success output (Section 2.9).
- On failure: report the error and offer to retry or rollback.

**Constraints:**
- The skill MUST NOT ask the user to run terminal commands. It runs them directly.
- The skill MUST NOT overwrite existing SSH keys without asking.
- If `id_ed25519` already exists and auth still fails, the key may not be registered with the host. Skip to Step 4 (display the existing key for the user to add).

### 2.9 Success Output

Print a summary:

```
Remote configured:
  Name:   <name>
  URL:    <url>
  Status: Connected

Branch collaboration features are now available in the CDD dashboard.
```

### 2.10 Config Sync

After a successful add or set-url, check whether the configured remote name matches the `branch_collab.remote` value in `.purlin/config.json` (default: `"origin"`; fallback: `remote_collab.remote`).

- If the remote name matches the config value (or is `"origin"` and no config override exists): no action needed.
- If the remote name does NOT match and it is the **only** configured remote: prompt the user: "Remote `<name>` is not the default (`origin`). Should `/pl-remote-push` and `/pl-remote-pull` use `<name>` as the default remote? [Y/n]" If yes, write or update the `branch_collab.remote` field in `.purlin/config.json`.
- If there are multiple remotes: inform the user which remote push/pull will use (per config), and suggest updating config if they want to change the default.

This ensures the one-step setup promise holds: after `/pl-remote-add`, push and pull work without manual config editing.

### 2.11 FORBIDDEN Pattern Enforcement

- MUST NOT execute any push or pull operations. This is a configuration-only command.
- MUST NOT delete existing remotes unless rolling back a **newly added** remote after a failed connectivity check (Section 2.8 failure recovery only). For existing remotes where set-url was used, rollback restores the old URL -- never removes.
- User-provided remote names and URLs MUST be properly quoted when passed to git commands to prevent shell injection.

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

#### Scenario: pl-remote-add Reports Connectivity Failure And Classifies Error

    Given no git remotes are configured
    And the user provides a URL with an SSH auth failure
    When the remote is added via git remote add
    Then git ls-remote fails
    And the command suggests checking SSH keys or credentials
    And offers the user a chance to correct the URL

#### Scenario: pl-remote-add Rolls Back New Remote On Declined Correction

    Given no git remotes are configured
    And the user provides an unreachable URL
    When git ls-remote fails and the user declines to correct
    Then the command executes git remote remove to clean up the failed add
    And exits with code 1

#### Scenario: pl-remote-add Restores Old URL On Set-Url Failure

    Given a remote "origin" is configured with URL "git@github.com:user/old-repo.git"
    When /pl-remote-add git@bad-host:user/repo.git --name origin is invoked
    And git ls-remote fails and the user declines to correct
    Then the command restores the original URL "git@github.com:user/old-repo.git"
    And does not remove the remote

#### Scenario: pl-remote-add Normalizes Browser URL to SSH

    Given no git remotes are configured
    When /pl-remote-add https://bitbucket.org/team/repo/src/main/ is invoked
    Then the command normalizes to "git@bitbucket.org:team/repo.git"
    And asks the user to confirm the normalized URL
    When the user confirms
    Then git remote add origin git@bitbucket.org:team/repo.git is executed

#### Scenario: pl-remote-add Sets Up SSH Key On Auth Failure

    Given no git remotes are configured
    And no SSH key exists at ~/.ssh/id_ed25519
    When /pl-remote-add git@bitbucket.org:team/repo.git is invoked
    And git ls-remote fails with "Permission denied (publickey)"
    Then the command generates an SSH key via ssh-keygen (no user commands)
    And runs ssh-keyscan to add the host to known_hosts
    And displays the public key contents
    And prints the Bitbucket SSH key settings URL
    And waits for the user to confirm the key was added
    When the user confirms
    Then the command re-runs git ls-remote and succeeds

#### Scenario: pl-remote-add Uses Existing SSH Key When Available

    Given no git remotes are configured
    And ~/.ssh/id_ed25519.pub exists
    When /pl-remote-add git@github.com:user/repo.git is invoked
    And git ls-remote fails with "Permission denied (publickey)"
    Then the command does NOT generate a new key
    And displays the existing public key contents
    And prints the GitHub SSH key settings URL
    And waits for the user to confirm

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

#### Scenario: pl-remote-add Prompts Config Sync When Non-Origin Name Is Only Remote

    Given no git remotes are configured
    When /pl-remote-add git@github.com:user/repo.git --name upstream is invoked
    And connectivity verification succeeds
    Then the command prompts whether push/pull should use "upstream" as the default
    And if user confirms, branch_collab.remote is set to "upstream" in .purlin/config.json

#### Scenario: pl-remote-add Skips Config Sync When Name Is Origin

    Given no git remotes are configured
    When /pl-remote-add git@github.com:user/repo.git --name origin is invoked
    And connectivity verification succeeds
    Then the command does not prompt about config sync
    And .purlin/config.json is not modified

### QA Scenarios

None.
