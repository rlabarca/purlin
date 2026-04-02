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
    Reason: <specific hollow reason from criteria>
    → Fix: <what to change>

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

## Key Principles

- **Read-only.** Never modify code or test files.
- **Independent.** When spawned as a subagent, has fresh context — no memory of writing the tests.
- **Criteria-driven.** All judgments reference the criteria document, not ad hoc opinions.
- **Transparent.** The report shows the criteria version and source so anyone can verify the assessment was made against known standards.
