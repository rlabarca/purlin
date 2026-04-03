---
name: audit
description: Evaluate proof quality — STRONG/WEAK/HOLLOW assessments
---

Audit all proofs (or a specific feature) against configurable criteria. Read-only — never modifies code or test files.

## Usage

```
purlin:audit                        Audit all features with receipts
purlin:audit <feature>              Audit a specific feature
purlin:audit --criteria <path>      Use a specific criteria file
```

## Step 1 — Load Criteria

1. Check `.purlin/config.json` for `audit_criteria` field.
2. If set: fetch the external criteria file (clone repo, read file at pinned SHA). If pinned SHA doesn't match remote, warn: `"Audit criteria may be stale — run purlin:init --sync-audit-criteria"`
3. If not set: read `references/audit_criteria.md` (the default).
4. If `--criteria <path>` was passed, use that file instead (overrides both config and default).
5. Display: `Using audit criteria: <source> (Criteria-Version: N)`

## Step 2 — Evaluate Each Proof

For each feature being audited:

1. Read the spec's `## Proof` section — get every proof description.
2. For each proof, find the test file and test function from `.proofs-*.json` entries.
3. Read the actual test code (the function body, not just the marker).
4. Check if the rule being proved comes from an invariant (the rule key contains a `/` prefix from a spec in `specs/_invariants/`). If it does:
   - The fix directive must say "strengthen the test" not "update the rule"
   - If the rule itself is ambiguous or seems wrong, collect it for the invariant author recommendations section (see Step 3)
5. Apply the HOLLOW, WEAK, STRONG criteria from the loaded criteria document.
6. For `@manual` proofs: check staleness only, assess as MANUAL.

## Step 3 — Report

Use the bordered output format:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROOF AUDIT: <feature> (<N> proofs)
Criteria: <source> (Criteria-Version: N)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  PROOF-1 (RULE-1): <proof description>
    Test: <test_name> in <test_file>:<line>
    Assessment: STRONG ✓
    Reason: <why it's strong>

  PROOF-2 (RULE-2): <proof description>
    Test: <test_name> in <test_file>:<line>
    Assessment: HOLLOW ✗
    Criterion: <which criterion from audit_criteria.md was violated>
    Why: <what would slip through — why this matters>
    Fix: <specific, actionable change the builder should make>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INTEGRITY SCORE: <N>%
  STRONG: N   WEAK: N   HOLLOW: N   MANUAL: N
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If HOLLOW or WEAK proofs found, append directives:

```
Fix proof quality in the build loop, then re-verify:
  → Run: test <feature> (fix PROOF-N: <what to fix>)
  → Run: purlin:verify
```

If any invariant rules have clarity issues, append a separate section:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RECOMMENDATIONS FOR INVARIANT AUTHORS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  i_security_no_eval (Source: git@github.com:acme/security-policies.git)
    RULE-1: "No eval() calls in source code"
    → Suggest: clarify scope — does this include test files? Current wording is ambiguous.

  i_prodbrief_checkout (Source: git@bitbucket.org:acme/product-briefs.git)
    RULE-3: "Order confirmation email arrives within 60 seconds"
    → Suggest: specify what "arrives" means — delivered to SMTP server, or in user's inbox?
```

This section only appears when invariant rules have clarity issues. It's advisory — the invariant author decides whether to act.

## Teammate Mode

When running as a purlin-auditor teammate in an agent team:

- Read references/audit_criteria.md at startup
- After completing the initial audit, message findings directly to the purlin-builder teammate (not the lead)
- Format each finding with the three-part structure:
  ```
  HOLLOW: login PROOF-3 (RULE-3)
  Criterion: mocks the exact function the rule is about
  Why: test passes even if bcrypt is misconfigured — a real auth bypass would not be caught
  Fix: remove bcrypt.checkpw mock. Store a password via create_user('alice', 'secret'),
       retrieve the hash, assert bcrypt.checkpw(b'secret', stored_hash) returns True.
  ```
- Wait for the builder's response confirming the fix
- Re-read the fixed test code and re-assess
- If the fix resolves the issue: mark as STRONG, move to the next finding
- If the fix is still WEAK or HOLLOW: message the builder again with more specific guidance
- When all findings are addressed (or after 3 rounds on any single proof): send the final integrity score to the lead

### Invariant Rule Handling (teammate mode)

When a HOLLOW or WEAK proof is for an invariant rule:
- Message the builder: "Fix the test to properly prove <invariant>/<rule>. The invariant is read-only — strengthen the test, don't suggest changing the rule."
- If the rule itself is ambiguous: message the lead (not the builder): "Recommend to invariant author (<source>): <rule> could be clearer — <suggestion>"

## External LLM Mode

When `.purlin/config.json` has `audit_llm` set, the audit runs Step 1 (Load Criteria) first, then uses the loaded criteria in the prompt sent to the external LLM instead of evaluating proofs inline.

1. Load criteria via Step 1 above (respects `--criteria`, external criteria config, and defaults).
2. For each feature being audited, construct the prompt:

```
You are a code test auditor. Evaluate whether each test actually proves what the proof description claims.

CRITERIA:
<paste full contents of references/audit_criteria.md>

SPEC PROOF DESCRIPTIONS:
<paste the ## Proof section from the spec>

TEST CODE:
<paste the actual test function code for each proof>

For each proof, respond in EXACTLY this format (one block per proof, no other text):

PROOF-ID: PROOF-N
RULE-ID: RULE-N
ASSESSMENT: STRONG|WEAK|HOLLOW
CRITERION: <which criterion was violated, or "matches proof description" if STRONG>
WHY: <what real problem this creates, or "test meaningfully proves the rule" if STRONG>
FIX: <specific change to make, or "none" if STRONG>
---
```

3. Shell out: replace `{prompt}` in the configured command with the constructed prompt. Capture stdout.
4. Parse the response: look for `PROOF-ID:`, `ASSESSMENT:`, `CRITERION:`, `WHY:`, `FIX:` lines. Be flexible — different LLMs format slightly differently. Look for the keywords, not exact whitespace.
5. If parsing fails for a proof (LLM didn't follow the format): mark that proof as `UNKNOWN — external LLM response could not be parsed` and include the raw response excerpt.
6. Display the same report format as the default mode:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROOF AUDIT: <feature> (<N> proofs)
Criteria: references/audit_criteria.md (Criteria-Version: N)
Auditor: Gemini Pro (external — cross-model)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

The report header shows which LLM did the audit.

### External LLM with Agent Teams

When agent teams are active AND external LLM is configured, the lead relays findings:

1. Lead shells out to the external LLM per feature
2. Lead parses the response
3. Lead messages the builder teammate with each finding:
   ```
   [Gemini Pro audit] HOLLOW: login PROOF-3
   Criterion: mocks the function being tested
   Why: test passes even if bcrypt is misconfigured
   Fix: remove mock, use real bcrypt call
   ```
4. Builder fixes and messages lead back
5. Lead shells out to external LLM again for re-audit
6. Loop until no HOLLOW proofs or 3 rounds per proof

The builder teammate never talks to the external LLM. The lead relays.

## Key Principles

- **Read-only.** Never modify code or test files.
- **Independent.** When spawned as a subagent, has fresh context — no memory of writing the tests.
- **Criteria-driven.** All judgments reference the criteria document, not ad hoc opinions.
- **Transparent.** The report shows the criteria version and source so anyone can verify the assessment was made against known standards.
- **Actionable recommendations.** Every HOLLOW or WEAK finding includes three parts:
  - **Criterion** — which specific criterion was violated (name it from audit_criteria.md)
  - **Why** — what real problem this creates (what bug or failure would slip through)
  - **Fix** — a specific, concrete change the builder should make (not "improve the test" but "replace `expected = hash_func(input)` with `expected = '5e884898da28...'`")

  Bad fix recommendation: "Make the test stronger"
  Good fix recommendation: "Remove the bcrypt.checkpw mock. Store a password via `create_user('alice', 'secret')`, retrieve the stored hash, assert `bcrypt.checkpw(b'secret', stored_hash)` returns True"
