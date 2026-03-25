# Implementation Notes: Purlin Smoke Testing

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|

## Notes

**[CLARIFICATION]** The `_split_architect_content` heuristic in the tier table reader works by checking both `PURLIN_OVERRIDES.md` and `QA_OVERRIDES.md` — results are merged, with entries in both files deduplicated by feature name.

**[CLARIFICATION]** `get_smoke_features()` combines two sources: the tier table (from override files) AND `_smoke.json` files with `"tier": "smoke"`. This satisfies spec § 2.4's requirement that the smoke gate also detects `_smoke.json` files even if the feature is not in the tier table.

**[CLARIFICATION]** `order_verification()` returns a structured ordering but does NOT execute tests. The `/pl-verify` skill consumes this ordering to run smoke regressions first, then smoke QA scenarios, then standard features.

### Test Quality Audit
- Rubric: 6/6 PASS
- Tests: 7 total, 7 passed
- AP scan: clean
- Date: 2026-03-25
