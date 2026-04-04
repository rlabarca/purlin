---
name: status
description: Show rule coverage and actionable directives via sync_status
---

Call the `sync_status` MCP tool and display its output. The directives tell you exactly what to do next.

## Usage

```
purlin:status                   Show all features
purlin:status --role <role>     Filter by role (pm, dev, qa)
```

## Step 1 — Call sync_status

```
sync_status(role: <from argument, optional>)
```

## Step 2 — Display Output

The MCP tool returns a per-feature coverage report with `→` directives. Display it directly.

Example output from `sync_status`:

```
auth_login: VERIFIED
  3/3 rules proved
  vhash=a1b2c3d4
  → No action needed.

user_profile: 1/2 rules proved
  RULE-1: PASS (PROOF-1 in tests/test_profile.py)
  RULE-2: NO PROOF
  → Fix: write a test with @pytest.mark.proof("user_profile", "PROOF-2", "RULE-2")
  → Run: purlin:unit-test

webhook_delivery: 2/3 rules proved
  RULE-1: PASS (PROOF-1 in tests/test_webhook.py)
  RULE-2: PASS (PROOF-2 in tests/test_webhook.py)
  RULE-3: FAIL (PROOF-3 — test_retry_logic failed)
  → Fix: test_retry_logic is failing. Check the test or fix the code.
  → Run: purlin:unit-test

notification_system: no rules defined
  WARNING: No ## Rules section found.
  → Run: purlin:spec notification_system

design_tokens: 5 rules (global — auto-applied to all features)
  RULE-1: Font sizes use rem units
  RULE-2: Colors reference design token variables
  ...
```

## Step 3 — Summary

After the detailed output, show a one-line summary:

```
Summary: 4 features | 1 VERIFIED | 2 PARTIAL | 1 no rules
```

## The Directives

The `→` lines are the key output. They tell the agent (or user) exactly what action to take:

| Directive | Meaning |
|-----------|---------|
| `→ No action needed.` | Feature is fully proved |
| `→ Run: purlin:spec <name>` | Spec needs rules written |
| `→ Fix: rewrite as "- RULE-1: ..."` | Rules exist but aren't numbered |
| `→ Fix: write a test with @pytest.mark.proof(...)` | Rule has no proof |
| `→ Fix: <test_name> is failing` | Proof exists but test fails |
| `→ Run: purlin:unit-test` | Tests need to be run |
| `→ Re-verify and run: purlin:verify --manual ...` | Manual stamp is stale |
| `→ Verify manually, then run: purlin:verify --manual ...` | Manual proof needs stamping |
