# Discovery Sidecar: regression_testing

### [BUG] M33: Runner doesn't capture stderr (Discovered: 2026-03-23)
- **Scenario:** features/regression_testing.md:Once mode runs single harness invocation
- **Observed Behavior:** No `stderr_excerpt` was included in the result when claude is unavailable or produces errors. The `execute_harness()` function in `dev/regression_runner.sh` did not redirect stderr to a capture file, so stderr output was lost from the result JSON.
- **Expected Behavior:** The runner should capture stderr output and include a `stderr_excerpt` field in the result object, per spec Section 2.1 ("record exit_code and include the stderr excerpt in regression_result.json").
- **Action Required:** Builder
- **Status:** RESOLVED
- **Resolution:** Added stderr capture via temp file redirect (`2>"$stderr_tmpfile"`) in all three timeout dispatch paths (gtimeout, timeout, macOS fallback). The captured stderr is truncated to ~1000 chars via `head -c 1000` and included as `stderr_excerpt` in the result JSON only when non-empty. Stderr is still echoed to the terminal for visibility. Added 4 unit tests covering: failure with stderr, success without stderr, claude unavailability errors, and truncation of long stderr.

### [BUG] M35: pl-verify 2.2.4 regression table untested (Discovered: 2026-03-23)
- **Scenario:** features/regression_testing.md:Staleness detection prioritizes re-testing
- **Observed Behavior:** No unit tests existed for the status table rendering or hard gate logic in pl-verify regression section.
- **Expected Behavior:** Unit tests should cover regression status table rendering and hard gate pass/fail logic.
- **Action Required:** Builder
- **Status:** RESOLVED
- **Resolution:** Added `TestCompletionGate` class with 11 tests covering: gate pass/fail logic (5 tests for various result states), status table rendering (3 tests for PASS/FAIL/multi-feature tables), and hard gate blocking semantics (3 tests verifying FAIL blocks, PASS allows, None allows completion). Also added `TestStalenessDetectionExpanded` class with 5 tests covering expanded staleness scenarios: implementation file staleness, all-sources-older non-staleness, missing tests.json (NOT_RUN), sorting priority, and companion file exemption.
