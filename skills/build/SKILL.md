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
2. Read the spec. Extract all `RULE-N` entries from `## Rules`.
3. Read all `> Requires:` specs (including invariants in `specs/_invariants/`). Collect their rules too.
4. For design invariants with `> Source: <figma-url>`, read the Figma file via MCP (`get_design_context`) to get visual context for implementation.

Display the combined rule set:

```
Building: <name>
Rules (own): RULE-1, RULE-2, RULE-3
Rules (from i_design_tokens): RULE-1, RULE-2
Rules (from api_contracts): RULE-1
Scope: src/auth.js, src/auth.test.js
```

## Step 2 — Implement

Write code that satisfies all rules. Use `> Scope:` paths as guidance for where to write.

- Implement the feature naturally — there is no required order or ceremony.
- Keep the rules visible. If a rule constrains behavior, make sure the code satisfies it.
- If implementation reveals that a rule is wrong or missing, update the spec (this is expected).

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

Each RULE must have at least one PROOF. The proof plugin emits `<feature>.proofs-<tier>.json` next to the spec file.

## Step 4 — Run Tests

Run the test suite. Check that proof files were emitted and rules are covered.

```bash
pytest                    # or: npx jest, or: bash test.sh
```

Call `sync_status` to verify coverage. Follow any `→` directives for uncovered rules.

## Step 5 — Commit

```
git commit -m "feat(<name>): <description>"
```
