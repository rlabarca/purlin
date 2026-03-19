## Implementation Notes

### Intra-Phase Mode
Added `--intra-phase <N>` CLI argument via argparse. The `compute_feature_independence()` function follows the same grouping pattern as `group_parallel_phases()` but operates on features within a single phase rather than on phases.

### parse_delivery_plan() Signature Change
Added optional `include_statuses` parameter (default `{'PENDING'}`). Default mode is unchanged. Intra-phase mode passes `{'PENDING', 'IN_PROGRESS'}` since both are valid targets per spec Section 2.9.

### Audit Finding -- 2026-03-19

[DISCOVERY] Diagnostic output mixes stderr and stdout — Acknowledged

**Source:** /pl-spec-code-audit --deep (item #44)
**Severity:** LOW
**Details:** The spec does not explicitly define which output stream diagnostic/debug messages should use. Current implementation sends some diagnostic information to stdout mixed with primary output, which can interfere with piped usage (e.g., `phase_analyzer.py | jq`).
**Suggested fix:** Route all diagnostic/debug output to stderr and reserve stdout for structured (JSON) output only. This follows the Unix convention and matches the pattern used by other Purlin CLI tools (e.g., `status.sh` uses stderr for progress, stdout for JSON).

