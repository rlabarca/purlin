# Feature: proof_plugins_jest

> Requires: proof_common, schema_proof_format, security_no_dangerous_patterns
> Scope: scripts/proof/jest_purlin.js
> Stack: node/jest, custom reporter (onTestResult + onRunComplete hooks)
> Description: The Jest proof reporter. Parses `[proof:...]` markers from test titles and
>   emits standardized proof JSON. Inherits all shared proof-plugin behavior from proof_common.

## What it does

A Jest reporter that scans each test title for a `[proof:...]` marker, maps the Jest result
status to pass/fail, and writes one proof file per feature/tier. Only the Jest-specific marker
syntax, title handling, path resolution, and status mapping live here.

## Rules

- RULE-1: The marker is parsed from the test title using the pattern `[proof:feature:PROOF-N:RULE-N:tier]` where tier defaults to `"unit"`
- RULE-2: Test names without a `[proof:...]` marker are ignored
- RULE-3: `test_file` is recorded as the path relative to Jest's `rootDir`
- RULE-4: Jest status `"passed"` maps to `"pass"` and all other executed statuses map to `"fail"`; a skipped, pending, todo or disabled test did not execute, so it writes nothing and keeps its committed entry (`proof_common` RULE-18)

## Proof

- PROOF-1 (RULE-1): Create a test `it("works [proof:feat:PROOF-1:RULE-1:unit]", ...)`; run Jest; verify proof entry has `feature: "feat"`, `id: "PROOF-1"`, `rule: "RULE-1"` @e2e
- PROOF-2 (RULE-2): Create a test without `[proof:...]` in the title; run Jest; verify no proof entry is emitted for that test @e2e
- PROOF-3 (RULE-3): Run Jest; verify `test_file` is relative to `rootDir` @e2e
- PROOF-4 (RULE-4): Create a failing Jest test with a proof marker; verify `status` is `"fail"` @e2e
- PROOF-5 (RULE-4): Run the reporter over a test file whose only marked test reports status `pending`, against a proof file that already holds a `pass` entry for that id from another host; verify the reporter writes no entry for the pending test and leaves the existing file byte-identical, so the committed entry survives; a reporter that maps `pending` to `fail`, or that reaps the entry, fails @integration
