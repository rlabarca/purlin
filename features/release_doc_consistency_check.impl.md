# Implementation Notes: Documentation Consistency Check

This step applies to user-facing documentation only. Feature specification files (`features/*.md`) are not "documentation" for the purposes of this step — they are the ground truth source, not the output being checked here.

For the Purlin framework repository, README.md is the primary documentation target. Consumer projects may also have documentation in `docs/` or equivalent locations.

### Test Quality Audit
Evaluated via Haiku subagent (2026-03-18)

Context: This feature has Code: null — the automated scenarios are tested via `doc_consistency_check.py` (a detection script owned by `release_audit_automation`). Tests verify the detection logic; the correction/commit step is performed by the Architect agent at runtime and is inherently untestable via unit tests. Subagent DIVERGENT verdicts reflect this architectural gap, not actual test defects.

- Scenario: Stale feature description corrected -> TestDocConsistencyStaleRef -> ALIGNED (detection-scoped: verifies stale path references are identified with correct category and content)
- Scenario: Documentation is fully consistent -> TestDocConsistencyCoverageGap -> ALIGNED (detection-scoped: verifies coverage gaps are identified when features lack README mention)
- Scenario: Reference to removed functionality corrected -> TestDocConsistencyTombstone -> ALIGNED (detection-scoped: verifies tombstone references in README are flagged)
- Scenario: Stale file path corrected -> TestAllScriptsValidJSON.test_doc_consistency_check -> ALIGNED (contract: verifies output structure for downstream consumers)
