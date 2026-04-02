---
name: verify
description: Run all tests, issue verification receipts
---

Run the FULL test suite across all tiers, then issue verification receipts for every feature with complete rule coverage.

## Usage

```
purlin:verify                           Run all tests, issue receipts for all covered features
purlin:verify --audit                   Clean-room re-execution, compare vhash to committed receipt
purlin:verify --manual <feature> <PROOF-N>  Stamp a manual proof in the spec
```

## Default Mode — Full Verification

### Step 1 — Run All Tests

Run the full test suite (all tiers). The proof plugins emit `*.proofs-*.json` files next to specs.

```bash
# Detect framework from config or project files
pytest                    # Python
npx jest                  # JavaScript
bash test.sh              # Shell
```

### Step 2 — Collect Results

Call `sync_status` to get per-feature coverage. For each feature:

- **READY** (all rules have passing proofs): eligible for receipt.
- **Partial coverage**: report which rules lack proofs. No receipt.
- **Failing proofs**: report failures. No receipt.

### Step 3 — Issue Receipts

For each feature with READY status:

1. Compute `vhash = sha256(sorted RULE IDs + sorted proof IDs/statuses)` truncated to 8 hex chars.
2. Get `commit = git rev-parse HEAD`.
3. Write receipt to `specs/<category>/<feature>.receipt.json`:

```json
{
  "feature": "<name>",
  "vhash": "<8-char hex>",
  "commit": "<full sha>",
  "timestamp": "<ISO 8601>",
  "rules": ["RULE-1", "RULE-2"],
  "proofs": [
    {"id": "PROOF-1", "rule": "RULE-1", "status": "pass"},
    {"id": "PROOF-2", "rule": "RULE-2", "status": "pass"}
  ]
}
```

### Step 4 — Report

```
Verification complete: N/T features verified.

Receipts issued (N features):
  auth_login: vhash=a1b2c3d4 (3 rules, 3 proofs)
  user_profile: vhash=e5f6a7b8 (2 rules, 2 proofs)

No receipt (M features):
  webhook_delivery: 2/3 rules proved (RULE-3: NO PROOF)
  notification_system: RULE-1 FAIL
```

Where `N` is the number of features that received receipts and `T` is the total number of features (receipted + partial + failing). This fraction makes it obvious when the job is not complete.

### Step 4a2 — Structural-Only Coverage Summary

After issuing receipts, check if any READY features have structural-only coverage (sync_status reports them as `READY (structural only)`). If so, add a summary section after the receipts table:

```
Structural-only coverage (no behavioral proofs):
  purlin_agent (8 proofs — all grep/existence)
  purlin_skills (6 proofs — all grep/existence)
  purlin_references (9 proofs — all grep/existence)

These specs prove documents have the right content, not that the system follows them.
→ Consider: create specs/integration/e2e_purlin_lifecycle.md with @e2e proofs that test actual agent behavior
```

This is informational — not a gate. The receipts are still valid. The note makes it visible that the coverage is structural, not behavioral.

### Step 4b — Directive Block for Remaining Work

If ANY features are partial or failing (i.e., `N < T`), print a directive block **after** the receipts table:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠ M features still need tests before full verification:

  webhook_delivery (2/3 rules proved)
  → Run: test webhook_delivery

  notification_system (0/4 rules proved)
  → Run: test notification_system

Work through these, then run purlin:verify again.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

This block MUST:
1. List every partial/failing feature with its coverage count (`proved/total rules proved`)
2. Include a `→ Run:` directive for each one telling the agent which feature to test
3. End with `Work through these, then run purlin:verify again.`

The directive block ensures the agent does not stop after the first batch of receipts — it reads the remaining work and continues.

### Step 4c — Handling Failing Proofs

**NEVER modify code or test files during `purlin:verify`.** Verify is a read-only gate. If you find yourself about to edit a file during verify, STOP — you are in the wrong skill. Exit verify and switch to `purlin:build`.

When tests fail during verify:

1. Do NOT fix code or tests. Do NOT iterate. Report the failures with diagnosis and stop.
2. For each failing proof, output:
   - The rule it proves
   - What the test expected vs what it got
   - Diagnosis: is this likely a code bug, test bug, or spec drift?
   - Directive: `→ Run: test <feature>` to fix in the build loop

3. After reporting all failures, display the action block:

   ```
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ⚠ VERIFICATION INCOMPLETE — N proofs failing across M features.

   Fix these in the build loop, then run purlin:verify again:
     → Run: test <feature_1>
     → Run: test <feature_2>
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ```

### Step 5 — Commit

```
git commit -m "verify: [Complete:all] features=N/T vhash=<combined-hash>"
```

Where `N/T` is the verified/total count (e.g., `features=5/11`). The combined hash covers all individual vhashes: `sha256(sorted vhashes joined by comma)[:8]`.

---

## --audit Mode

Clean-room re-execution that compares results against committed receipts.

1. Run the full test suite (same as default mode).
2. Compute vhash for each feature.
3. Compare against existing `*.receipt.json` files.
4. Report: MATCH (receipt valid), MISMATCH (receipt stale — rules or proofs changed), MISSING (no receipt on file).

For CI integration: exit code 0 if all receipts match, exit code 1 if any mismatch or missing.

---

## --manual Mode

Stamp a manual proof in the spec's `## Proof` section.

```
purlin:verify --manual auth_login PROOF-3
```

1. Find the spec: `specs/**/auth_login.md`.
2. Read `git config user.email` and `git rev-parse HEAD`.
3. Find `PROOF-3` in the `## Proof` section.
4. Append `@manual(<email>, <YYYY-MM-DD>, <commit_sha>)` to the proof line:

```markdown
- PROOF-3 (RULE-3): User can log in via SSO @manual(dev@example.com, 2026-03-31, a1b2c3d)
```

5. Commit: `git commit -m "verify(<feature>): manual stamp PROOF-3"`

Manual stamps become stale when files in `> Scope:` are modified after the stamp's commit SHA. `sync_status` detects this and issues a `→ Re-verify` directive.
