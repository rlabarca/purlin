# Discovery Sidecar: regression_testing

### [BUG] M33: Runner doesn't capture stderr (Discovered: 2026-03-23)
- **Scenario:** features/regression_testing.md:Once mode runs single harness invocation
- **Observed Behavior:** No `stderr_excerpt` was included in the result when claude is unavailable or produces errors. The `execute_harness()` function in `scripts/test_support/regression_runner.sh` did not redirect stderr to a capture file, so stderr output was lost from the result JSON.
- **Expected Behavior:** The runner should capture stderr output and include a `stderr_excerpt` field in the result object, per spec Section 2.1 ("record exit_code and include the stderr excerpt in regression_result.json").
- **Action Required:** Engineer
- **Status:** RESOLVED
- **Resolution:** Added stderr capture via temp file redirect (`2>"$stderr_tmpfile"`) in all three timeout dispatch paths (gtimeout, timeout, macOS fallback). The captured stderr is truncated to ~1000 chars via `head -c 1000` and included as `stderr_excerpt` in the result JSON only when non-empty. Stderr is still echoed to the terminal for visibility. Added 4 unit tests covering: failure with stderr, success without stderr, claude unavailability errors, and truncation of long stderr.

### [BUG] M35: pl-verify 2.2.4 regression table untested (Discovered: 2026-03-23)
- **Scenario:** features/regression_testing.md:Staleness detection prioritizes re-testing
- **Observed Behavior:** No unit tests existed for the status table rendering or hard gate logic in pl-verify regression section.
- **Expected Behavior:** Unit tests should cover regression status table rendering and hard gate pass/fail logic.
- **Action Required:** Engineer
- **Status:** RESOLVED
- **Resolution:** Added `TestCompletionGate` class with 11 tests covering: gate pass/fail logic (5 tests for various result states), status table rendering (3 tests for PASS/FAIL/multi-feature tables), and hard gate blocking semantics (3 tests verifying FAIL blocks, PASS allows, None allows completion). Also added `TestStalenessDetectionExpanded` class with 5 tests covering expanded staleness scenarios: implementation file staleness, all-sources-older non-staleness, missing tests.json (NOT_RUN), sorting priority, and companion file exemption.

### [BUG] harness_runner write_results does not persist agent_behavior regression results (Discovered: 2026-03-25)
- **Scenario:** Harness runner result file persistence (all agent_behavior suites)
- **Observed Behavior:** When `harness_runner.py` runs an `agent_behavior` suite externally (user terminal), it prints correct pass/fail counts and "Results: <path>" to stdout, but the regression.json file on disk retains the previous run's content. Verified via `stat` (mtime unchanged) and direct `python3 json.load()` (old data). Both the Claude Code session and the user's terminal see the stale file. The harness clearly executes `write_results()` (the print statements after it fire), yet the file is not updated.
- **Expected Behavior:** `regression.json` reflects the latest run's results immediately after the harness exits.
- **Action Required:** None.
- **Status:** RESOLVED — Root cause: OS-level buffering on macOS. `json.dump` + `close()` flushes Python buffers but doesn't guarantee disk persistence. Added `f.flush()` + `os.fsync(f.fileno())` to `write_results()` to force the write to disk before returning (2026-03-28).
