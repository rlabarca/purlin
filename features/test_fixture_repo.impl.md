# Implementation Notes: Test Fixture Repo

*   **Setup Script Location:** `dev/setup_fixture_repo.sh` — Purlin-dev-specific, not distributed to consumers. Creates the convention-path fixture repo at `.purlin/runtime/fixture-repo` with all 74 tags across 29 features.
*   **Convention Path:** `.purlin/runtime/fixture-repo` (bare git repo). Gitignored via `.purlin/runtime/` pattern. Deterministically regenerable from the setup script.
*   **Fixture Tool Location:** `tools/test_support/fixture.sh` — consumer-facing, submodule-safe. Implements checkout, cleanup, list, prune subcommands.
*   **Tag Count:** 74 unique tags covering all `## Test Fixtures` sections across 29 features.
*   **Test Isolation Fix:** `test_no_repo_url_returns_repo_unavailable` in `tools/critic/test_critic.py` needed a `project_root` override to a temp directory to avoid resolving the real convention-path repo. Without this, the test passed `repo_url=None` but the three-tier lookup found the real repo at tier 3.
*   **`init` and `add-tag` Implementation:** The existing `dev/setup_fixture_repo.sh` is the reference implementation for what `add-tag` needs to do — it already does temp clone, copy files, commit, tag, push to bare, cleanup. Engineer mode should: (1) add `cmd_init` and `cmd_add_tag` functions to `tools/test_support/fixture.sh` following the existing dispatch pattern (`cmd_checkout`, `cmd_cleanup`, etc. + `case` branch), (2) extract the tag-creation logic from `setup_fixture_repo.sh` into `cmd_add_tag`, (3) refactor `setup_fixture_repo.sh` to call `fixture init` and `fixture add-tag` instead of raw git plumbing, (4) add tag format validation to `cmd_add_tag` (3 slash-separated segments, each lowercase alphanumeric + hyphens).
*   **[CLARIFICATION]** The `release_audit_automation.md` fixture tags use different feature slugs (e.g., `release_verify_deps/` instead of `release_audit_automation/`) because those integration tests verify multiple release steps, each with their own namespace. This is intentional per the tag convention. (Severity: INFO)
*   **[CLARIFICATION]** The `agent_behavior_tests.md` fixture tags reference tags in other features' namespaces (`cdd_startup_controls/`, `pl_session_resume/`, `pl_help/`) rather than `agent_behavior_tests/`. These cross-references are correct — the behavior tests consume project states defined by those features. The setup script creates all referenced tags. (Severity: INFO)

*   **`remote` and Auto-Push Implementation:** `cmd_remote` handles three cases: (1) local repo exists → add/update origin remote + push all tags, (2) no local repo + non-empty remote → bare clone, (3) no local repo + empty remote → init bare + add origin. URL is stored in config via `_write_fixture_repo_url` python3 helper. Auto-push in `cmd_add_tag` reads config after local tag creation and pushes the single tag; push failure warns but exits 0 (local tag is still valid). `--no-push` flag suppresses auto-push.

**[DISCOVERY] [ACKNOWLEDGED]** QA recommendation decision logic untested
**Source:** /pl-spec-code-audit --deep (M32)
**Severity:** MEDIUM
**Details:** Tests validate the `fixture_recommendations.md` file format but not the QA decision logic (when to recommend a remote repo) or that Engineer mode startup sequence reads the file. Both are agent-level behaviors but should have structural tests verifying the skill file documents the workflow.
**Suggested fix:** Add structural tests that verify the QA authoring skill references fixture recommendations and Engineer mode startup reads the file.
