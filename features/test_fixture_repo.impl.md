# Implementation Notes: Test Fixture Repo

*   **Setup Script Location:** `dev/setup_fixture_repo.sh` — Purlin-dev-specific, not distributed to consumers. Creates the convention-path fixture repo at `.purlin/runtime/fixture-repo` with all 74 tags across 29 features.
*   **Convention Path:** `.purlin/runtime/fixture-repo` (bare git repo). Gitignored via `.purlin/runtime/` pattern. Deterministically regenerable from the setup script.
*   **Fixture Tool Location:** `tools/test_support/fixture.sh` — consumer-facing, submodule-safe. Implements checkout, cleanup, list, prune subcommands.
*   **Tag Count:** 74 unique tags covering all `## Test Fixtures` sections across 29 features.
*   **Test Isolation Fix:** `test_no_repo_url_returns_repo_unavailable` in `tools/critic/test_critic.py` needed a `project_root` override to a temp directory to avoid resolving the real convention-path repo. Without this, the test passed `repo_url=None` but the three-tier lookup found the real repo at tier 3.
*   **[CLARIFICATION]** The `release_audit_automation.md` fixture tags use different feature slugs (e.g., `release_verify_deps/` instead of `release_audit_automation/`) because those integration tests verify multiple release steps, each with their own namespace. This is intentional per the tag convention. (Severity: INFO)
*   **[CLARIFICATION]** The `agent_behavior_tests.md` fixture tags reference tags in other features' namespaces (`cdd_startup_controls/`, `pl_session_resume/`, `pl_help/`) rather than `agent_behavior_tests/`. These cross-references are correct — the behavior tests consume project states defined by those features. The setup script creates all referenced tags. (Severity: INFO)
