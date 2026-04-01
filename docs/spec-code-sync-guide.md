# Spec-Code Sync Guide

The rule-proof model is Purlin's core mechanism for keeping specs and code in sync.

## The Model

```
Spec --> Rules --> Proofs --> sync_status
```

1. **Specs** describe what a feature does and define testable rules.
2. **Rules** are numbered constraints (`RULE-1`, `RULE-2`, ...) that code must satisfy.
3. **Proofs** are test results linked to rules via proof markers. Test runners emit proof JSON files.
4. **`sync_status`** diffs rules against proofs and reports coverage with actionable directives.

## Spec Format (3 sections)

```markdown
# Feature: feature_name

> Requires: other_spec, i_invariant_name
> Scope: src/feature.js, src/feature.test.js

## What it does
One paragraph explaining purpose and motivation.

## Rules
- RULE-1: First testable constraint
- RULE-2: Second testable constraint

## Proof
- PROOF-1 (RULE-1): Observable assertion for rule 1
- PROOF-2 (RULE-2): Observable assertion for rule 2
```

### Metadata

- **`Requires:`** — other specs whose rules also apply. Commonly used for invariants.
- **`Scope:`** — files this spec covers. Used for manual proof staleness detection.

## How sync_status Works

The `sync_status` MCP tool:

1. Scans `specs/**/*.md` for `## Rules` sections, extracts `RULE-N` entries.
2. Scans `specs/**/*.proofs-*.json` for proof results.
3. Matches proofs to rules by feature name and rule ID.
4. Reports coverage per feature with directives.

### Coverage States

| State | Meaning |
|-------|---------|
| `READY` | All rules proved, vhash computed |
| `PASS` | This rule has a passing proof |
| `FAIL` | This rule has a failing proof |
| `NO PROOF` | No test is linked to this rule |
| `MANUAL PROOF STALE` | Manual stamp exists but scope files changed |
| `MANUAL PROOF NEEDED` | Manual proof declared but not yet stamped |

### Directives

`sync_status` output includes directives that tell the agent exactly what to do:

- `Fix: write a test with @pytest.mark.proof(...)` — a rule needs a proof
- `Fix: test_name is failing` — a proof is failing
- `Run: purlin:unit-test` — run tests to emit proofs
- `Run: purlin:spec feature_name` — spec needs rules
- `No action needed.` — feature is fully proved

## Required Invariants

When a spec has `> Requires: i_design_colors`, the invariant's rules appear in `sync_status` output for that feature. Tests must prove both own rules and required rules.

## Verification Receipts

When `purlin:verify` runs tests and all rules pass, it writes a receipt:

```
specs/<category>/feature_name.receipt.json
```

The receipt includes a `vhash` (verification hash) computed from sorted rule IDs and proof statuses. This serves as a tamper-evident proof that all rules were covered at a specific point in time.
