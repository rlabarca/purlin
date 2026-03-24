# User Testing Discoveries: Test Fixture Repo

### [BUG] M32: QA recommendation decision logic untested (Discovered: 2026-03-23)
- **Observed Behavior:** Format of QA recommendations is validated in tests but the decision logic and Builder startup read path are untested.
- **Expected Behavior:** Tests should cover the decision logic that produces QA recommendations and verify that the Builder correctly reads them at startup.
- **Action Required:** Builder
- **Status:** OPEN
- **Source:** Spec-code audit (deep mode). See test_fixture_repo.impl.md for full context.
