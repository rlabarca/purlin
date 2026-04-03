---
name: build
description: Inject spec rules into context, then implement
---

Read a spec, load all its rules (including from `> Requires:` dependencies), and implement the feature.

## Usage

```
purlin:build <name>             Build a feature from its spec
purlin:build                    Resume building the current feature
```

## Step 1 — Load the Spec

1. Find the spec: `specs/**/<name>.md`.
2. Read the spec. Extract all `RULE-N` entries from `## Rules` and all `PROOF-N` entries from `## Proof`.
3. Read all `> Requires:` specs (including invariants in `specs/_invariants/`). Extract their `RULE-N` and `PROOF-N` entries too — both rules and proof descriptions are needed for implementation.
4. If the feature spec itself or any required spec (anchor or invariant) has a `> Visual-Reference:` field, load the visual reference at **full fidelity**:
   - `figma://fileKey/nodeId` → call `get_design_context` and `get_screenshot` MCP tools
   - `./path/to/image.png` → read the image file
   - `./path/to/file.html` → read the HTML file
   - `https://url` → take a screenshot via Playwright MCP if available
   - Display: `Visual reference loaded from: <source>`

Display the combined rule set with proof descriptions:

```
Building: <name>
Own rules: RULE-1, RULE-2, RULE-3
Required from api_rest_conventions:
  RULE-1: All endpoints return JSON with {data, error, meta} envelope
  PROOF-1: GET /endpoint returns {data: ..., error: null, meta: {}}
Required from i_design_modal:
  RULE-1: Implementation must visually match the Figma design
  PROOF-1: Screenshot comparison against Figma reference @e2e
  Visual reference loaded from: figma://ABC123/1:234
Scope: src/auth.js, src/auth.test.js
```

## Step 2 — Implement

Write code that satisfies all rules. Use `> Scope:` paths as guidance for where to write.

- Implement the feature naturally — there is no required order or ceremony.
- Keep the rules visible. If a rule constrains behavior, make sure the code satisfies it.
- If implementation reveals that a rule is wrong or missing, update the spec (this is expected).
- **When building a feature that requires a design invariant or anchor with `> Visual-Reference:`:**
  - Read the visual reference at FULL FIDELITY (Figma MCP, image file, etc.)
  - Build from the visual reference, not from rules — the invariant's rule just says "match the design," so the visual reference IS the spec
  - The visual reference captures everything: layout relationships, alignment, visual hierarchy, spacing proportions, colors, typography
  - Feature spec rules describe behavioral requirements — build those from the rules
  - When the visual reference and a behavioral rule conflict, the visual reference wins for visual implementation — but the behavioral rule must still be satisfied for verification

## Step 3 — Write Tests with Proof Markers

Write tests that prove each rule. Use proof markers so the test runner emits proof files.

**pytest:**
```python
@pytest.mark.proof("feature_name", "PROOF-1", "RULE-1")
def test_something():
    assert result == expected
```

**Jest:**
```javascript
it("does something [proof:feature_name:PROOF-1:RULE-1:default]", () => {
  expect(result).toBe(expected);
});
```

**Shell:**
```bash
source scripts/proof/shell_purlin.sh
purlin_proof "feature_name" "PROOF-1" "RULE-1" pass "description"
purlin_proof_finish
```

Each RULE must have at least one PROOF — both own rules AND required rules. For required rules, use the **required spec's feature name** in the proof marker, not your own feature name:

```python
# Own rule — uses YOUR feature name
@pytest.mark.proof("login", "PROOF-1", "RULE-1")

# Required rule from api_rest_conventions — uses THE ANCHOR's name
@pytest.mark.proof("api_rest_conventions", "PROOF-1", "RULE-1")
```

The proof plugin emits `<feature>.proofs-<tier>.json` next to the spec file.

**Tier review (mandatory before running tests):**
Review every proof marker just written. Apply tier heuristics from `references/spec_quality_guide.md`:
- Test hits API/database/filesystem/subprocess → `@slow`
- Test needs browser/UI rendering → `@e2e`
- Test needs human judgment → `@manual`
- Pure logic/in-memory → default (no tag)

If ANY proof marker is missing a tier tag and the test clearly isn't default tier (it calls subprocess, hits a network endpoint, etc.), add the tag before running.

After writing tests, ALWAYS spawn a purlin-auditor teammate to review proofs. Do NOT audit your own tests in the same context — the auditor must be independent. This applies regardless of the number of proofs.

## Step 4 — Run Tests and Iterate

The iteration loop is: **write code → write tests → run tests → call sync_status → read directives → fix → repeat**. The loop does NOT end until `sync_status` shows READY for the target feature.

```bash
pytest                    # or: npx jest, or: bash test.sh
```

After tests complete, call `sync_status` and display the full result. **This is not optional.** If `sync_status` is not called, the agent doesn't know if coverage is complete. Follow any `→` directives for uncovered rules.

**When a test fails, diagnose the root cause before fixing:**
1. Read the failing assertion — what did the test expect vs what did it get?
2. Read the spec rule the proof is linked to — is the test asserting the right behavior?
3. If the test is correct and the code is wrong → fix the code
4. If the test has a bug (wrong mock, wrong expected value) → fix the test
5. If the rule itself is wrong → update the spec first, then fix code and test

**Never weaken an assertion to make it pass.** If `assert response.status == 401` fails because the code returns 200, the code is wrong. See `references/spec_quality_guide.md` "When Tests Fail" for the full diagnostic guide.

**Assertion change detection (mandatory after fixing a failing test):**
After fixing a failing test, before running tests again, re-read the original proof description from the spec's `## Proof` section. Verify the assertion still matches. If the fix changed WHAT the test asserts (different status code, different field, looser check), flag it:

```
WARNING: Assertion for PROOF-2 (RULE-2) was changed during iteration.
Original proof description: "POST invalid password; verify 401"
New assertion: assert status == 400
Reason: API returns 400 for validation errors, not 401. Spec rule may need updating.
→ Run: purlin:spec <name> to review RULE-2
```

If you changed what a test asserts (not just how), the proof description in the spec may be wrong. The commit message MUST explain why the assertion changed.

## Teammate Mode

When running as a purlin-builder teammate in an agent team:

- Listen for messages from the purlin-auditor teammate
- When audit feedback arrives with HOLLOW or WEAK assessments:
  a. Read the specific finding (which proof, what's wrong, suggested fix)
  b. Read the spec's proof description for the affected proof
  c. Fix the test following the audit's suggestion
  d. Run purlin:unit-test to verify the fix doesn't break other proofs
  e. Message the auditor: "Fixed PROOF-N in <feature>. Re-audit please."
- Do NOT weaken assertions to satisfy audit — if the audit says a proof is HOLLOW because it mocks bcrypt, replace the mock with real bcrypt. Don't remove the assertion.
- If fixing a proof requires changing the spec rule (because the rule is wrong), message the lead instead of the auditor: "RULE-N in <feature> needs updating — <reason>. Can the reviewer handle this?"

## Step 5 — Commit

```
git commit -m "feat(<name>): <description>"
```
