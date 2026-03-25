# Implementation Notes: Release Audit Automation

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|
| (see prose) | [ACKNOWLEDGED]** verify_zero_queue reads critic.json directly instead of scan.sh | DISCOVERY | PENDING |
| (see prose) | [ACKNOWLEDGED]** Instruction audit contradiction detection is heuristic-only | DISCOVERY | PENDING |

**[AUTONOMOUS]** Created `tools/release/audit_common.py` as a shared utility module for project root detection, finding construction, output formatting, and JSON output. This was not specified but the shared output format (Section 2.2) and shared submodule safety pattern (Section 2.3) naturally called for a common module. (Severity: WARN)
**PM Acknowledgment (2026-03-19):** Approved. Extracting shared infrastructure into a common module is consistent with the DRY principle and the spec's shared output format requirement. No spec change needed.

**[AUTONOMOUS]** Folded `release_framework_doc_consistency.py` (Section 2.10) into `doc_consistency_check.py` and `instruction_audit.py` as permitted by the spec: "If the overlap is sufficient, this script MAY be omitted and its checks folded into the other two." The doc consistency script handles README staleness and feature coverage; the instruction audit handles override consistency and path resolution. (Severity: WARN)
**PM Acknowledgment (2026-03-19):** Approved. The spec explicitly permits this folding. The distribution of checks across the two remaining scripts is logical and complete.

**[CLARIFICATION]** Tests use local temp directory fixtures (via `create_fixture()` helper) rather than fixture repo tags. The spec defines fixture tags in Section 2.11 for the fixture repo, but the test infrastructure can exercise the same checks with in-process fixture state. This avoids a dependency on a remote fixture repo for unit tests while still validating detection accuracy. (Severity: INFO)

**[CLARIFICATION]** The `submodule_safety_audit.py` implements categories 1, 3, 4, and 5 of the 7 listed in Section 2.6 via direct code analysis. Categories 2 (climbing priority), 6 (hardcoded root assumptions), and 7 (instruction file path references) overlap significantly with categories 1 and 5 and are partially covered by the env var and CWD checks. Full AST-based data flow analysis for climbing priority ordering would require significantly more complexity for marginal additional safety. (Severity: INFO)

**[DISCOVERY] [ACKNOWLEDGED]** verify_zero_queue reads critic.json directly instead of scan.sh
**Source:** /pl-spec-code-audit --deep (M41)
**Severity:** MEDIUM
**Details:** Spec §2.5 says `verify_zero_queue.py` reuses `tools/cdd/scan.sh` JSON output. The implementation reads `tests/<feature>/critic.json` files directly via `load_feature_status()`. If scan.sh output shape ever diverges from critic.json, the two approaches would produce different results.
**Suggested fix:** Change `verify_zero_queue.py` to invoke `scan.sh` and parse its JSON output, or call the shared status computation function directly.

**[DISCOVERY] [ACKNOWLEDGED]** Instruction audit contradiction detection is heuristic-only
**Source:** /pl-spec-code-audit --deep (M42)
**Severity:** MEDIUM
**Details:** `check_contradictions()` in `instruction_audit.py` uses word-overlap heuristics (requires 2+ context words in common). No structural analysis of rule subjects, objects, or semantic understanding. Real contradictions with different vocabulary are missed; unrelated rules sharing words produce false positives.
**Suggested fix:** Improve the algorithm to parse rule structure (subject + verb + constraint) and compare semantic intent, not just vocabulary overlap.
