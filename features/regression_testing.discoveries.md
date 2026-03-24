# User Testing Discoveries: Regression Testing

### [BUG] M33: Runner doesn't capture stderr (Discovered: 2026-03-23)
- **Observed Behavior:** No `stderr_excerpt` is included in the result when claude is unavailable or produces errors.
- **Expected Behavior:** The runner should capture stderr output and include a `stderr_excerpt` field in the result object when errors occur.
- **Action Required:** Builder
- **Status:** OPEN
- **Source:** Spec-code audit (deep mode). See regression_testing.impl.md for full context.

### [BUG] M35: pl-verify 2.2.4 regression table untested (Discovered: 2026-03-23)
- **Observed Behavior:** There are no unit tests for the status table rendering or hard gate logic in the pl-verify regression section (2.2.4).
- **Expected Behavior:** Unit tests should cover the regression status table rendering and the hard gate pass/fail logic.
- **Action Required:** Builder
- **Status:** OPEN
- **Source:** Spec-code audit (deep mode). See regression_testing.impl.md for full context.
