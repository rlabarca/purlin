/pl-remote-add -- Configure a git remote for this project.

```
/pl-remote-add [<url>] [--name <remote-name>]
```

**Owner: All roles**

No branch guard. No dirty check. This is a configuration-only command.

## Steps

### 0. Parse Arguments

Parse optional `<url>` and `--name <remote-name>` from the command invocation.

- If a positional argument is present that does not start with `--`, treat it as `<url>`.
- If `--name` is followed by a value, treat that value as `<remote-name>`.
- Both are optional. Missing values trigger interactive prompts in later steps.

### 1. Check Existing Remotes

Run `git remote -v`.

- If remotes exist, go to Step 6 (Mode 2).
- If no remotes exist, continue to Step 2 (Mode 1).

### 2. Help Banner (no URL argument only)

If no `<url>` was provided as an argument, print the following help banner:

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

If `<url>` was provided, skip this banner entirely and proceed to Step 4.

### 3. Hosting Hints Scan

Scan for hosting hints to help the user choose a URL:

1. **SSH config:** Check `~/.ssh/config` for configured hosts. Look for `Host` entries matching `github.com`, `gitlab.com`, `bitbucket.org`, or other known hosting providers.
2. **Git credential helpers:** Run `git config --global --get-regexp credential` to detect configured credential stores or helpers.
3. **Hosting CLIs:** Check for:
   - `gh` (GitHub CLI): `command -v gh`
   - `glab` (GitLab CLI): `command -v glab`

Present any findings as suggestions. Example output:

```
Detected hosting hints:
  - SSH config has github.com configured
  - GitHub CLI (gh) is available
```

Do NOT auto-select any option. The user chooses.

### 4. URL Prompt

If `<url>` was provided as an argument, use it directly and skip this prompt.

Otherwise, prompt the user:

```
Enter a git remote URL (SSH or HTTPS -- any git-compatible host):
```

Wait for the user to provide a URL.

### 5. Remote Name Prompt

If `--name <remote-name>` was provided, use it directly.

Otherwise, prompt with a default:

```
Remote name [origin]:
```

If the user provides an empty response or confirms the default, use `"origin"`.

### 6. Mode 2: Remote(s) Already Configured

This step is reached when `git remote -v` showed existing remotes in Step 1.

1. Display the current remotes:
   ```
   Existing remotes:
     <output of git remote -v>
   ```

2. If both `<url>` and `--name` were provided as arguments:
   - Check if the named remote already exists (`git remote get-url <name>` succeeds).
   - **Named remote exists:** Run `git remote set-url <name> <url>`. Proceed to Step 8.
   - **Named remote does not exist:** Run `git remote add <name> <url>`. Proceed to Step 8.

3. If arguments were not fully provided, present options:
   ```
   Options:
     1. Change URL of an existing remote
     2. Add a new additional remote
   ```
   - Option 1: Prompt for which remote to update and the new URL.
   - Option 2: Prompt for the new remote name and URL.

   Then proceed to Step 7.

### 7. Execute

Based on the resolved action from previous steps:

- **New remote:** `git remote add "<name>" "<url>"`
- **Existing remote URL change:** `git remote set-url "<name>" "<url>"`

All user-provided names and URLs MUST be properly quoted in the git commands.

### 8. Connectivity Verification

Run:
```
git ls-remote "<name>"
```

- **Success (exit code 0):** Proceed to Step 9.
- **Failure (non-zero exit code):** Classify the error:
  - **Authentication error** (output contains "Permission denied", "Authentication failed", "could not read Username", or similar): Report "Authentication failed. Check your SSH keys or credentials for this host."
  - **Network/DNS error** (output contains "Could not resolve hostname", "Connection refused", or similar): Report "Could not connect to remote host. Verify the URL is correct and the host is reachable."
  - **Other error:** Report the raw git error output.

  Then offer the user a chance to correct the URL:
  ```
  Would you like to enter a corrected URL? [Y/n]
  ```
  - **User provides corrected URL:** Update with `git remote set-url "<name>" "<corrected-url>"` and re-run connectivity check.
  - **User declines correction:** Rollback:
    - If this was a newly added remote (from `git remote add`): `git remote remove "<name>"`.
    - If this was a URL change (from `git remote set-url`): `git remote set-url "<name>" "<old-url>"` to restore the previous URL.

### 9. Success Output

Print:

```
Remote configured:
  Name:   <name>
  URL:    <url>
  Status: Connected

Branch collaboration features are now available in the CDD dashboard.
```

### 10. Config Sync

If the remote name is NOT `"origin"` AND this remote is the only configured remote (check with `git remote`):

1. Prompt whether to update `.purlin/config.json` to use this remote name as the default:
   ```
   The remote "<name>" is the only configured remote but is not named "origin".
   Update .purlin/config.json to set branch_collab.remote = "<name>"? [Y/n]
   ```

2. If the user confirms:
   - Read `.purlin/config.json`.
   - Set or create `branch_collab.remote` to `"<name>"`.
   - Write the updated config.

3. If the user declines, skip the config update.

If the remote name IS `"origin"`, skip this step entirely (no prompt, no config change needed since "origin" is the default).

## FORBIDDEN

- **MUST NOT** execute any push or pull operations (`git push`, `git pull`, `git fetch` beyond `ls-remote`).
- **MUST NOT** delete existing remotes (except rollback of a newly added remote on connectivity failure, or restoring a previous URL on set-url failure).
- **MUST** properly quote all user-provided names and URLs in git commands to prevent shell injection.
