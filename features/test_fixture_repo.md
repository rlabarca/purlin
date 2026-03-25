# Feature: Test Fixture Repo System

> Label: "Tool: Test Fixture Repo"
> Category: "Test Infrastructure"
> Prerequisite: features/policy_critic.md

[Complete] <!-- re-verified 2026-03-23 after doc-only spec edits (decision matrix, section renumbering) -->

## 1. Overview

A test infrastructure pattern where project states for automated testing live as immutable tags in a dedicated git fixture repository. Each tag represents the preconditions for one test scenario. This is consumer-facing -- any project using Purlin can create their own fixture repo to provide controlled, reproducible state for automated test execution.

The fixture repo eliminates the "complex setup" problem: scenarios that require specific git states, config values, or branch topologies get their preconditions checked in as tagged snapshots rather than constructed at test time.

---

## 2. Requirements

### 2.1 Feature Metadata Convention

- **Convention path:** The fixture repo lives at `.purlin/runtime/fixture-repo` (a local bare git repo). This is the default location — no configuration is needed. Setup scripts in `dev/` generate this repo deterministically from the project's own files.
- The expected pattern is **one fixture repo per project**. Tags are namespaced by feature name (`<project-ref>/<feature-name>/<scenario-slug>`), so a single repo holds fixtures for all features.
- When the fixture repo exists at the convention path, automated test tools and the Critic can look up fixture tags by feature name and scenario slug without any per-feature metadata.
- **Optional overrides:** Feature files MAY include a `> Test Fixtures: <repo-url>` blockquote metadata line to point at a different repo (e.g., a remote URL or alternate local path). `.purlin/config.json` MAY include a `fixture_repo_url` key to override the convention path project-wide. These are for unusual cases only — most projects use the convention path exclusively.
- **Resolution order:** The Critic and fixture tools resolve the fixture repo in this order: (1) per-feature `> Test Fixtures:` metadata, (2) project-level `fixture_repo_url` config, (3) convention path `.purlin/runtime/fixture-repo`. The first one that exists wins.
- Relative paths (in any source) are resolved against `PURLIN_PROJECT_ROOT`.

### 2.2 Tag Convention (Immutable Fixture States)

Fixture states are git tags (not branches). Tags are immutable -- once created, they represent a fixed snapshot of project state for that scenario. No drift, no merge conflicts.

**Convention:** `<project-ref>/<feature-name>/<scenario-slug>`

- `<project-ref>` is the project branch or version the fixtures target (e.g., `main`, `v2`, `release-1.x`). Most single-branch projects use `main/`.
- `<feature-name>` matches the feature file name without extension (e.g., `cdd_branch_collab`).
- `<scenario-slug>` is an Architect-chosen, short descriptive identifier (2-4 words, kebab-case with hyphens). Slugs describe the fixture state, not the scenario title. Examples: `ahead-3`, `empty-repo`, `expert-mode`. Note: `<feature-name>` uses underscores (matching the feature filename), while `<scenario-slug>` uses hyphens. This distinction is intentional -- filenames follow Python/filesystem conventions, slugs follow URL/kebab-case conventions.

**Examples:**
- `main/cdd_branch_collab/sync-state-ahead`
- `main/cdd_branch_collab/sync-state-diverged`
- `main/release_verify_deps/cycle-in-prerequisites`
- `main/cdd_startup_controls/expert-mode`

When a project version changes enough to need different fixtures (schema changes, new config format), new tags are created under the new `<project-ref>`. Old tags coexist until pruned.

### 2.3 Tagged Commit Contents

Each tagged commit in the fixture repo contains the project state needed for that scenario:

- `.purlin/` config files (config.json, config.local.json, overrides)
- `features/` directory with feature specs
- `tests/` directory with any pre-existing test artifacts
- Git history (commits, branches) as needed by the scenario
- `.purlin/runtime/` files (port files, checkpoints, active_branch)
- Any other files the scenario's Given preconditions require

The commit message MUST describe the state it represents (e.g., "Project with local branch 3 commits ahead of remote collab branch").

### 2.4 Fixture Tool

**Location:** `tools/test_support/fixture.sh` -- consumer-facing, submodule-safe.

**Subcommands:**

- `fixture init [--path <path>]` -- Creates a bare git repo at the convention path (`.purlin/runtime/fixture-repo`). Idempotent: if the repo already exists, prints a message and exits 0. Uses `git init --bare`. The `--path` option overrides the convention path. Prints the repo path to stdout.
- `fixture add-tag <tag> [--from-dir <path>] [--message <msg>] [--force] [--no-push]` -- Creates a tagged commit in the fixture repo from a source directory. The tag MUST follow the `<ref>/<feature>/<slug>` convention (validated: 3 path segments, lowercase alphanumeric plus hyphens in each segment). `--from-dir` defaults to `$PURLIN_PROJECT_ROOT`. `--message` defaults to `"State for <tag>"`. Errors if the tag already exists unless `--force` is specified. Implementation: temp clone of bare repo, copy source files, commit, tag, push to bare, cleanup temp clone. If the fixture repo does not exist, errors with "Run `fixture init` first." **Auto-push:** After successfully creating the tag locally, if `fixture_repo_url` is set in `.purlin/config.json`, automatically pushes the new tag to the remote via `fixture push <url> --tag <tag>`. Prints `"Pushed <tag> to remote."` on success. If the push fails, prints a warning but does NOT fail the command (the local tag is still valid). Use `--no-push` to skip the auto-push.
- `fixture checkout <repo-url> <tag> [--dir <path>]` -- Shallow clone at the specified tag into a temp directory (or the path specified by `--dir`). Prints the checkout path to stdout. Uses `git clone --depth 1 --branch <tag>` for efficiency.
- `fixture cleanup <path>` -- Remove the checked-out fixture directory (`rm -rf`). Validates the path is under `/tmp/` or the system temp directory before removing, as a safety guard.
- `fixture list <repo-url> [--ref <project-ref>]` -- List available fixture tags via `git ls-remote --tags`. Optionally filter by `<project-ref>/` prefix. Output: one tag per line, sorted alphabetically.
- `fixture verify-url <url>` -- Test read/write access to a fixture repo URL. If the URL is HTTPS and fails, automatically tries the SSH equivalent for GitHub/GitLab. Prints the working URL to stdout on success (exit 0). Prints diagnostic guidance to stderr on failure (exit 1). Agents call this before recording `> Test Fixtures:` metadata.
- `fixture remote <url>` -- One-time setup that connects the local fixture repo to a shared remote. Stores `<url>` in `.purlin/config.json` under `fixture_repo_url`. Behavior depends on local state:
  - **Local repo exists** (`.purlin/runtime/fixture-repo`): Verifies the URL via `verify-url`, adds it as the `origin` remote on the local bare repo, pushes all existing tags and branches to the remote, and prints `"Synced N fixture tags to remote."`.
  - **No local repo**: Clones the remote to `.purlin/runtime/fixture-repo` (bare clone). If the remote is empty (zero refs), initializes a bare repo locally and adds the remote as `origin` instead. Prints `"Fixture repo configured. Remote: <url>"`.
  - **Already configured**: If `fixture_repo_url` is already set in config, prints the current URL. If a different URL is passed, prompts: `"Remote is already set to <old>. Replace with <new>? [y/n]"`. On confirmation, updates the config and re-adds the remote.
  - **Access failure**: If `verify-url` fails, prints diagnostic guidance (same as `verify-url`) and exits non-zero without modifying config.
- `fixture push <remote-url> [--tag <tag>]` -- Push fixture tags from the local convention-path repo to a remote git URL. When `--tag` is specified, pushes only that tag; otherwise pushes all tags. If push fails due to authentication, prints a diagnostic message guiding the user through setting up git push access (SSH key, token, etc.) and exits non-zero. The agent retries after the user confirms access is configured. This command enables the workflow where tags are created locally (via `fixture add-tag`) and then synced to a shared remote repo.
- `fixture prune <repo-url> [--ref <project-ref>]` -- Cross-reference fixture tags against active feature files in the current project's `features/` directory. List orphan tags (feature no longer exists or has a tombstone). Prompt for confirmation before deleting remote tags.

**Submodule safety:**
- Uses `PURLIN_PROJECT_ROOT` for resolving the `features/` directory when cross-referencing tags.
- Temp directories created via `mktemp -d`.
- No artifacts written inside `tools/`.
- All generated files (if any) go to `.purlin/runtime/` or system temp.

### 2.5 Pruning and Lifecycle

**Prune command:** `fixture prune <repo-url>` scans all tags via `git ls-remote --tags`, extracts the `<feature-name>` component from each tag path, and checks whether a matching `features/<feature-name>.md` exists in the current project. Tags whose feature file is missing or has a tombstone (`features/tombstones/<feature-name>.md`) are listed as orphans.

**Tombstone integration:** When the Architect retires a feature via `/pl-tombstone`, and the feature spec has `> Test Fixtures:` metadata, the tombstone protocol gains a reminder step: "Run `fixture prune <repo-url>` to flag this feature's fixture tags for deletion."

### 2.6 Fixture Trigger Decision Matrix

Fixtures are recommended and created by different agents at different stages. This matrix defines the explicit triggers:

| Role | Trigger | Action |
|------|---------|--------|
| **Architect** | Writing a spec where scenarios need controlled project state (multi-feature interactions, specific lifecycle states, config variations) | Declare `### Integration Test Fixture Tags` section with tag table and state descriptions in the feature spec |
| **Builder** | Feature spec contains a fixture tag section (`### 2.x ... Fixture Tags`) | Create setup script, run `fixture init` + `fixture add-tag` for each declared tag |
| **QA** (during `/pl-regression-author`) | Scenario needs state beyond inline `setup_commands` | Create fixtures directly via `fixture add-tag`; record in `fixture_usage.json` |
| **QA** (during `/pl-regression-author`) | Feature has NO Architect-declared fixture tags but controlled state would improve test determinism | Assess need: create directly via `fixture add-tag` if moderate complexity |

**Key principle:** QA is authorized to create fixtures without Architect pre-declaration. The Architect declares fixture needs when obvious at spec time; QA discovers needs during regression authoring. Both paths are valid. The Architect path provides upfront planning; the QA path captures discoveries made during test design.

### 2.6.1 Architect Workflow

1. While designing a feature, the Architect identifies scenarios that need specific project state (git state, config values, branch topologies, etc.).
2. The Architect prompts the user: "These scenarios need controlled state. Want to use a fixture repo for automated testing?"
3. If yes: the user creates an empty git repo for test fixtures. Before recording the URL, the Architect MUST verify access (see Section 2.6.4).
4. If no: scenarios stay manual (`@manual-interactive` / `@manual-visual`).
5. The Architect writes scenarios with Given steps that reference fixture state (e.g., "Given the fixture tag `main/cdd_branch_collab/sync-state-ahead` is checked out").

### 2.6.2 Builder Workflow

1. The Builder reads the feature spec and identifies fixture tag sections declaring needed states.
2. The Builder MUST check whether the fixture repo exists at the convention path (or per-feature override). If it does not exist, the Builder runs the setup script (see step 7) or creates one. The Builder MUST prompt the user when the fixture repo is missing and explain what will be created.
3. The Builder uses `fixture init` to create the bare repo (if not already present) and `fixture add-tag` to create each declared tag from a constructed state directory.
4. Each tag points to a commit containing the project state for that scenario.
5. Each tagged commit has a clear message describing the state it represents.
6. **Remote push:** If the feature spec declares `> Test Fixtures: <remote-url>`, the Builder MUST push tags to the remote via `fixture push <remote-url>`. The Critic validates against the remote URL, so tags that exist only locally will not satisfy the Critic gate. If push fails, guide the user through access setup and retry (see Section 2.12).
7. The Builder writes the automated test code that checks out the tag, runs the check, and asserts results.
8. The Builder creates a setup script that deterministically generates the fixture repo from the project's own files. This script IS the portable fixture definition -- the repo is derived, not stored. The setup script MUST use `fixture init` and `fixture add-tag` subcommands. Test runners MUST check for the fixture repo and run the setup script when it is missing.
   - **Purlin framework repo:** Setup scripts go in `dev/` (e.g., `dev/setup_fixture_repo.sh`). These are Purlin-specific and not distributed to consumers.
   - **Consumer projects:** Setup scripts go in a project-appropriate location (e.g., `scripts/`, `dev/`, or `tests/`). The location is a Builder decision. The script MUST create the repo at the convention path (`.purlin/runtime/fixture-repo`) so the Critic and test tools can find it without configuration.

### 2.6.3 QA Workflow

QA MAY create and manage fixtures directly during regression authoring (`/pl-regression-author`). This eliminates the handoff delay between QA discovering a fixture need and Builder creating it.

1. During regression authoring, QA evaluates fixture needs per the decision logic in `regression_testing.md` Section 2.10.1.
2. If fixtures are needed and the fixture repo does not exist, QA runs `fixture init` to create it at the convention path.
3. QA uses `fixture add-tag` to create fixture tags from constructed state directories.
4. QA records fixture usage in `tests/qa/fixture_usage.json`.

**Ownership note:** QA creates fixtures as test infrastructure (alongside scenario JSON files and harness scripts). The Builder creates fixtures when the setup requires application-level knowledge (complex build states, database migrations, etc.). Both use the same `fixture init` / `fixture add-tag` tool.

### 2.6.4 Fixture URL Access Verification

Before recording a `> Test Fixtures: <url>` in a feature spec, the agent MUST verify that the URL is accessible for both read (checkout) and write (push) operations. Most fixture repos will be private — HTTPS URLs typically fail on private repos without explicit credential configuration, while SSH URLs work via configured keys.

**Verification protocol:**

1. **Test read access:** Run `git ls-remote --tags <url> 2>&1`. If this fails (non-zero exit, "could not read Username", or authentication error), the URL is not usable as-is.
2. **Try SSH format:** If the URL is HTTPS and read fails, construct the SSH equivalent:
   - `https://github.com/<owner>/<repo>` → `git@github.com:<owner>/<repo>.git`
   - `https://gitlab.com/<owner>/<repo>` → `git@gitlab.com:<owner>/<repo>.git`
   Test read access with the SSH URL. If it succeeds, use the SSH URL in the spec.
3. **Test write access:** Run `git ls-remote <url> 2>&1` (without `--tags`). If this succeeds, push access is likely available. Full push verification happens during `fixture push`.
4. **Guide the user:** If neither HTTPS nor SSH works, print:
   ```
   Cannot access <url> for read or write.

   For GitHub private repos:
     1. Ensure SSH key is configured: ssh -T git@github.com
     2. Use SSH URL format: git@github.com:<owner>/<repo>.git

   For HTTPS with token:
     1. Configure credential helper: git config credential.helper store
     2. Or use token URL: https://<token>@github.com/<owner>/<repo>
   ```
5. **Record the working URL:** Write the verified URL (usually SSH for private repos) to the spec's `> Test Fixtures:` metadata. Never record a URL that fails the read access test.

**`fixture verify-url <url>` subcommand:**

The fixture tool provides a `verify-url` subcommand that implements this protocol:
- Tests read access via `git ls-remote --tags`.
- If HTTPS fails, tries SSH equivalent for known hosts (GitHub, GitLab).
- Prints the working URL to stdout, or an error with guidance to stderr.
- Exit 0 with working URL, exit 1 with guidance.

Agents MUST call `fixture verify-url <url>` before recording any fixture URL in a spec.

### 2.7 Integration with /pl-aft-web

For CDD dashboard scenarios needing fixture state:

1. Check out fixture tag into temp dir via `fixture checkout`.
2. Start CDD server against it: `python3 tools/cdd/serve.py --project-root /tmp/fixture-xyz/`.
3. `/pl-aft-web` runs against that server instance.
4. Cleanup via `fixture cleanup`.

### 2.8 Integration with Agent Behavior Tests

For agent startup/resume scenarios:

1. Check out fixture tag (e.g., `main/cdd_startup_controls/expert-mode`).
2. Construct system prompt from the fixture's instruction files.
3. Run `claude --print` against the fixture project.
4. Assert output patterns.
5. Cleanup.

### 2.9 Critic Validation

The Critic MUST validate that declared fixture tags exist for features that reference them. When a feature spec contains a fixture tag section (e.g., `### 2.x Web-Verify Fixture Tags` or `### 2.x Integration Test Fixture Tags`) listing expected tags, the Critic checks `fixture list` output to confirm each tag exists. Missing tags produce a MEDIUM-priority Builder action item: the fixture infrastructure must be created before the feature can pass the Implementation Gate.

This validation is also triggered when a feature has `> Test Fixtures:` metadata and a scenario's Given step references a fixture tag by name.

**Validation Gap Coverage:**

The Critic handles two distinct states when fixture tags are declared:

1. **Fixture repo accessible:** Normal path — the Critic resolves the repo via the three-tier lookup (per-feature metadata → config → convention path), then validates each declared tag against `fixture list` output. Missing tags produce MEDIUM Builder action items.
2. **Fixture repo not found:** No tier in the resolution order points to an accessible git repo (typically because the setup script hasn't been run yet). The Critic generates a MEDIUM Builder action item (category: `fixture_repo_unavailable`) instructing the Builder to run the setup script to create the repo at `.purlin/runtime/fixture-repo`. Individual tag validation is skipped (repo must be created first).

**SSH fallback for remote repos:**

When `git ls-remote --tags <url>` fails on a remote URL (non-zero exit, empty output, or authentication error), the Critic MUST attempt an SSH fallback before reporting the repo as unavailable:

- If the URL matches `https://github.com/<owner>/<repo>`, retry with `git@github.com:<owner>/<repo>.git`.
- If the URL matches `https://gitlab.com/<owner>/<repo>`, retry with `git@gitlab.com:<owner>/<repo>.git`.
- For other HTTPS URLs, no automatic fallback — report `fixture_repo_unavailable` with a note that the URL may require SSH format.

This handles the common case of private repos where SSH keys are configured but HTTPS authentication is not. The fallback is silent — if SSH succeeds, the Critic proceeds normally without surfacing the HTTPS failure.

### 2.10 Fixture Usage Tracking

QA maintains a usage tracker at `tests/qa/fixture_usage.json` (committed, QA-owned) that records which fixtures are used by which regression scenarios. This file is updated during regression scenario authoring (see `features/regression_testing.md` Section 2.10).

**Format:**

```json
{
  "last_updated": "2026-03-18T...",
  "features": {
    "instruction_audit": {
      "fixture_type": "local",
      "tags_used": ["main/instruction_audit/override-contradiction"],
      "last_authored": "2026-03-18T..."
    },
    "branch_collab": {
      "fixture_type": "none",
      "recommendation": "remote fixture repo needed",
      "reason": "complex git state with multiple branches"
    }
  }
}
```

QA announces fixture usage during authoring: `"Using fixture tag main/instruction_audit/override-contradiction (local repo)"`.

### 2.11 Remote Fixture Repos

When a feature spec declares `> Test Fixtures: <remote-url>`, the Critic validates tags against the remote repo (via `git ls-remote --tags`). Tags must exist on the remote for the Critic to clear them. The local convention-path repo is a staging area; the remote is the source of truth for declared fixtures.

**Builder push workflow:**

When creating fixtures for a feature with a remote configured (via `fixture remote` or `> Test Fixtures:` metadata):

1. Create tags locally via `fixture add-tag` — auto-push handles the rest. Each `add-tag` call automatically pushes the new tag to the configured remote (see Section 2.4).
2. If auto-push fails (authentication, permissions), the Builder:
   a. Prints a clear diagnostic: what failed, what access is needed.
   b. Guides the user through setting up push access (SSH key, personal access token, repo permissions).
   c. After the user confirms access is configured, retries via `fixture push <url>`.
   d. Does NOT ask the user to push manually — the Builder pushes once it has access.
3. After successful push, verify with `fixture list <remote-url>` that the tags are visible.
4. Re-run `tools/cdd/status.sh` to confirm the Critic clears the fixture validation.

**Remote repo setup flow:**

When a feature needs a fixture repo and no remote URL is configured:

1. The Builder prompts: "This feature needs fixture tags. Would you like to use a remote repo (shared, Critic-validated) or local only?"
2. If the user provides a remote URL, the Builder runs `fixture remote <url>` to configure the project-wide remote. This stores the URL in config, connects or clones the repo, and syncs any existing local tags.
3. If the user wants to create a new remote repo, the Builder guides them: "Create an empty git repo at your preferred host (GitHub, GitLab, etc.) and give me the URL." Then runs `fixture remote <url>`.
4. For per-feature overrides (rare), the Builder records `> Test Fixtures: <url>` in the feature spec instead.

**Checkout from remote:**

`fixture checkout` already supports remote URLs. When a remote URL is the resolved fixture repo (via the three-tier lookup), `fixture checkout <remote-url> <tag>` performs a shallow clone from the remote. No local convention-path repo is needed for checkout — only for tag creation.

### 2.12 Integration Test Fixture Tags

| Tag | State Description |
|-----|-------------------|
| `main/test_fixture_repo/repo-with-tags` | Bare git fixture repo with 3 example tags at known commits |
| `main/test_fixture_repo/empty-repo` | Bare git fixture repo initialized but containing no tags |
| `main/test_fixture_repo/repo-with-duplicate-tag` | Bare git fixture repo with a pre-existing tag for overwrite testing |

---

## 3. Scenarios

### Unit Tests

#### Scenario: Checkout creates temp directory with fixture state

    Given a fixture repo exists at <repo-url>
    And the repo has a tag "main/test_feature/scenario-one"
    When `fixture checkout <repo-url> main/test_feature/scenario-one` is run
    Then a temp directory is created
    And the directory contains the tagged commit's files
    And the checkout path is printed to stdout

#### Scenario: Checkout with explicit directory

    Given a fixture repo exists at <repo-url>
    And the repo has a tag "main/test_feature/scenario-one"
    When `fixture checkout <repo-url> main/test_feature/scenario-one --dir /tmp/my-fixture` is run
    Then the fixture is checked out to /tmp/my-fixture
    And /tmp/my-fixture contains the tagged commit's files

#### Scenario: Cleanup removes fixture directory

    Given a fixture was checked out to /tmp/fixture-abc
    When `fixture cleanup /tmp/fixture-abc` is run
    Then /tmp/fixture-abc no longer exists

#### Scenario: Cleanup refuses non-temp paths

    Given a path "/Users/someone/important-project" is passed
    When `fixture cleanup /Users/someone/important-project` is run
    Then the command prints an error about unsafe path
    And does not delete the directory

#### Scenario: List shows all fixture tags

    Given a fixture repo has tags main/feat_a/s1, main/feat_a/s2, main/feat_b/s1
    When `fixture list <repo-url>` is run
    Then all three tags are printed, one per line, sorted alphabetically

#### Scenario: List filters by project ref

    Given a fixture repo has tags main/feat_a/s1, v2/feat_a/s1
    When `fixture list <repo-url> --ref main` is run
    Then only main/feat_a/s1 is printed
    And v2/feat_a/s1 is not shown

#### Scenario: Prune identifies orphan tags

    Given a fixture repo has tags main/feat_a/s1 and main/feat_retired/s1
    And the current project has features/feat_a.md but no features/feat_retired.md
    When `fixture prune <repo-url>` is run
    Then main/feat_retired/s1 is listed as an orphan
    And main/feat_a/s1 is not listed

#### Scenario: Prune detects tombstoned features

    Given a fixture repo has tags main/old_feature/s1
    And the current project has features/tombstones/old_feature.md
    When `fixture prune <repo-url>` is run
    Then main/old_feature/s1 is listed as an orphan

#### Scenario: Init creates bare repo at convention path

    Given no fixture repo exists at `.purlin/runtime/fixture-repo`
    When `fixture init` is run
    Then a bare git repo is created at `.purlin/runtime/fixture-repo`
    And the repo path is printed to stdout
    And `git rev-parse --is-bare-repository` in that path returns "true"

#### Scenario: Init is idempotent when repo exists

    Given a fixture repo already exists at `.purlin/runtime/fixture-repo`
    When `fixture init` is run
    Then the command exits 0
    And prints a message indicating the repo already exists
    And the existing repo is not modified

#### Scenario: Init with explicit path

    Given no fixture repo exists at `/tmp/custom-fixture-repo`
    When `fixture init --path /tmp/custom-fixture-repo` is run
    Then a bare git repo is created at `/tmp/custom-fixture-repo`
    And the custom path is printed to stdout

#### Scenario: Add-tag creates tagged commit from directory

    Given a fixture repo exists at the convention path
    And a source directory contains files representing project state
    When `fixture add-tag main/test_feature/my-state --from-dir <source-dir>` is run
    Then the tag `main/test_feature/my-state` exists in the fixture repo
    And checking out that tag yields the files from the source directory
    And the commit message defaults to "State for main/test_feature/my-state"

#### Scenario: Add-tag defaults to project root when from-dir omitted

    Given a fixture repo exists at the convention path
    And PURLIN_PROJECT_ROOT is set
    When `fixture add-tag main/test_feature/default-source` is run without --from-dir
    Then the tag is created from the files in PURLIN_PROJECT_ROOT

#### Scenario: Add-tag rejects invalid tag format

    Given a fixture repo exists at the convention path
    When `fixture add-tag invalid-tag-no-slashes` is run
    Then the command exits with a non-zero status
    And prints an error about invalid tag format
    And no tag is created

#### Scenario: Add-tag refuses existing tag without force

    Given a fixture repo exists at the convention path
    And the tag `main/test_feature/existing-state` already exists
    When `fixture add-tag main/test_feature/existing-state` is run without --force
    Then the command exits with a non-zero status
    And prints an error that the tag already exists
    And the existing tag is not modified

#### Scenario: Add-tag with force overwrites existing tag

    Given a fixture repo exists at the convention path
    And the tag `main/test_feature/existing-state` already exists
    When `fixture add-tag main/test_feature/existing-state --force` is run
    Then the command exits 0
    And the tag `main/test_feature/existing-state` points to a new commit
    And checking out that tag yields the updated files

#### Scenario: Verify-url succeeds with accessible SSH URL

    Given a remote git repo exists at git@github.com:owner/repo.git
    And SSH keys are configured for github.com
    When `fixture verify-url git@github.com:owner/repo.git` is run
    Then the command exits 0
    And prints git@github.com:owner/repo.git to stdout

#### Scenario: Verify-url falls back to SSH when HTTPS fails on private repo

    Given a private remote git repo exists at https://github.com/owner/repo
    And HTTPS auth is not configured
    And SSH keys are configured for github.com
    When `fixture verify-url https://github.com/owner/repo` is run
    Then the command exits 0
    And prints git@github.com:owner/repo.git to stdout

#### Scenario: Verify-url prints guidance when no access method works

    Given a remote git repo URL where neither HTTPS nor SSH access is configured
    When `fixture verify-url <url>` is run
    Then the command exits 1
    And prints diagnostic guidance to stderr about configuring SSH keys or HTTPS tokens

#### Scenario: Push syncs all tags to remote

    Given a fixture repo exists at the convention path with tags main/feat_a/s1 and main/feat_a/s2
    And a remote git repo exists at <remote-url> with no tags
    When `fixture push <remote-url>` is run
    Then both tags are pushed to the remote
    And `fixture list <remote-url>` shows main/feat_a/s1 and main/feat_a/s2

#### Scenario: Push syncs a specific tag to remote

    Given a fixture repo exists at the convention path with tags main/feat_a/s1 and main/feat_a/s2
    And a remote git repo exists at <remote-url> with no tags
    When `fixture push <remote-url> --tag main/feat_a/s1` is run
    Then only main/feat_a/s1 is pushed to the remote
    And `fixture list <remote-url>` shows main/feat_a/s1

#### Scenario: Push fails gracefully on auth error

    Given a fixture repo exists at the convention path with tags
    And a remote git repo exists at <remote-url> but push access is not configured
    When `fixture push <remote-url>` is run
    Then the command exits with a non-zero status
    And prints a diagnostic message about authentication failure
    And suggests steps to configure push access

#### Scenario: QA records fixture usage during scenario authoring

    Given QA is authoring a regression scenario for feature "instruction_audit"
    And the scenario uses fixture tag "main/instruction_audit/override-contradiction"
    When the scenario JSON file is written
    Then tests/qa/fixture_usage.json is updated with the feature entry
    And the entry records fixture_type "local" and the tag used
    And last_authored is set to the current timestamp

#### Scenario: Remote setup with existing local repo syncs tags

    Given a fixture repo exists at `.purlin/runtime/fixture-repo` with tags main/feat_a/s1 and main/feat_a/s2
    And a remote git repo exists at <remote-url> with no tags
    When `fixture remote <remote-url>` is run
    Then `fixture_repo_url` is set to <remote-url> in `.purlin/config.json`
    And the remote is added as origin on the local bare repo
    And both tags are pushed to the remote
    And the output includes "Synced 2 fixture tags to remote."

#### Scenario: Remote setup clones when no local repo exists

    Given no fixture repo exists at `.purlin/runtime/fixture-repo`
    And a remote git repo exists at <remote-url> with tags main/feat_a/s1
    When `fixture remote <remote-url>` is run
    Then `fixture_repo_url` is set to <remote-url> in `.purlin/config.json`
    And `.purlin/runtime/fixture-repo` is created as a bare clone of the remote
    And the output includes "Fixture repo configured. Remote: <remote-url>"

#### Scenario: Remote setup initializes when remote is empty

    Given no fixture repo exists at `.purlin/runtime/fixture-repo`
    And a remote git repo exists at <remote-url> with zero refs
    When `fixture remote <remote-url>` is run
    Then `fixture_repo_url` is set to <remote-url> in `.purlin/config.json`
    And a bare repo is initialized at `.purlin/runtime/fixture-repo`
    And the remote is added as origin
    And the output includes "Fixture repo configured. Remote: <remote-url>"

#### Scenario: Remote setup rejects inaccessible URL

    Given a URL that fails verify-url (neither HTTPS nor SSH access works)
    When `fixture remote <url>` is run
    Then the command exits with a non-zero status
    And `.purlin/config.json` is not modified
    And diagnostic guidance is printed

#### Scenario: Remote setup prompts before replacing existing URL

    Given `fixture_repo_url` is already set to <old-url> in `.purlin/config.json`
    When `fixture remote <new-url>` is run
    Then the output includes "Remote is already set to <old-url>. Replace with <new-url>?"
    When the user confirms
    Then `fixture_repo_url` is updated to <new-url>
    And the new remote replaces origin on the local bare repo

#### Scenario: Add-tag auto-pushes when remote is configured

    Given a fixture repo exists at the convention path
    And `fixture_repo_url` is set in `.purlin/config.json`
    When `fixture add-tag main/test_feature/new-state` is run
    Then the tag is created locally
    And the tag is automatically pushed to the remote
    And the output includes "Pushed main/test_feature/new-state to remote."

#### Scenario: Add-tag auto-push failure does not fail the command

    Given a fixture repo exists at the convention path
    And `fixture_repo_url` is set but push access is broken
    When `fixture add-tag main/test_feature/new-state` is run
    Then the tag is created locally (exit 0)
    And the output includes a warning about the failed push
    And the local tag is still valid

#### Scenario: Add-tag skips auto-push with --no-push

    Given a fixture repo exists at the convention path
    And `fixture_repo_url` is set in `.purlin/config.json`
    When `fixture add-tag main/test_feature/new-state --no-push` is run
    Then the tag is created locally
    And no push to the remote is attempted

### QA Scenarios

None.
