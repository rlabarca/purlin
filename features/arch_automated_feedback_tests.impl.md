# Implementation Notes: Automated Feedback Tests

## Review: Spec Revision f383f70 (2026-03-16)

The FORBIDDEN section was restructured into two parts:

1. **`### FORBIDDEN`** now states "No grepable FORBIDDEN patterns defined for this anchor." This is correct — the Critic's `discover_forbidden_patterns()` in `tools/critic/policy_check.py` scans for `FORBIDDEN: <pattern>` lines. Since none exist, features anchored to this node correctly get zero policy violations (PASS).

2. **`### Behavioral Constraints (Non-Grepable)`** contains the actual constraints, now with explicit "Verification: QA review of test scripts" tags:
   - No human interaction during AFT execution
   - No AFT-owned server lifecycle (but harness-owned permitted via `> AFT Start:` metadata)

### Server Lifecycle Nuance

The revised constraint explicitly permits test infrastructure that starts a server BEFORE the AFT runs (e.g., `> AFT Start:` metadata). This is a relaxation from the previous blanket prohibition. The `/pl-aft-web` command (Step 3.5) uses `> AFT Start:` metadata for auto-start, which is compliant. Step 3.6 uses fixture-backed servers started by the AFT for testing — this is test infrastructure (fixture server, not the application), which is consistent with the intent.
