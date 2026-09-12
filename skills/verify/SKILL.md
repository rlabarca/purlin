---
name: verify
description: Run all tests, issue verification receipts
---

Run the FULL test suite across all tiers, then issue verification receipts for every feature with complete rule coverage.

## Usage

```
purlin:verify                           Run all tests, issue receipts for all covered features
purlin:verify --recheck                   Clean-room re-execution, compare vhash to committed receipt
purlin:verify --manual <feature> <PROOF-N>  Stamp a manual proof in the spec
```

## Default Mode — Full Verification

### Pre-check: uncommitted changes

Before running verification, call sync_status. If it reports uncommitted spec/proof changes, warn the user:

"There are uncommitted spec/proof changes. Verification receipts reference committed state — uncommitted changes won't be included in the vhash. Commit first?"

If the user says yes, commit the changes. If no, proceed but note the receipts may not reflect current state.

### Step 1 — Run All Tests

Run the full test suite across all tiers by calling `purlin:test --all`. This handles framework detection, test execution, proof file emission, and the post-test sync_status call.

### Step 2 — Collect Results

Read the coverage output from `purlin:test --all` (which includes sync_status results). For each feature:

- **PASSING** (ALL rules have passing proofs, no receipt yet): eligible for receipt.
- **PARTIAL** (some rules proved, none failing): report which rules lack proofs. No receipt — all rules must be proved to reach PASSING.
- **FAILING** (any proof has status FAIL): report failures. No receipt.
- **UNTESTED** (no proof has executed for the feature at all): no receipt, and this is not a
  failure. Distinguish the two reasons, because the next step differs: when the files named in
  the spec's `> Scope:` do not exist, nothing has been built yet — report
  `→ Run: purlin:build <feature>`. When they do exist, the gap is tests —
  report `→ Run: purlin:test <feature>`. A project working spec-first will have every
  feature UNTESTED by design; say so plainly rather than reporting it as a shortfall, and
  point at `purlin:audit --design` for the gauge that is measurable in that state.

### External reference check (non-blocking)

Before issuing receipts, check if any required anchor has `> Source:` with a stale or missing `> Pinned:`. If so, warn:

```
⚠ Anchor <name> may be stale — external reference has not been synced recently.
  Verification proceeds, but consider running: purlin:anchor sync <name>
```

This is informational — it does not block receipt issuance.

### Step 3 — Issue Receipts

For each feature with PASSING status:

1. Compute the `vhash`. What it binds and how the segments are joined is stated
   once, in `specs/mcp/sync_status.md` RULE-6; never restate the formula here.
2. Get `commit = git rev-parse HEAD`.
3. Write receipt to `specs/<category>/<feature>.receipt.json` in the shape
   `references/formats/receipt_format.md` defines (version 2: `vhash_version`,
   `rule_hashes`, full proof identity, an `evidence` block and the optional
   `manual` and `awaiting_runner` lists). That file is the contract; this skill
   does not repeat it.

#### The run the receipt rests on

Do not issue a receipt without a recorded test run. The issuer refuses unless the
run marker exists, records a sweep that passed, and names the commit that is HEAD
now, because a receipt over proof files nobody re-ran is a claim about a file
rather than about a test. The override exists (`--no-run-check`) and it is not
silent: it warns, and the receipt records `evidence.test_run: null`.

A proof file that the recorded run did not execute and no runner committed is
evidence with no witness. The issuer names the file and the count and issues
nothing for that feature.

#### Platform-partial receipts

A feature declaring a proof `@on(windows-2022)` that has no result there still
earns a receipt: an absent runner is not a failure, and blocking on one would make
a receipt unobtainable on every machine but the runner. The receipt records the gap
in `awaiting_runner` instead, as the triple that names which proof, at which tier,
on which platform:

```json
"awaiting_runner": [{"id": "PROOF-53", "tier": "unit", "platform": "windows-2022"}]
```

so it never claims more than was verified. The key is omitted when nothing is
awaiting, so an ordinary receipt is unchanged. A receipt carrying it is a
verified-here claim, not a verified-everywhere one.
`sync_status` reports the same proofs as `AWAITING RUNNER`, and re-running verify
after CI commits the results clears the list. See `specs/skills/skill_verify.md`
RULE-9 and `specs/mcp/sync_status.md` RULE-47.

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

### Step 4a2 — Structural Check Summary

After issuing receipts, check if any features have structural checks but are not PASSING (structural checks are not counted as proofs). If so, add a summary section after the receipts table:

```
Features with structural checks only (not PASSING):
  purlin_agent (8 structural checks, 0 behavioral proofs)
  skill_build (6 structural checks, 0 behavioral proofs)
  purlin_references (9 structural checks, 0 behavioral proofs)

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
2. For each failing proof, diagnose using the framework in `references/spec_quality_guide.md` ("When Tests Fail"): is this a code bug, test bug, or spec drift? Output:
   - The rule it proves
   - What the test expected vs what it got
   - The diagnosis
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

### Step 4e — Independent Audit (automatic)

After issuing receipts, ALWAYS spawn an independent audit. The auditor runs in a separate
context for unbiased evaluation. No exceptions, regardless of the number of proofs.

**This is the authoritative, project-wide audit.** `purlin:build` also runs one, but that is
feature-scoped and advisory — fast feedback on the feature just built. This one measures the
whole project and is the number to report.

Spawn a `purlin:purlin-auditor` with prompt:
  "Audit all features that just received receipts: <feature list>.
   Load criteria via: python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit/static_checks.py --load-criteria --project-root <project_root>
   Audit cache is at .purlin/cache/audit_cache.json — use cached results where proof hashes match.
   For each proof, read the spec description and the test code.
   Assess as STRONG/WEAK/HOLLOW.
   Report any HOLLOW or WEAK findings — remediation happens via purlin:build, not by
   spawning a fixer agent. Loop until no HOLLOW proofs remain or 3 rounds per proof.
   Report the final integrity score."

If HOLLOW or WEAK proofs are found:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠ AUDIT FOUND QUALITY ISSUES

  PROOF-3 (login): HOLLOW ✗ — mocks bcrypt, proves nothing
  PROOF-2 (checkout): WEAK ~ — missing body assertion

Fix in the build loop, then re-verify:
  → Run: test login (fix PROOF-3: use real bcrypt)
  → Run: test checkout (fix PROOF-2: add body assertion)
  → Run: purlin:verify
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

The loop: verify → audit → if issues → build fixes → verify again. Verify does NOT fix tests. Build fixes. Audit judges.

### Step 5 — Commit

Commit per `references/commit_conventions.md` using the `verify:` prefix: `verify: [Complete:all] features=N/T vhash=<combined-hash>`. `N/T` is verified/total count. The combined hash covers all individual vhashes: `sha256(sorted vhashes joined by comma)[:8]`.

---

## --recheck Mode

Clean-room re-execution that compares results against committed receipts.

1. Run the full test suite via `purlin:test --all` (same as default mode).
2. Compute vhash for each feature.
3. Compare against existing `*.receipt.json` files.
4. For each feature with a matching receipt, verify it has behavioral proofs (structural-only features cannot have receipts).
5. Report features:

```
AUDIT RESULTS:

Behavioral features: 2/2 MATCH
  auth_login: MATCH (vhash=a1b2c3d4)
  user_profile: MATCH (vhash=e5f6a7b8)

Structural-only features: 2/2 MATCH (not counted toward integrity score)
  purlin_agent: MATCH (vhash=f1a2b3c4) — 8 proofs, all grep/existence
  skill_build: MATCH (vhash=d5e6f7a8) — 6 proofs, all grep/existence
  → Structural-only features need behavioral rules and E2E proofs for full audit credit

Missing/Mismatched:
  webhook_delivery: MISMATCH (receipt stale)
```

6. Report: MATCH (receipt valid), MISMATCH (receipt stale — rules or proofs changed), MISSING (no receipt on file).

For CI integration: exit code 0 if all receipts match (both behavioral and structural-only), exit code 1 if any mismatch or missing. The structural-only separation is informational — it does not change the exit code, but it makes the coverage quality visible in audit reports.

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
