# Testing Lifecycle Reference

Authoritative reference for the complete testing lifecycle across all three Purlin modes. Shows how each test category flows through define, implement, verify, and complete — and how failures route between personas.

For result schemas, harness types, and assertion tiers, see `test_infrastructure.md`.

---

## 1. Test Categories

| Category | Defined By | Implemented By | Run By | Verified By | Output File |
|----------|-----------|---------------|--------|-------------|-------------|
| Unit Tests | Engineer (spec `### Unit Tests`) | Engineer (test code) | Engineer (build Step 3, auto) | Engineer (test runner) | `tests/<f>/tests.json` |
| QA Scenarios (@auto) | PM (spec `### QA Scenarios`) | QA (regression JSON) | QA (harness runner, auto) | QA (regression.json eval) | `tests/<f>/regression.json` |
| QA Scenarios (@manual) | PM (spec `### QA Scenarios`) | N/A (human protocol) | QA (presents to user) | User + QA (checklist) | Discovery sidecars |
| Smoke Regressions | QA (promotes critical-path) | QA (`_smoke.json`) | QA (Phase A Step 2, auto) | QA (halt-on-fail gate) | `tests/<f>/regression.json` |
| Visual Spec | PM (spec `## Visual Specification`) | Engineer (web test setup) | QA (`purlin:web-test`, auto) | QA (screenshot + Figma) | Screenshots, discoveries |
| Web Tests | Engineer (spec `> Web Test:`) | Engineer (Playwright) | Engineer (build) + QA (verify) | Both (different phases) | Web test results |

**Key distinction:** PM defines WHAT to test (abstract scenarios in Gherkin). QA decides HOW to test (harness type, assertions, @auto/@manual classification). Engineer writes code that makes tests pass. PM does not need to know harness capabilities; QA does not need to understand implementation details.

---

## 2. Lifecycle Phases

```
Phase       | PM                  | Engineer             | QA
------------+---------------------+----------------------+----------------------
            |                     |                      |
DEFINE      | Write QA Scenarios  |                      |
            | (what to test)      |                      |
            | Write Visual Spec   |                      |
            | Regression Guidance |                      |
            |         |           |                      |
            |         v           |                      |
IMPLEMENT   |                     | Write code           |
            |                     | Write unit tests     |
            |                     | Run unit tests -->   |
            |                     |   tests.json         |
            |                     | Run web tests        |
            |                     |   (if visual spec)   |
            |                     |         |            |
            |                     |         v            |
            |                     | Mark [Testing] ----->|
            |                     |                      |
PREPARE     |                     |                      | Classify scenarios
(QA setup)  |                     |                      |   (@auto / @manual)
            |                     |                      | Author regression JSON
            |                     |                      | Author smoke JSON
            |                     |                      | Readiness check (0c)
            |                     |                      |         |
            |                     |                      |         v
VERIFY      |                     |                      | Run smoke gate (halt)
(automated) |                     |                      | Run @auto scenarios
            |                     |                      | Run regression suites
            |                     |                      | Visual verification
            |                     |                      |         |
            |                     |                      |    failures?
            |                     |                      |    +----+----+
            |                     |                      |   no        yes
            |                     |                      |    |    +----v----+
            |                     |                      |    |    |AUTO-FIX |
            |                     |  <-- internal mode --+    |    |  LOOP   |
            |                     |  fix code/tests      |    |    | (max 5) |
            |                     |  -- internal mode -->|    |    +----+----+
            |                     |                      |    |         |
            |                     |                      |    v         v
VERIFY      |                     |                      | Manual checklist
(manual)    |                     |                      | Record discoveries
            |                     |                      |         |
            |                     |                      |         v
COMPLETE    |                     |                      | Mark [Complete][Verified]
            |                     |                      |
------------+---------------------+----------------------+----------------------
ESCALATION  | <-- spec dispute,   | <-- code bug         | <-- stale test
PATHS       |     intent drift    |     from QA          |     from Engineer
            |     Resolve spec    |     Fix code         |     Fix scenario JSON
            |     --> re-verify   |     --> re-verify    |     --> re-run
```

### Phase Details

**DEFINE (PM):** PM writes QA Scenarios in Gherkin in the feature spec. Scenarios describe observable behavior, not implementation. PM optionally writes Regression Guidance suggesting what to focus on. PM writes Visual Specification with design references for UI features.

**IMPLEMENT (Engineer):** Engineer reads the spec and writes code + unit tests. Unit tests run automatically during build Step 3 and produce `tests.json`. For features with visual specs and `> Web Test:` metadata, Engineer also runs `purlin:web-test` during build. Engineer marks the feature `[Testing]` when implementation is complete.

**PREPARE (QA):** QA classifies PM's scenarios as `@auto` (automatable via harness) or `@manual` (requires human verification). QA authors regression JSON (`tests/qa/scenarios/<feature>.json`) with harness type, assertions, and fixture tags. For smoke-tier features, QA authors `_smoke.json` with a subset of critical scenarios. Step 0c validates all @auto scenarios have regression JSON before tests begin.

**VERIFY — automated (QA):** Step 2 runs smoke tests (halt on failure). Step 3 runs @auto scenarios via the harness runner. Regression suites run in-session. Failures are recorded as `[BUG]` discoveries.

**VERIFY — auto-fix loop (QA + Engineer):** When `--auto-verify` is active and automated tests failed, the agent iterates: Engineer fixes code bugs, QA fixes stale test assertions, re-run failed tests only. Max 5 iterations. See Section 3.

**VERIFY — manual (QA):** Phase B presents remaining @manual scenarios and visual items as a checklist. User reports pass/fail. Failures are classified as BUG, DISCOVERY, INTENT_DRIFT, or SPEC_DISPUTE.

**COMPLETE (QA):** Features where all tests pass and zero discoveries are open are marked `[Complete] [Verified]`.

---

## 3. Auto-Fix Loop Detail

The auto-fix iteration loop (Phase A.5) crosses the QA/Engineer boundary to resolve automated test failures without manual intervention.

### Per-Iteration Structure

```
+--------------------------------------------------+
| Iteration N (max 5)                              |
|                                                  |
| 1. Collect all FAIL results                      |
|    (skip PASS, ESCALATED)                        |
|                                                  |
| 2. ENGINEER FIX PHASE                            |
|    - Internal switch to Engineer                 |
|    - Read failure details + source code          |
|    - Diagnose: code bug / stale test / spec gap  |
|    - Fix code bugs, flag stale tests for QA      |
|    - Escalate spec issues to PM                  |
|    - Commit fixes, update companion files        |
|                                                  |
| 3. QA FIX PHASE                                  |
|    - Internal switch to QA                       |
|    - Fix stale test assertions flagged by Eng    |
|    - Commit scenario updates                     |
|                                                  |
| 4. RE-RUN                                        |
|    - Run ONLY failed scenario files              |
|    - Passed scenarios are cached (not re-run)    |
|    - Update failure tracker                      |
|                                                  |
| 5. CHECK ESCALATIONS                             |
|    - Same failure signature twice -> escalate    |
|    - Zero progress this iteration -> early exit  |
+--------------------------------------------------+
```

### Failure Diagnosis Decision Tree

When Engineer examines a failure during the fix phase:

```
Read regression.json: expected, actual_excerpt, scenario_ref
Read source code referenced by scenario_ref
Read test scenario assertions
                    |
                    v
    +--- Is the CODE wrong? ---+
    |                          |
   yes                         no
    |                          |
    v                          v
Fix source code         +--- Is the TEST wrong? ---+
Commit: fix(scope)      |                          |
                        yes                         no
                         |                          |
                         v                          v
Flag for QA fix         ESCALATE to PM
(stale test)            Record [SPEC_DISPUTE]
                        or [INTENT_DRIFT]
```

### Internal Mode Switch

The auto-fix loop uses lightweight internal mode switches (defined in `purlin:verify`):
- Terminal badge stays "QA" throughout — rapid mode flips are invisible to the user.
- Write-boundary enforcement remains active. Mode guard still checks file classification.
- Companion file gate runs when leaving Engineer (fixes must be documented).
- Pending work is committed before each switch.

---

## 4. Test File Ownership Map

### Engineer-Owned (CODE)

| File | Purpose | Produced By |
|------|---------|-------------|
| `tests/<f>/test_*.py` | Unit test code | Engineer (written by hand) |
| `tests/<f>/test_*.sh` | Shell test code | Engineer (written by hand) |
| `tests/<f>/tests.json` | Unit test results | Test runner (pytest, jest, etc.) |

### QA-Owned

| File | Purpose | Produced By |
|------|---------|-------------|
| `tests/qa/scenarios/<f>.json` | Regression scenario declarations | QA (authored) |
| `tests/qa/scenarios/<f>_smoke.json` | Smoke regression scenarios | QA (authored) |
| `tests/<f>/regression.json` | Regression test results | Harness runner (auto-generated) |
| `features/<f>.discoveries.md` | Discovery sidecars | QA (any mode can add OPEN entries) |

### PM-Owned (SPEC)

| File | Purpose |
|------|---------|
| `features/<f>.md` `### QA Scenarios` | Scenario definitions (what to test) |
| `features/<f>.md` `## Visual Specification` | Visual design checklists |
| `features/<f>.md` `## Regression Guidance` | Optional testing guidance for QA |

### Cross-References

- File classification rules: `file_classification.md`
- Result schemas and harness types: `test_infrastructure.md`
- Assertion tier definitions: `test_infrastructure.md` Section "Assertion Tiers"

---

## 5. Failure Routing

When a test fails, diagnosis determines who resolves it:

```
Test fails --> Diagnose
  |-- Code bug           --> Engineer fixes source code
  |-- Stale test         --> QA fixes scenario JSON assertions
  |-- Spec unclear       --> PM updates spec --> re-verify in future session
  |-- External dep       --> ESCALATE (manual resolution required)
  +-- Figma drift        --> PM re-ingests design
```

### Routing by Discovery Type

| Discovery Type | Routed To | Resolution |
|---------------|-----------|------------|
| `[BUG]` | Engineer | Fix code, re-run test |
| `[BUG] test-scenario:` | QA | Fix assertion pattern, re-run test |
| `[SPEC_DISPUTE]` | PM | Resolve spec intent, re-verify |
| `[INTENT_DRIFT]` | PM | Align spec with actual intent, re-verify |
| `[DISCOVERY]` | PM or Engineer | Evaluate, decide on spec/code change |

### Escalation Re-Entry

Tests escalated to PM during the auto-fix loop are not abandoned. The lifecycle continues:
1. PM receives the discovery via scan results / `purlin:status`.
2. PM resolves the spec (updates scenario, clarifies intent, or confirms current behavior is correct).
3. In a future session, QA re-runs `purlin:verify` — the resolved spec guides new assertions.

---

## 6. Deduplication Rules

- **QA does NOT re-verify Engineer-completed Unit Tests.** Unit tests run during build and their results (`tests.json`) are trusted. QA scenarios test different concerns (behavioral, integration, end-to-end).
- **Web-test visual dedup:** Features with `> Web Test:` metadata have visual items verified by Engineer during build and by QA in Phase A Step 5. These items are excluded from the Phase B manual checklist.
- **Smoke is a tier, not a separate test type.** A smoke regression (`_smoke.json`) is a subset of the full regression (`<feature>.json`). Both produce results in `regression.json`. Smoke runs first and gates further verification.
