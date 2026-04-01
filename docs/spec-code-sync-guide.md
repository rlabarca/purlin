# Spec-Code Sync Guide

Purlin keeps specs and code in sync through one mechanism: **rules in specs, proofs in tests**.

## How It Works

```
Spec (RULE-1, RULE-2)  →  Tests (@proof markers)  →  Proof files  →  sync_status
```

- A spec defines rules: `RULE-1: passwords must be hashed with bcrypt`
- A test proves a rule: `@pytest.mark.proof("login", "PROOF-1", "RULE-1")`
- The test runner emits a proof file: `specs/auth/login.proofs-default.json`
- `sync_status` diffs rules against proofs and tells you what's missing

No tracking system. No ledger. The filesystem is the state.

## Spec Format

```markdown
# Feature: login

> Requires: i_security_policy
> Scope: src/auth/login.js, src/auth/session.js

## What it does
User authentication with email and password.

## Rules
- RULE-1: Passwords are hashed with bcrypt before storage
- RULE-2: Failed logins are rate-limited to 5 per minute
- RULE-3: Sessions expire after 30 minutes of inactivity

## Proof
- PROOF-1 (RULE-1): Store a password; verify bcrypt hash in database
- PROOF-2 (RULE-2): Submit 6 invalid passwords; verify the 6th returns 429
- PROOF-3 (RULE-3): Create session, wait 31 minutes, verify token rejected
```

**`## Rules`** — parsed by `sync_status`. Must use `RULE-N:` format.
**`## Proof`** — NOT parsed (except `@manual` stamps). It's a blueprint for the agent writing tests.
**`> Requires:`** — other specs/invariants whose rules also apply to this feature.
**`> Scope:`** — files this feature covers. Used for manual proof staleness detection.

Full format: `references/formats/spec_format.md`

## Reading sync_status

```
purlin:status
```

Output:
```
login: 2/3 rules proved
  RULE-1: PASS (PROOF-1 in test_login.py)
  RULE-2: PASS (PROOF-2 in test_login.py)
  RULE-3: NO PROOF
  → Fix: write a test with @pytest.mark.proof("login", "PROOF-3", "RULE-3")
  → Run: purlin:unit-test
```

Every problem has a `→` directive telling you exactly what to do. Follow the directives until all rules show PASS.

## Coverage States

| State | Meaning | Action |
|-------|---------|--------|
| READY | All rules proved | `→ No action needed` or `purlin:verify` to ship |
| PASS | Rule has a passing proof | None |
| FAIL | Rule has a failing proof | Fix the code or the test |
| NO PROOF | No test linked to this rule | Write a test with a proof marker |
| MANUAL PROOF STALE | Manual stamp exists but code changed since | Re-verify manually |
| MANUAL PROOF NEEDED | Manual proof declared but not stamped | Verify by hand, then stamp |

## Verification Receipts

When all rules are proved, `purlin:verify` runs the full test suite and issues a receipt:

```
verify: [Complete:all] features=3 vhash=f7a2b9c1
```

The `vhash` is `sha256(sorted rule IDs + sorted proof IDs/statuses)`. It proves these rules had these test outcomes. CI `--audit` mode re-runs all tests independently to confirm.

## Required Specs and Invariants

`> Requires: i_security_policy` means the invariant's rules apply to this feature too. `sync_status` includes required rules in the coverage report. Tests must prove both the feature's own rules and required rules.

Invariants are read-only — see the [Invariants Guide](invariants-guide.md).
