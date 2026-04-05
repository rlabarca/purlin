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

## Step 1.5 — Load Audit Cache

Read `.purlin/cache/audit_cache.json` via:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit/static_checks.py --read-cache
```

The cache maps proof hashes to previous assessments:

```json
{
  "a1b2c3d4e5f6a7b8": {
    "assessment": "STRONG",
    "criterion": "matches rule intent",
    "why": "test exercises the rule correctly",
    "fix": "none",
    "cached_at": "2026-04-03T..."
  }
}
```

For each proof that reaches Pass 2, compute the proof hash from (rule text + proof description + test function code). If the hash exists in the cache, use the cached assessment — skip the LLM call. Report cached results with a `(cached)` label:

```
PROOF-1 (RULE-1): STRONG ✓ (cached)
```

After the audit completes, write all new assessments to the cache (both cached hits and fresh LLM results). This means the cache grows over time and subsequent runs are faster.

## Step 1.6 — Plan Parallel Execution

After loading the cache, run Pass 0 (`--check-spec-coverage`) for every feature to categorize them:

- **Skip entirely:** structural-only specs — report structural checks as excluded, no subagent needed
- **Cache-only:** non-structural specs where every proof hash exists in the cache. Run Pass 1 in the main context to re-check for new structural defects (a cached STRONG proof could have been edited to `assert True`). If all proofs still pass Pass 1 and have cache hits, use cached assessments — no LLM needed.
- **Needs LLM:** at least one proof has no cache hit or fails Pass 1 — requires fresh Pass 2 evaluation

For features in the "Needs LLM" category, launch up to 3 parallel evaluations using the Agent tool:

```
Agent(subagent_type="purlin-auditor", prompt="Audit feature <name>: ...")
Agent(subagent_type="purlin-auditor", prompt="Audit feature <name>: ...")
Agent(subagent_type="purlin-auditor", prompt="Audit feature <name>: ...")
```

Each subagent receives:
- The audit criteria
- The audit cache (so it can check for hits on its assigned feature)
- The feature's spec and test files to evaluate

When all subagents complete, merge their results into the final report and update the cache with all new assessments.

For features in "Skip entirely" and "Cache-only" categories, evaluate them in the main context (no subagent needed — they're fast).

## Step 2 — Audit Pipeline

### Pre-filter: Structural Check Exclusion (Pass 0 — always runs first)

Before evaluating individual proofs, classify each proof as structural or behavioral using the proof description.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit/static_checks.py --check-spec-coverage --spec-path <spec_path>
```

**Structural proofs** (grep, file exists, section present — matches structural pattern, no behavioral indicators):
- Skip entirely — do not send to Pass 1 or Pass 2
- Do not include in the audit total
- Report once per feature: "N structural checks excluded from audit"

**Behavioral proofs** proceed to Pass 1 and Pass 2 as normal.

If a feature has ONLY structural proofs:
- Report: "All proofs are structural checks — excluded from audit. Add behavioral proofs for audit coverage."
- Do not include the feature in the integrity score

If a feature has a mix:
- Structural proofs excluded, behavioral proofs audited normally

Report:

```
N structural checks excluded from audit
→ Add behavioral rules that test what the system does, not what files contain
```

Specs with at least one behavioral rule proceed to Pass 1 normally.

### Proof-File Structural Checks (Pass 0.5 — language-agnostic, no source reading)

Before reading any source code, run structural checks on the proof JSON files. These operate on JSON regardless of what language produced the proofs:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit/static_checks.py --check-proof-file --proof-path <proof_json> --spec-path <spec_path>
```

Checks:
- **Proof ID collision** — same PROOF-N targeting different RULE-N values. Severity: MEDIUM.
- **Proof rule orphan** — proof targets a RULE-N not in the spec. Severity: LOW.

Report findings inline with the feature's audit output. Proof ID collisions indicate confused proof tracking; orphans indicate stale markers.

### Static Analysis: Structural Defect Detection (Pass 1 — deterministic, no LLM)

For specs that passed Pass 0 (have behavioral rules), run the deterministic static checker:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit/static_checks.py <test_file> <feature_name> --spec-path <spec_path>
```

Any proof that fails a structural check is immediately rated HOLLOW — no LLM override possible:

```
PROOF-3 (RULE-3): HOLLOW ✗ (deterministic)
  Check: logic_mirroring
  Why: expected value computed by hash_func() — same function being tested. If hash_func has a bug, test confirms the bug.
  Fix: replace expected = hash_func(input) with a precomputed literal: assert result == "5e884898..."
```

The `(deterministic)` label tells the user this was caught by static analysis, not LLM judgment.

### Semantic Evaluation: LLM Alignment Check (Pass 2 — only for surviving proofs)

Proofs that passed structural checks go to the LLM for semantic evaluation. The LLM prompt is STRIPPED of all structural heuristics. It ONLY evaluates semantic alignment.

**Batch all proofs for a feature into a single LLM evaluation.** Do NOT evaluate proofs one-at-a-time — this wastes LLM calls. Construct one prompt per feature containing ALL surviving proofs (those that passed Pass 0 and Pass 1 and are not cache hits).

For each feature being audited:

1. Read the spec's `## Proof` section — get every proof description.
2. For each proof, find the test file and test function from `.proofs-*.json` entries.
3. Read the actual test code (the function body, not just the marker).
4. Drop any proof already rated HOLLOW by Pass 1 or resolved by cache hit.
5. For `@manual` proofs: check staleness only, assess as MANUAL — exclude from LLM batch.
6. Check if any remaining proof's rule comes from an anchor (the rule key contains a `/` prefix from a spec in `specs/_anchors/`). If so:
   - The fix directive must say "strengthen the test" not "update the rule"
   - If the rule itself is ambiguous or seems wrong, collect it for the anchor author recommendations section (see Step 3)
7. If zero proofs remain after steps 4–5: skip Pass 2 entirely for this feature.
8. If proofs remain: construct a single prompt containing ALL surviving proof descriptions and ALL test code. Send one LLM call per feature, not one per proof.

**For Claude (default auditor):**

```
You are evaluating semantic alignment between spec rules and test code.
Structural issues (assert True, no assertions, logic mirroring) have already been checked and passed.

For each proof, answer ONLY these questions:
1. Does the test set up a scenario that exercises the rule's constraint?
2. Does the test check the specific outcome the proof description claims?
3. Is anything described in the proof missing from the test?
4. Does the assertion contain a tautological escape hatch (OR branch that always passes)?
5. Does the assertion validate test setup data instead of code-under-test output?
6. Does the test function name contradict the actual assertion values?

Rate each: STRONG (test matches rule intent) or WEAK (test partially matches — something is missing or too loose).
Do NOT check for structural issues — those were already handled.
```

**For external LLM (`audit_llm` configured):**

Same prompt, but wrapped in the structured response format:

```
For each proof, respond in EXACTLY this format:

PROOF-ID: PROOF-N
RULE-ID: RULE-N
ASSESSMENT: STRONG|WEAK
CRITERION: <what semantic aspect is missing, or "matches rule intent" if STRONG>
WHY: <what behavior would slip through, or "test exercises the rule correctly" if STRONG>
FIX: <specific change to align test with rule, or "none" if STRONG>
---
```

Note: the LLM can ONLY return STRONG or WEAK in Pass 2. HOLLOW is exclusively determined by Pass 1 (deterministic). This prevents the LLM from disagreeing with the static checker.

## Step 3 — Report

Use the bordered output format with findings grouped by value tier (see `references/audit_criteria.md` § Finding Priority):

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROOF AUDIT: <feature> (<N> proofs)
Criteria: <source> (Criteria-Version: N)
Auditor: Pass 0 — spec coverage | Pass 1 — static_checks.py | Pass 2 — Claude (or external LLM name)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CRITICAL (fix first — tests prove nothing):
  PROOF-4 (RULE-4): HOLLOW ✗ — no assertions
    Why: test function has zero assert/expect statements
    Fix: add assertions checking the response status and body

HIGH VALUE (real coverage gaps):
  PROOF-2 (RULE-2): WEAK ~ — missing negative test
    Why: rule says "reject invalid passwords" but test only checks valid login
    Fix: add test with invalid password, assert 401 response

MEDIUM VALUE (self-confirming tests):
  PROOF-6 (RULE-6): HOLLOW ✗ — logic mirroring
    Why: expected = compute_hash(input) — same function as code under test
    Fix: replace with precomputed literal: assert result == "5e884898..."

STRONG (no action needed):
  PROOF-1 (RULE-1): STRONG ✓
  PROOF-3 (RULE-3): STRONG ✓

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INTEGRITY SCORE: <N>%
  CRITICAL: N   HIGH: N   MEDIUM: N   LOW: N   STRONG: N   MANUAL: N
  Audited: N proofs (M cached, K fresh) | J structural excluded
  Fix priority: N critical, then N high-value, then N medium
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Finding Priority

Group findings by value tier. Within each tier, list HOLLOW before WEAK. Present tiers in this order: CRITICAL, HIGH, MEDIUM, LOW, STRONG.

**Value tier mapping** (authoritative source: `references/audit_criteria.md` § Finding Priority):

CRITICAL — test proves nothing:
  - HOLLOW: no_assertions, bare_except
  - HOLLOW: assert_true when the assertion is literally `assert True`, `assertTrue(True)`, or `expect(true).toBe(true)`

HIGH — real coverage gap:
  - WEAK: missing assertions (proof says X AND Y, test only checks X)
  - WEAK: only happy path (rule implies error handling, test has none)
  - WEAK: missing negative test (constraint rule, no rejection test)
  - WEAK: deep mocking on critical path

MEDIUM — self-confirming test:
  - HOLLOW: logic_mirroring
  - HOLLOW: mock_target_match

LOW — weak assertion form:
  - HOLLOW: assert_true when heuristic (assert x is True, assert len >= 0)
  - WEAK: assertion_farming, catch_all_assertions, string_containment

When spawning the builder to fix findings, pass them in priority order: CRITICAL first, then HIGH, then MEDIUM. The builder fixes in that order. If the 3-round limit is reached, the highest-value findings have been addressed.

For features with structural checks excluded, the report looks like:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROOF AUDIT: purlin_agent (0 behavioral proofs)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  8 structural checks excluded from audit

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
→ All proofs are structural checks. Add behavioral rules and E2E proofs.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If HOLLOW or WEAK proofs found, append directives:

```
Fix proof quality in the build loop, then re-verify:
  → Run: test <feature> (fix PROOF-N: <what to fix>)
  → Run: purlin:verify
```

If any anchor rules have clarity issues, append a separate section:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RECOMMENDATIONS FOR ANCHOR AUTHORS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  security_no_eval (Source: git@github.com:acme/security-policies.git)
    RULE-1: "No eval() calls in source code"
    → Suggest: clarify scope — does this include test files? Current wording is ambiguous.

  prodbrief_checkout (Source: git@bitbucket.org:acme/product-briefs.git)
    RULE-3: "Order confirmation email arrives within 60 seconds"
    → Suggest: specify what "arrives" means — delivered to SMTP server, or in user's inbox?
```

This section only appears when anchor rules have clarity issues. It's advisory — the anchor author decides whether to act.

## When Running as Independent Auditor

When spawned by purlin:verify or another agent:

- Read references/audit_criteria.md at startup
- For each proof, assess as STRONG/WEAK/HOLLOW using the three-pass pipeline
- After completing the audit, if HOLLOW or WEAK proofs are found:
  - Spawn a purlin-builder to fix the identified issues
  - Format each finding with the three-part structure (PROOF-ID, finding, fix)
  - After the builder responds, re-audit the fixed proofs
  - If still WEAK or HOLLOW, provide more specific guidance
  - After 3 rounds on any single proof, move on
- When all findings are addressed (or rounds exhausted): report the final integrity score

### Anchor Rule Handling

When a HOLLOW or WEAK proof is for an anchor rule:
- Message the builder: "Fix the test to properly prove <anchor>/<rule>. The anchor is read-only — strengthen the test, don't suggest changing the rule."
- If the rule itself is ambiguous: message the lead (not the builder): "Recommend to anchor author (<source>): <rule> could be clearer — <suggestion>"

## External LLM Mode

When `.purlin/config.json` has `audit_llm` set, the audit still runs Pass 1 (deterministic) first. Only proofs that pass structural checks go to the external LLM for Pass 2.

1. Load criteria via Step 1 above (respects `--criteria`, external criteria config, and defaults).
2. Run Pass 1 (deterministic) for all proofs. Any failures are HOLLOW — final.
3. For proofs that passed Pass 1 and are not cache hits, **batch all proofs per feature** into a single shell-out. Construct the Pass 2 prompt:

```
You are evaluating semantic alignment between spec rules and test code.
Structural issues (assert True, no assertions, logic mirroring) have already been checked and passed.

SPEC PROOF DESCRIPTIONS:
<paste the ## Proof section from the spec — only proofs that passed Pass 1>

TEST CODE:
<paste the actual test function code for each proof>

For each proof, respond in EXACTLY this format:

PROOF-ID: PROOF-N
RULE-ID: RULE-N
ASSESSMENT: STRONG|WEAK
CRITERION: <what semantic aspect is missing, or "matches rule intent" if STRONG>
WHY: <what behavior would slip through, or "test exercises the rule correctly" if STRONG>
FIX: <specific change to align test with rule, or "none" if STRONG>
---
```

4. Shell out: replace `{prompt}` in the configured command with the constructed prompt. Capture stdout.
5. Parse the response: look for `PROOF-ID:`, `ASSESSMENT:`, `CRITERION:`, `WHY:`, `FIX:` lines. Be flexible — different LLMs format slightly differently. Look for the keywords, not exact whitespace.
6. If the external LLM returns HOLLOW for a proof, override to WEAK — only Pass 1 can produce HOLLOW.
7. If parsing fails for a proof (LLM didn't follow the format): mark that proof as `UNKNOWN — external LLM response could not be parsed` and include the raw response excerpt.
8. Display the combined report:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROOF AUDIT: <feature> (<N> proofs)
Criteria: references/audit_criteria.md (Criteria-Version: N)
Auditor: Pass 1 — static_checks.py | Pass 2 — Gemini Pro (external — cross-model)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

The report header shows both audit passes.

### External LLM with Independent Audit

When external LLM is configured, the lead relays findings:

1. Lead shells out to the external LLM per feature
2. Lead parses the response
3. Lead spawns a builder with each finding:
   ```
   [Gemini Pro audit] HOLLOW: login PROOF-3
   Criterion: mocks the function being tested
   Why: test passes even if bcrypt is misconfigured
   Fix: remove mock, use real bcrypt call
   ```
4. Builder fixes and reports results back
5. Lead shells out to external LLM again for re-audit
6. Loop until no HOLLOW proofs or 3 rounds per proof

The builder never calls the external LLM. The lead relays.

## Step 4 — Refresh Status

After the audit report is complete and the cache has been written, call `sync_status` to refresh the dashboard data:

```
sync_status()
```

This updates `.purlin/report-data.js` so the HTML dashboard reflects the new integrity score immediately. Without this step, the dashboard stays stale until the next `purlin:status` call.

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
