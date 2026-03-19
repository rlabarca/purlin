## Implementation Notes

### Intra-Phase Mode
Added `--intra-phase <N>` CLI argument via argparse. The `compute_feature_independence()` function follows the same grouping pattern as `group_parallel_phases()` but operates on features within a single phase rather than on phases.

### parse_delivery_plan() Signature Change
Added optional `include_statuses` parameter (default `{'PENDING'}`). Default mode is unchanged. Intra-phase mode passes `{'PENDING', 'IN_PROGRESS'}` since both are valid targets per spec Section 2.9.

