# Discovery Sidecar: test_fixture_repo

## [BUG] M32: QA recommendation decision logic untested

- **Status:** RESOLVED
- **Action Required:** Engineer
- **Description:** QA recommendation decision logic was embedded as test helper methods rather than tested as production code. The decision logic that determines when QA should produce a fixture recommendation (based on state complexity and remote configuration) and Engineer mode startup read path for parsing fixture_recommendations.md were both untested against edge cases.
- **Resolution:** Extracted decision logic and read path into `scripts/test_support/fixture_recommendations.py` as production functions (`evaluate_fixture_needs`, `parse_recommendations`, `get_pending_recommendations`, `write_recommendation`). Added 30 new tests covering all decision branches (fixture tags present, simple/complex/no state, remote configured/missing, malformed config) and read path edge cases (empty file, missing file, partial fields, whitespace-only, multiple statuses). Updated existing scenario tests to use the production module. Total test count: 61 (up from 31).

### [BUG] add-tag regex permits underscores in slug segment (Discovered: 2026-03-23)
- **Observed Behavior:** scripts/test_support/fixture.sh:128 regex accepts underscores in the slug segment of tag paths.
- **Expected Behavior:** Spec says scenario slugs use hyphens only (kebab-case). Fix regex to reject underscores in the third path segment.
- **Action Required:** Engineer
- **Status:** RESOLVED
- **Source:** Spec-code audit (LOW). See test_fixture_repo.impl.md for context.
