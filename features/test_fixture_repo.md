# Feature: Test Fixture Repo System

> Label: "Tool: Test Fixture Repo"
> Category: "Test Infrastructure"
> Prerequisite: features/policy_critic.md

[TODO]

## 1. Overview

A test infrastructure pattern where project states for automated testing live as immutable tags in a dedicated git fixture repository. Each tag represents the preconditions for one test scenario. This is consumer-facing -- any project using Purlin can create their own fixture repo to provide controlled, reproducible state for automated test execution.

The fixture repo eliminates the "complex setup" problem: scenarios that require specific git states, config values, worktree layouts, or branch topologies get their preconditions checked in as tagged snapshots rather than constructed at test time.

---

## 2. Requirements

### 2.1 Feature Metadata Convention

- Feature files MAY include a `> Test Fixtures: <repo-url>` blockquote metadata line (e.g., `> Test Fixtures: https://github.com/org/my-project-fixtures.git`), placed alongside other `>` metadata (Label, Category, Prerequisite, Web Testable).
- The URL declares the git repository containing fixture states for that feature's scenarios.
- Multiple features MAY reference the same fixture repo URL.
- The expected pattern is **one fixture repo per project**. Tags are namespaced by feature name (`<project-ref>/<feature-name>/<scenario-slug>`), so a single repo holds fixtures for all features. Multiple repos per project are supported but not recommended unless there's a specific reason (e.g., access control separation).
- When present, automated test tools can look up fixture tags by feature name and scenario slug.

### 2.2 Tag Convention (Immutable Fixture States)

Fixture states are git tags (not branches). Tags are immutable -- once created, they represent a fixed snapshot of project state for that scenario. No drift, no merge conflicts.

**Convention:** `<project-ref>/<feature-name>/<scenario-slug>`

- `<project-ref>` is the project branch or version the fixtures target (e.g., `main`, `v2`, `release-1.x`). Most single-branch projects use `main/`.
- `<feature-name>` matches the feature file name without extension (e.g., `cdd_branch_collab`).
- `<scenario-slug>` is a kebab-case slug derived from the scenario title (e.g., `sync-state-ahead`).

**Examples:**
- `main/cdd_branch_collab/sync-state-ahead`
- `main/cdd_branch_collab/sync-state-diverged`
- `main/cdd_isolated_teams/worktree-with-uncommitted`
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

- `fixture checkout <repo-url> <tag> [--dir <path>]` -- Shallow clone at the specified tag into a temp directory (or the path specified by `--dir`). Prints the checkout path to stdout. Uses `git clone --depth 1 --branch <tag>` for efficiency.
- `fixture cleanup <path>` -- Remove the checked-out fixture directory (`rm -rf`). Validates the path is under `/tmp/` or the system temp directory before removing, as a safety guard.
- `fixture list <repo-url> [--ref <project-ref>]` -- List available fixture tags via `git ls-remote --tags`. Optionally filter by `<project-ref>/` prefix. Output: one tag per line, sorted alphabetically.
- `fixture prune <repo-url> [--ref <project-ref>]` -- Cross-reference fixture tags against active feature files in the current project's `features/` directory. List orphan tags (feature no longer exists or has a tombstone). Prompt for confirmation before deleting remote tags.

**Submodule safety:**
- Uses `PURLIN_PROJECT_ROOT` for resolving the `features/` directory when cross-referencing tags.
- Temp directories created via `mktemp -d`.
- No artifacts written inside `tools/`.
- All generated files (if any) go to `.purlin/runtime/` or system temp.

### 2.5 Pruning and Lifecycle

**Prune command:** `fixture prune <repo-url>` scans all tags via `git ls-remote --tags`, extracts the `<feature-name>` component from each tag path, and checks whether a matching `features/<feature-name>.md` exists in the current project. Tags whose feature file is missing or has a tombstone (`features/tombstones/<feature-name>.md`) are listed as orphans.

**Tombstone integration:** When the Architect retires a feature via `/pl-tombstone`, and the feature spec has `> Test Fixtures:` metadata, the tombstone protocol gains a reminder step: "Run `fixture prune <repo-url>` to flag this feature's fixture tags for deletion."

### 2.6 Architect Workflow

1. While designing a feature, the Architect identifies scenarios that need specific project state (git state, config values, worktree layouts, etc.).
2. The Architect prompts the user: "These scenarios need controlled state. Want to use a fixture repo for automated testing?"
3. If yes: the user creates an empty git repo for test fixtures. The Architect records the URL as `> Test Fixtures: <repo-url>` in the feature spec.
4. If no: scenarios stay manual (`@manual-interactive` / `@manual-visual`).
5. The Architect writes scenarios with Given steps that reference fixture state (e.g., "Given the fixture tag `main/cdd_branch_collab/sync-state-ahead` is checked out").

### 2.7 Builder Workflow

1. The Builder reads the feature spec, sees `> Test Fixtures: <repo-url>` metadata.
2. The Builder creates tags in the fixture repo following the convention: `<project-ref>/<feature>/<scenario-slug>`.
3. Each tag points to a commit containing the project state for that scenario.
4. Each tagged commit has a clear message describing the state it represents.
5. The Builder writes the automated test code that checks out the tag, runs the check, and asserts results.
6. For Purlin-internal fixtures (features in `dev/`), the Builder creates a setup script (`dev/setup_<name>_fixtures.sh`) that deterministically generates the fixture repo from the project's own files. This script IS the portable fixture definition -- the repo is derived, not stored. Test runners SHOULD auto-invoke this script when the fixture repo is missing.

### 2.8 Integration with /pl-web-verify

For CDD dashboard scenarios needing fixture state:

1. Check out fixture tag into temp dir via `fixture checkout`.
2. Start CDD server against it: `python3 tools/cdd/serve.py --project-root /tmp/fixture-xyz/`.
3. `/pl-web-verify` runs against that server instance.
4. Cleanup via `fixture cleanup`.

### 2.9 Integration with Agent Behavior Tests

For agent startup/resume scenarios:

1. Check out fixture tag (e.g., `main/cdd_startup_controls/expert-mode`).
2. Construct system prompt from the fixture's instruction files.
3. Run `claude --print` against the fixture project.
4. Assert output patterns.
5. Cleanup.

### 2.10 Critic Validation (Optional)

The Critic MAY validate that fixture tags exist for scenarios that reference them. When a feature has `> Test Fixtures:` metadata and a scenario's Given step references a fixture tag, the Critic can check `fixture list` output to confirm the tag exists. This is informational (MEDIUM priority), not blocking.

---

## 3. Scenarios

### Automated Scenarios

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

### Manual Scenarios (Human Verification Required)

None.
