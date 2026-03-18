## Implementation Notes

### Intra-Phase Mode
Added `--intra-phase <N>` CLI argument via argparse. The `compute_feature_independence()` function follows the same grouping pattern as `group_parallel_phases()` but operates on features within a single phase rather than on phases.

### parse_delivery_plan() Signature Change
Added optional `include_statuses` parameter (default `{'PENDING'}`). Default mode is unchanged. Intra-phase mode passes `{'PENDING', 'IN_PROGRESS'}` since both are valid targets per spec Section 2.9.

### Test Quality Audit
- Deletion test: Each test verifies specific behavioral output from the analyzer. Deleting `compute_feature_independence()` would cause all 5 intra-phase tests to fail.
- AP-1 (tautology): Tests assert specific JSON structure and values, not mere existence.
- AP-2 (echo): Tests verify computed output (grouping, ordering), not input reflection.
- AP-3 (mock-only): Tests run the actual `phase_analyzer.py` script as a subprocess.
- AP-4 (flag-check): Tests verify behavioral outcomes (exit codes, JSON structure, dependency relationships).
- AP-5 (constant): Tests use fixture data with known dependency structures.
