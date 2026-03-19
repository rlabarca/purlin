# Implementation Notes: Release Audit Automation

**[AUTONOMOUS]** Created `tools/release/audit_common.py` as a shared utility module for project root detection, finding construction, output formatting, and JSON output. This was not specified but the shared output format (Section 2.2) and shared submodule safety pattern (Section 2.3) naturally called for a common module. (Severity: WARN)
**Architect Acknowledgment (2026-03-19):** Approved. Extracting shared infrastructure into a common module is consistent with the DRY principle and the spec's shared output format requirement. No spec change needed.

**[AUTONOMOUS]** Folded `release_framework_doc_consistency.py` (Section 2.10) into `doc_consistency_check.py` and `instruction_audit.py` as permitted by the spec: "If the overlap is sufficient, this script MAY be omitted and its checks folded into the other two." The doc consistency script handles README staleness and feature coverage; the instruction audit handles override consistency and path resolution. (Severity: WARN)
**Architect Acknowledgment (2026-03-19):** Approved. The spec explicitly permits this folding. The distribution of checks across the two remaining scripts is logical and complete.

**[CLARIFICATION]** Tests use local temp directory fixtures (via `create_fixture()` helper) rather than fixture repo tags. The spec defines fixture tags in Section 2.11 for the fixture repo, but the test infrastructure can exercise the same checks with in-process fixture state. This avoids a dependency on a remote fixture repo for unit tests while still validating detection accuracy. (Severity: INFO)

**[CLARIFICATION]** The `submodule_safety_audit.py` implements categories 1, 3, 4, and 5 of the 7 listed in Section 2.6 via direct code analysis. Categories 2 (climbing priority), 6 (hardcoded root assumptions), and 7 (instruction file path references) overlap significantly with categories 1 and 5 and are partially covered by the env var and CWD checks. Full AST-based data flow analysis for climbing priority ordering would require significantly more complexity for marginal additional safety. (Severity: INFO)
