# Feature: Agentic Toolbox — Community Tool Lifecycle

> Label: "Tool: Toolbox Community Lifecycle"
> Category: "Install, Update & Scripts"
> Owner: PM
> Prerequisite: toolbox_core.md

## 1. Overview

This feature defines the lifecycle for community tools in the Agentic Toolbox: downloading from git repos (`add`), updating from upstream (`pull`), sharing project tools to repos (`push`), and editing community tools locally (`edit`). Community tools bridge the gap between framework-distributed tools and project-specific tools by enabling sharing across projects via git repositories.

Each community tool lives in its own git repository with a `tool.json` at the root.

---

## 2. Requirements

### 2.1 Community Tool Repository Format

A community tool git repository MUST contain:
*   `tool.json` at the repository root, conforming to the tool schema defined in `toolbox_core.md` Section 2.1.
*   Required fields in `tool.json`: `id`, `friendly_name`, `description`.
*   Optional: `README.md` at repository root for documentation.

The `id` field in `tool.json` SHOULD use the `community.` prefix. If the prefix is absent, the toolbox auto-prefixes `community.` during `add`.

No other files are required or expected. Supporting files (scripts, templates) MAY be included alongside `tool.json`.

### 2.2 Add (`purlin:toolbox add <git-url>`)

1. Clone the repository to a temporary directory.
2. Validate `tool.json` exists at the repository root. If absent: error with message explaining the expected format.
3. Parse `tool.json`. Validate required fields (`id`, `friendly_name`, `description`). If invalid: error listing missing fields.
4. Normalize the tool ID: if `id` does not start with `community.`, auto-prefix it. Inform the user of the rename.
5. Check for ID collision against all three registries. If collision: error naming the conflicting tool and its category.
6. Create directory `.purlin/toolbox/community/<tool_id>/`.
7. Copy `tool.json` (and any supporting files from the repo) to the community directory.
8. Register the tool in `.purlin/toolbox/community_tools.json` with:
    *   `id`: the normalized ID
    *   `source_dir`: relative path `community/<tool_id>`
    *   `version`: from `tool.json` field `version`, or `"0.0.0"` if absent
    *   `source_repo`: the git URL provided by the user
    *   `author`: from `tool.json` field `metadata.author`, or from `git config user.email` if absent
    *   `last_pull_sha`: HEAD SHA of the cloned repository
9. Clean up temporary directory.
10. Confirm: `"Added community tool '<id>' from <git-url>. Version: <version>."`

**Error recovery:** If any step after step 6 fails, clean up the partially-created community directory and do not update the registry.

### 2.3 Pull (`purlin:toolbox pull [tool]`)

**Single tool:** `purlin:toolbox pull community.deploy_vercel`
**All tools:** `purlin:toolbox pull`

For each community tool being updated:

1. Read `source_repo` and `last_pull_sha` from `community_tools.json`.
2. Fetch remote HEAD: `git ls-remote <source_repo> HEAD`. If unreachable: warn and skip this tool (do not abort all updates).
3. Compare remote HEAD SHA against `last_pull_sha`. If identical: report `"<id>: already up to date."` and skip.
4. Clone to temporary directory, check out HEAD.
5. **Local edit detection:** Compare the current local `tool.json` content (in `.purlin/toolbox/community/<tool_id>/tool.json`) against the content at `last_pull_sha` (stored per-tool in `community_tools.json`). To retrieve the original content: clone the source repo to a temp directory and `git show <last_pull_sha>:tool.json`. If they differ, the user has made local edits.
6. **If no local edits:** Auto-update. Copy new `tool.json` (and any supporting files) to the community directory. Update `last_pull_sha` and `version` in registry.
7. **If local edits detected:** Show the diff between local and upstream. Offer three options:
    *   **Accept upstream** — overwrites local changes with upstream version.
    *   **Keep local** — skips this update. `last_pull_sha` is NOT updated (conflict persists for next pull).
    *   **Show diff** — display a three-way comparison (last-pull version, local version, upstream version) so the user can decide.
8. Clean up temporary directory.
9. Report summary: `"Updated N tools. Skipped M (up to date). Conflicts: K."`

### 2.4 Push (`purlin:toolbox push <tool> [git-url]`)

**Community tool (update existing repo):** `purlin:toolbox push community.deploy_vercel`
**Project tool (promote to community):** `purlin:toolbox push my_audit git@github.com:user/purlin-tool-my-audit.git`

1. Resolve tool name via fuzzy matching.
2. **If community tool:**
    *   `git-url` argument is optional. If omitted, use the stored `source_repo` from the registry. If provided, use the argument (and update `source_repo`).
    *   Error if no `source_repo` is stored and no `git-url` is provided.
3. **If project tool:**
    *   `git-url` argument is REQUIRED. Error if missing: `"This is a project tool with no source repo. Specify a git URL: 'purlin:toolbox push <tool> <git-url>'"`
    *   Prompt for version number (suggest `"1.0.0"`).
    *   Set `author` from `git config user.email`. Confirm with user.
    *   Rename ID: strip any existing prefix, apply `community.` prefix.
4. **Purlin tool:** Block with message: `"Purlin tools cannot be pushed. Use 'purlin:toolbox copy' first to create a project tool, then push that."`
5. **Dry-run preview:** Show what will be pushed (tool definition, version, target repo). Require confirmation.
6. Create repository structure in a temporary directory:
    *   `tool.json` — full tool definition with community metadata.
    *   `README.md` — auto-generated from friendly_name and description if not already present.
7. Initialize git repo (or clone existing), commit, push to URL.
8. **If project→community promotion:**
    *   Remove tool from `project_tools.json`.
    *   Add to `community_tools.json` with `source_repo`, `version`, `last_pull_sha` (HEAD after push), `author`.
    *   Create `.purlin/toolbox/community/<new_id>/` directory with the tool files.
9. **If community tool update:**
    *   Update `version` and `last_pull_sha` in registry.
10. Confirm: `"Pushed '<id>' to <git-url>. Version: <version>."`

### 2.5 Edit Community Tool

See `pl_toolbox.md` Section 2.6 for the edit flow. Key community-specific behavior:
*   Warning displayed before editing: `"Local edits will diverge from upstream. Next 'purlin:toolbox pull' will detect the conflict."`
*   Edits are written to `.purlin/toolbox/community/<tool_id>/tool.json`.
*   `metadata.last_updated` is set to today.
*   `last_pull_sha` in the registry is NOT updated (this is how pull detects local edits).

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Add community tool from valid repo

    Given a git repo at <url> contains a valid tool.json with id "deploy_vercel"
    When the user runs "purlin:toolbox add <url>"
    Then a directory ".purlin/toolbox/community/community.deploy_vercel/" is created
    And tool.json is copied to that directory
    And community_tools.json contains an entry with id "community.deploy_vercel"
    And the entry has source_repo, version, last_pull_sha, and author fields

#### Scenario: Add auto-prefixes community ID

    Given a git repo contains tool.json with id "deploy_vercel" (no community. prefix)
    When the user runs "purlin:toolbox add <url>"
    Then the tool is registered with id "community.deploy_vercel"
    And the user is informed of the ID rename

#### Scenario: Add fails on missing tool.json

    Given a git repo does not contain tool.json at root
    When the user runs "purlin:toolbox add <url>"
    Then an error is displayed explaining the required format
    And no files are created locally

#### Scenario: Add fails on ID collision

    Given a community tool with id "community.deploy_vercel" already exists
    And a git repo contains tool.json with id "deploy_vercel"
    When the user runs "purlin:toolbox add <url>"
    Then an error is displayed naming the conflicting tool

#### Scenario: Pull updates when no local edits

    Given community tool "community.deploy_vercel" has last_pull_sha "abc123"
    And the source repo HEAD is "def456"
    And the local tool.json has not been edited since pull
    When the user runs "purlin:toolbox pull community.deploy_vercel"
    Then tool.json is updated with upstream content
    And last_pull_sha is updated to "def456"

#### Scenario: Pull detects local edits

    Given community tool "community.deploy_vercel" has last_pull_sha "abc123"
    And the source repo HEAD is "def456"
    And the local tool.json has been edited since pull
    When the user runs "purlin:toolbox pull community.deploy_vercel"
    Then a diff is shown between local and upstream
    And the user is offered "Accept upstream / Keep local / Show diff"

#### Scenario: Pull skips up-to-date tools

    Given community tool "community.deploy_vercel" has last_pull_sha "abc123"
    And the source repo HEAD is "abc123"
    When the user runs "purlin:toolbox pull"
    Then the output shows "community.deploy_vercel: already up to date."

#### Scenario: Pull handles unreachable repo gracefully

    Given community tool "community.deploy_vercel" has source_repo pointing to an unreachable URL
    When the user runs "purlin:toolbox pull"
    Then a warning is shown for that tool
    And other community tools continue updating

#### Scenario: Push project tool to new repo

    Given project tool "my_audit" exists in project_tools.json
    When the user runs "purlin:toolbox push my_audit git@github.com:user/purlin-tool-my-audit.git"
    And provides version "1.0.0" and confirms author
    Then a dry-run preview is shown and confirmed
    And the tool is pushed to the git URL
    And the tool is removed from project_tools.json
    And the tool is added to community_tools.json with id "community.my_audit"
    And a directory ".purlin/toolbox/community/community.my_audit/" is created

#### Scenario: Push community tool uses stored repo

    Given community tool "community.deploy_vercel" has source_repo "git@github.com:user/deploy.git"
    When the user runs "purlin:toolbox push community.deploy_vercel" (no git-url)
    Then the tool is pushed to "git@github.com:user/deploy.git"

#### Scenario: Push project tool without git-url errors

    Given project tool "my_audit" has no source_repo
    When the user runs "purlin:toolbox push my_audit" (no git-url)
    Then an error is displayed with the required syntax

#### Scenario: Push purlin tool is blocked

    Given the user runs "purlin:toolbox push purlin.verify_zero_queue"
    When the skill resolves the tool
    Then the message "Purlin tools cannot be pushed" is displayed

### Manual Scenarios (Human Verification Required)

None.
