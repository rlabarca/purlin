# Discovery Sidecar: test_fixture_repo

## [BUG] M32: QA recommendation decision logic untested

- **Status:** RESOLVED
- **Action Required:** Builder
- **Description:** QA recommendation decision logic was embedded as test helper methods rather than tested as production code. The decision logic that determines when QA should produce a fixture recommendation (based on state complexity and remote configuration) and the Builder startup read path for parsing fixture_recommendations.md were both untested against edge cases.
- **Resolution:** Extracted decision logic and read path into `tools/test_support/fixture_recommendations.py` as production functions (`evaluate_fixture_needs`, `parse_recommendations`, `get_pending_recommendations`, `write_recommendation`). Added 30 new tests covering all decision branches (fixture tags present, simple/complex/no state, remote configured/missing, malformed config) and read path edge cases (empty file, missing file, partial fields, whitespace-only, multiple statuses). Updated existing scenario tests to use the production module. Total test count: 61 (up from 31).
