# Implementation Notes: Spec-Code Audit

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|
| (see prose) | [ACKNOWLEDGED]** test_support test file missing 3 state fields | DISCOVERY | PENDING |

*   **Tool Location:** `.claude/commands/pl-spec-code-audit.md` (agent skill command file)
*   **Test Location:** `tests/pl_spec_code_audit/test_command.py`
*   The command is an agent instruction file, not executable code. Tests verify that the command file contains the correct instructions, keywords, structural elements, and referenced infrastructure for all 54 automated scenarios.
*   The command file originally referenced "9 gap dimensions" in two places; corrected to "10", then extended to "12" with the addition of Requirement Hygiene (dimension 11) and Code Ownership (dimension 12). The spec's Gap Dimensions Table and all command file references now list 12 dimensions. Now updated to 12 dimensions with the addition of Dimension 12 (Code ownership).

### Test Quality Audit
- Rubric: 6/6 PASS
- Tests: 147 total, 147 passed
- AP scan: clean
- Date: 2026-03-23

### Phase 0.5 Heuristic Ranking Rationale

The ownership heuristic chain (H1-H6) is ranked by signal reliability:

*   **H1-H2 (HIGH):** Explicit path references in companion or spec files are the most reliable because they represent intentional documentation by Engineer mode or PM. These are exact-match lookups.
*   **H3 (HIGH, deep only):** Test import tracing requires reading source but provides a strong ownership signal -- if a feature's test suite imports a file, that file is part of the feature's implementation. Restricted to deep mode because it requires parsing source files.
*   **H4 (HIGH):** The skill file naming convention (`pl-<name>.md` -> `pl_<name>.md`) is a project-enforced invariant, making it as reliable as an explicit reference.
*   **H5 (MEDIUM):** Directory convention mapping (e.g., `pl_help` -> `tools/help/`) is reliable when directory structures are well-organized but can produce false positives in flat directory layouts or when multiple features share a directory.
*   **H6 (LOW, deep only):** Name similarity is the weakest signal -- substring matching can produce spurious links. Used only as a last resort and flagged as "weak ownership" in audit output.

### False Positive Mitigation Strategy

Three independent mechanisms layer to reduce noise:

1.  **Infrastructure exclusion list** targets files that exist in nearly every Python/JS project and are never feature-specific. The list (`__init__.py`, `conftest.py`, `*_utils.*`, build system files) can be extended via `.purlin/config.json` `audit_infra_patterns` if a project has additional boilerplate.
2.  **Import fan-in threshold** (3+ features) prevents shared utility modules from being flagged as orphaned. The threshold of 3 was chosen because a module imported by only 1-2 features should be co-owned by those features; a module imported by 3+ is genuinely cross-cutting infrastructure.
3.  **Confidence-weighted ownership** ensures that weak heuristic matches (H5/H6) suppress the gap finding but still surface in the audit table as review items. This avoids both false positives (marking genuinely owned code as orphaned) and false negatives (silently accepting a weak match without human verification).
*   The command is an agent instruction file, not executable code. Tests verify that the command file contains the correct instructions, keywords, structural elements, and referenced infrastructure for all 33 automated scenarios.
*   The command file originally referenced "9 gap dimensions" in two places; corrected to "10", then extended to "12" with the addition of Requirement Hygiene (dimension 11) and Code Ownership (dimension 12). The spec's Gap Dimensions Table and all command file references now list 12 dimensions.

**[DISCOVERY] [ACKNOWLEDGED]** test_support test file missing 3 state fields
**Source:** /pl-spec-code-audit --deep (M15)
**Severity:** MEDIUM
**Details:** `tools/test_support/test_pl_spec_code_audit.py` `TestCrossSessionResume.test_state_file_tracks_required_fields` checks for 7 fields but omits `timestamp`, `code_inventory`, and `ownership_map_complete`. The newer `tests/pl_spec_code_audit/test_command.py` correctly checks all 10.
**Suggested fix:** Add the 3 missing fields to the older test file's assertion list.
