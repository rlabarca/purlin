---
name: audit
description: Evaluate proof quality — Proof Design (provable?) and Proof Integrity (proven?)
---

Audit all proofs (or a specific feature) against configurable criteria. Read-only — never modifies code or test files.

## Usage

```
purlin:audit                        Audit — mode derived from project state
purlin:audit <feature>              Audit a specific feature
purlin:audit --design               Proof Design only (specs; no tests needed)
purlin:audit --integrity            Proof Integrity only (requires tests)
purlin:audit --criteria <path>      Use a specific criteria file
```

Two gauges, measured separately (`references/audit_criteria.md`):

| Gauge | Question | Reads | Needs tests? |
|-------|----------|-------|-------------|
| **Proof Design** | *Is the claim provable?* | the rule and its proof description | No |
| **Proof Integrity** | *Is the claim proven?* | the test code behind each proof | Yes |

`purlin:verify` answers the third question — *does it pass right now?* — and owns pass/fail.
Neither gauge is a gate.

## Step 0 — Select Mode

**Derive the mode from what exists. Do not guess, and do not ask.**

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit/static_checks.py \
  --audit-scope --project-root <project_root>
```

That reports, per feature, `rules`, `proofs_declared`, `proofs_executed`,
`scope_files_exist`, `test_files_present`, plus a `recommended_mode` and the `why` behind it.

| Observed state | Mode | Why |
|---|---|---|
| The user asked for one ("audit my spec", "are my proofs any good", "before we build") | as asked | Words beat inference |
| `--design` or `--integrity` passed | as passed | Explicit override |
| `proofs_executed == 0` everywhere | **design only** | No test code exists, so Integrity is unmeasurable. Pass 1 and Pass 0.5 would exit 2 on the missing files |
| `proofs_executed == proofs_declared` | **both** | Design is cheap and bounds what Integrity can reach |
| partial | **both** | Run Integrity only for the features that have executed proofs — never report it over proofs that never ran |

`scope_files_exist` separates two states that look identical in a coverage report: a spec whose
`> Scope:` files do not exist yet (nothing built — the next step is `purlin:build`) from one
whose files exist but have no proofs (the next step is `purlin:test`).

**Announce the choice and the state behind it**, so the user can see why:

```
Mode: Proof Design only — 12 features, 47 proof descriptions, 0 executed proofs.
      No test code to grade yet. Run purlin:build to reach Proof Integrity.
```

In design-only mode, run Step 1 (criteria) then Step D below, and skip Steps 1.6, 2, 3.5. Step
3.4 still applies: write the design cache. Never run Pass 0.5 or Pass 1 without proof files —
they exit 2, which is the crash this step exists to prevent.

## Step D — Proof Design Pass

Grades proof descriptions. Reads no test code, so it runs on a spec-only project.

**Pass D1 — deterministic.** Per spec:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit/static_checks.py \
  --check-proof-design --spec-path <spec_path>
```

Returns a level per proof — `PROVABLE`, `LOOSE`, `UNPROVABLE` or `STRUCTURAL` — with a `check`
name and a `reason`. `STRUCTURAL` is not a defect: the rule is structural, so a presence check
is the right proof, and it is excluded from the Design score exactly as `EXCLUDED` is excluded
from Integrity.

**Pass D2 — LLM, for the descriptions D1 graded `PROVABLE`.** D1 is deliberately conservative
and only catches unambiguous defects. Ask, per proof:

```
For each proof description, given its rule:
1. If a test implemented this description faithfully, would it demonstrate the rule?
2. Is any part of the rule left uncovered by every proof for it?
3. Does the tier tag match what verifying this would actually require?
4. For a constraint rule (reject/block/limit), does the description exercise the rejection?

Rate each: PROVABLE, LOOSE, or UNPROVABLE. Report CRITERION, WHY and FIX for anything
that is not PROVABLE. Do not use STRONG/WEAK/HOLLOW — those describe tests, not
descriptions.
```

Cache results with `--write-design-cache` (same nine-field entry shape as Step 3.4), then
report:

```
PROOF DESIGN: <feature> (<N> descriptions)
  UNPROVABLE  PROOF-1 (RULE-1): existence is the entire assertion
    Fix: name the input and the expected output
  LOOSE       PROOF-4 (RULE-4): no expected value
  PROVABLE    PROOF-2, PROOF-3
  STRUCTURAL  PROOF-5 (excluded from scoring)

PROOF DESIGN SCORE: 50%  (PROVABLE / (PROVABLE + LOOSE + UNPROVABLE))
```

Remediation for a Design finding is `purlin:spec <feature>` — the description is the artifact
that is wrong. Never narrow a description to match a weak test, and never reword an anchor
rule.

## Step 1 — Load Criteria

Load combined criteria via the single-source function:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit/static_checks.py --load-criteria --project-root <project_root>
```

**Interpreter:** every `static_checks.py` invocation below is written as `python3`, but `python3` is not always on PATH (notably on Windows, where the launcher is `python` or `py -3`). Probe for an available interpreter and use the first that resolves — `python3`, then `python`, then `py -3` — for all `static_checks.py` commands in this skill.

If `--criteria <path>` was passed by the user, add `--extra <path>` to append that file too.

This returns built-in criteria + any configured additional team criteria + any extra file. Built-in criteria always apply — additional criteria are appended, never replace.

Display: `Using audit criteria: built-in (Criteria-Version: N)` and if additional criteria are present: `+ team criteria from <source> (pinned: <sha>)`

## Step 1.5 — Load Audit Cache

Read `.purlin/cache/audit_cache.json` via:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit/static_checks.py --read-cache
```

The cache maps proof hashes to previous assessments. Every entry carries all nine fields:

```json
{
  "a1b2c3d4e5f6a7b8": {
    "assessment": "STRONG",
    "criterion": "matches rule intent",
    "why": "test exercises the rule correctly",
    "fix": "none",
    "feature": "login",
    "proof_id": "PROOF-1",
    "rule_id": "RULE-1",
    "priority": "LOW",
    "cached_at": "2026-04-03T00:00:00+00:00"
  }
}
```

`feature` and `proof_id` are not optional: they are the deduplication key used by both
`write_audit_cache()` and `_read_audit_summary()`. An entry missing either one deduplicates
under the empty key `('', '')`, so an entire batch written in that shape collapses to a single
surviving row and the integrity score is then computed from one proof — a confident, plausible,
wrong percentage. `--write-cache` rejects such entries rather than merging them.

`cached_at` is stamped by the writer, so a value supplied here is advisory.

For each proof that reaches Pass 2, compute the proof hash from (rule text + proof description + test function code). If the hash exists in the cache, use the cached assessment — skip the LLM call. Report cached results with a `(cached)` label:

```
PROOF-1 (RULE-1): STRONG ✓ (cached)
```

After the audit completes, write all new assessments to the cache (both cached hits and fresh LLM results) — this is **Step 3.4 below**, which names the command. The cache grows over time, so subsequent runs are faster.

## Step 1.6 — Plan Parallel Execution

After loading the cache, categorize features for parallel execution:

- **Cache-only:** specs where every proof has a cache hit. Run Pass 1 in the main context to re-check for new structural defects (a cached STRONG proof could have been edited to `assert True`). If all proofs still pass Pass 1 and have cache hits, use cached assessments — no LLM needed.
- **Needs LLM:** at least one proof has no cache hit or fails Pass 1 — requires fresh Pass 2 evaluation

For features in the "Needs LLM" category, launch up to 3 parallel evaluations using the Agent tool:

```
Agent(subagent_type="purlin:purlin-auditor", prompt="Audit feature <name>: ...")
Agent(subagent_type="purlin:purlin-auditor", prompt="Audit feature <name>: ...")
Agent(subagent_type="purlin:purlin-auditor", prompt="Audit feature <name>: ...")
```

Each subagent receives:
- The audit criteria
- The audit cache (so it can check for hits on its assigned feature)
- The feature's spec and test files to evaluate

When all subagents complete, merge their results into the final report, then write every assessment to the cache via **Step 3.4**. Subagents must not write the cache themselves — a single writer keeps the merge under one lock.

For "Cache-only" features, evaluate them in the main context (no subagent needed — they're fast).

## Step 2 — Audit Pipeline

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

Run the deterministic static checker on all specs with proofs:

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

### Structural Classification + Semantic Evaluation (Pass 2 — only for surviving proofs)

Proofs that passed Pass 1 go to the LLM for classification and semantic evaluation. The LLM first classifies each proof as structural or behavioral, then evaluates behavioral proofs.

**Batch all proofs for a feature into a single LLM evaluation.** Do NOT evaluate proofs one-at-a-time — this wastes LLM calls. Construct one prompt per feature containing ALL surviving proofs (those that passed Pass 1 and are not cache hits).

For each feature being audited:

1. Read the spec's `## Proof` section — get every proof description.
2. For each proof, find the test file and test function from `.proofs-*.json` entries.
   - **Empty `test_file` fallback:** some runners cannot supply a source path — the xUnit logger emits `MakeRelative(_root, tc.CodeFilePath ?? "")`, and under `dotnet test` `CodeFilePath` is often null (no source info), so C# proof entries arrive with `test_file: ""`. When `test_file` is empty, resolve it from the fully-qualified `test_name` before Pass 1 and Pass 2:

     ```bash
     python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit/static_checks.py --resolve-source "<test_name>" --project-root <project_root> [--ext .cs]
     ```

     This derives the declaring type from `test_name` (the segment before the final `.method`) and searches the project's source files for its declaration, printing JSON `{test_name, test_file}`. Use the resolved `test_file` for both the Pass 1 command and the Pass-2 code read. To populate `test_file` natively instead, the consumer's test project must surface source info — run `dotnet test` with `RunConfiguration.CollectSourceInformation=true` and full PDBs.
3. Read the actual test code (the function body, not just the marker).
4. **Read fixture/setup code** — if the test references a class-scoped or module-scoped fixture (e.g. via `self` parameter or `@pytest.fixture(scope="class")`), include the fixture code in the prompt. This is critical for e2e tests where the "act" step is in the fixture.
5. Drop any proof already rated HOLLOW by Pass 1 or resolved by cache hit.
6. For `@manual` proofs: check staleness only, assess as MANUAL — exclude from LLM batch.
7. Check if any remaining proof's rule comes from an anchor (the rule key contains a `/` prefix from a spec in `specs/_anchors/`). If so:
   - The fix directive must say "strengthen the test" not "update the rule"
   - If the rule itself is ambiguous or seems wrong, collect it for the anchor author recommendations section (see Step 3)
8. If zero proofs remain after steps 5–6: skip Pass 2 entirely for this feature.
9. If proofs remain: construct a single prompt containing ALL surviving proof descriptions, ALL test code, and ALL fixture/setup code. Send one LLM call per feature, not one per proof.

**For Claude (default auditor):**

```
You are classifying and evaluating proofs against spec rules.
Structural issues (assert True, no assertions, logic mirroring) have already been checked and passed.

STEP 1 — CLASSIFY each proof as STRUCTURAL or BEHAVIORAL:

Examine the proof description, test code, AND fixture/setup code together.

STRUCTURAL — the content being checked exists independently of the test.
The test reads pre-existing files or static content that no code in the
test's setup chain produced. Examples: checking a config template has
certain fields, grepping source code for forbidden patterns, verifying a
markdown doc has correct sections.

BEHAVIORAL — the test verifies output produced by running code. Includes:
  - Direct function calls whose return value is asserted
  - E2E tests where a fixture runs the system (subprocess, API call,
    function invocation) and assertions check the artifacts it created
  - Tests that check files/strings CREATED by the test's setup chain
  - Tests where the "act" step is in a class-scoped fixture

Key signal: if the fixture or setup runs code that produces the artifact
being checked, the test is BEHAVIORAL — even if the assertions use
string-matching or regex on file contents. The question is not "what do
the assertions look like?" but "did code run to produce what's being
asserted on?"

STRUCTURAL proofs → EXCLUDED (not scored)

STEP 2 — EVALUATE each BEHAVIORAL proof:

For each behavioral proof, answer ONLY these questions:
1. Does the test set up a scenario that exercises the rule's constraint?
2. Does the test check the specific outcome the proof description claims?
3. Is anything described in the proof missing from the test?
4. Does the assertion contain a tautological escape hatch (OR branch that always passes)?
5. Does the assertion validate test setup data instead of code-under-test output?
6. Does the test function name contradict the actual assertion values?

Rate each: STRONG (test matches rule intent), WEAK (test partially matches — something is missing or too loose), or EXCLUDED (structural presence check, not behavioral).
Do NOT check for structural issues — those were already handled.
```

**For external LLM (`audit_llm` configured):**

Same prompt, but wrapped in the structured response format:

```
For each proof, respond in EXACTLY this format:

PROOF-ID: PROOF-N
RULE-ID: RULE-N
ASSESSMENT: STRONG|WEAK|EXCLUDED
CRITERION: <what semantic aspect is missing, "matches rule intent" if STRONG, or "structural presence check" if EXCLUDED>
WHY: <what behavior would slip through, "test exercises the rule correctly" if STRONG, or "test verifies document content, not system behavior" if EXCLUDED>
FIX: <specific change to align test with rule, "none" if STRONG, or "none — exclude from audit" if EXCLUDED>
---
```

Note: the LLM can return STRONG, WEAK, or EXCLUDED in Pass 2. HOLLOW is exclusively determined by Pass 1 (deterministic). EXCLUDED proofs are structural — the pipeline excludes them from scoring.

## Step 3 — Report

Use the bordered output format with findings grouped by value tier (see `references/audit_criteria.md` § Finding Priority):

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROOF AUDIT: <feature> (<N> proofs)
Criteria: <source> (Criteria-Version: N)
Auditor: Pass 1 — static_checks.py | Pass 2 — Claude (or external LLM name)
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
AUDIT SUMMARY:
  CRITICAL: N   HIGH: N   MEDIUM: N   LOW: N   STRONG: N   MANUAL: N
  Audited: N proofs (M cached, K fresh) | J structural excluded
  Fix priority: N critical, then N high-value, then N medium
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Finding Priority

Group findings by value tier (see `references/audit_criteria.md` § Finding Priority for the complete tier mapping). Within each tier, list HOLLOW before WEAK. Present tiers in this order: CRITICAL, HIGH, MEDIUM, LOW, STRONG.

When handing findings to `purlin:build`, pass them in priority order: CRITICAL first, then HIGH, then MEDIUM. The build loop fixes in that order. If the 3-round limit is reached, the highest-value findings have been addressed.

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

  prodbrief_checkout (Source: git@github.com:acme/product-briefs.git)
    RULE-3: "Order confirmation email arrives within 60 seconds"
    → Suggest: specify what "arrives" means — delivered to SMTP server, or in user's inbox?
```

This section only appears when anchor rules have clarity issues. It's advisory — the anchor author decides whether to act.

## When Running as Independent Auditor

When spawned by purlin:verify or another agent:

- Load criteria via `--load-criteria` (see Step 1)
- For each proof, assess as STRONG/WEAK/HOLLOW using the three-pass pipeline
- After completing the audit, if HOLLOW or WEAK proofs are found:
  - Report the findings — the audit is read-only and never edits code or tests
  - Format each finding with the three-part structure (PROOF-ID, finding, fix)
  - Remediation happens in the build loop: `purlin:build <feature>`. There is no separate
    fixer agent to spawn — on hosts where agent types are fixed by the harness, one would
    not be resolvable, so the instruction would be unfollowable
  - After the fixes land, re-audit the affected proofs
  - If still WEAK or HOLLOW, provide more specific guidance
  - After 3 rounds on any single proof, move on
- When all findings are addressed (or rounds exhausted): report the final integrity score

### Anchor Rule Handling

When a HOLLOW or WEAK proof is for an anchor rule:
- State the fix directive: "Fix the test to properly prove <anchor>/<rule>. The anchor is read-only — strengthen the test, don't suggest changing the rule."
- If the rule itself is ambiguous: message the lead: "Recommend to anchor author (<source>): <rule> could be clearer — <suggestion>"

## External LLM Mode

When `.purlin/config.json` has `audit_llm` set, the audit still runs Pass 1 (deterministic) first. Proofs that pass Pass 1 go to the external LLM for Pass 2 (classification + semantic evaluation).

1. Load criteria via Step 1 above (`--load-criteria` — respects additional team criteria and `--extra`).
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
3. Lead reports each finding for the build loop:
   ```
   [Gemini Pro audit] HOLLOW: login PROOF-3
   Criterion: mocks the function being tested
   Why: test passes even if bcrypt is misconfigured
   Fix: remove mock, use real bcrypt call
   ```
4. `purlin:build` applies the fixes and reports results back
5. Lead shells out to external LLM again for re-audit
6. Loop until no HOLLOW proofs or 3 rounds per proof

The build loop never calls the external LLM. The lead relays.

## Step 3.4 — Write Audit Cache (MANDATORY)

**An audit that does not write the cache has produced no measurement.** Nothing else in this
skill persists an assessment, and every later step assumes this one ran.

Collect every assessment from this audit — cache hits and fresh results alike — into a JSON
object keyed by proof hash, then pipe it to `--write-cache`:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit/static_checks.py \
  --write-cache --project-root <project_root> < <entries.json>
```

Pass `--project-root` explicitly. Every cache mode defaults to the current working directory,
so a cwd that is not the project root silently reads or writes a different project's cache.

Each entry needs all nine fields (see `references/audit_criteria.md` § Required entry fields):

```json
{
  "a1b2c3d4e5f6a7b8": {
    "assessment": "STRONG",
    "criterion": "matches rule intent",
    "why": "test exercises the rule correctly",
    "fix": "none",
    "feature": "login",
    "proof_id": "PROOF-1",
    "rule_id": "RULE-1",
    "priority": "LOW",
    "cached_at": "2026-04-03T00:00:00+00:00"
  }
}
```

`feature` and `proof_id` are the deduplication key — omit either and the whole batch collapses
to one surviving entry, so the score gets computed from a single proof. `--write-cache` rejects
such entries with exit 2 rather than merging them.

Verify it landed before moving on:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit/static_checks.py --read-cache --project-root <project_root>
```

If the cache is absent, `_read_audit_summary()` in `purlin_server.py` returns `None`,
`sync_status` reports `No audit data`, and the dashboard renders `—` — indistinguishable from
never having audited at all.

## Step 3.5 — Prune Stale Cache Entries (full audit only)

After writing all assessments to the cache, if this is a full audit (no specific feature argument), prune orphaned entries from deleted or renamed features. Collect all proof hashes that were computed during this audit (cache hits + fresh evaluations) into a temp file, one key per line:

```bash
# Write live keys to temp file
echo "<hash1>" > /tmp/purlin_live_keys.txt
echo "<hash2>" >> /tmp/purlin_live_keys.txt
# ... one line per proof hash computed during this audit

python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit/static_checks.py --prune-cache --live-keys-file /tmp/purlin_live_keys.txt
```

This removes cache entries for features that no longer exist while preserving all entries from the current audit. For single-feature audits, skip this step — they don't know which other features are live.

**Never run this with an empty live-keys file.** Pruning against zero live keys is a full sweep
that deletes every entry, including the ones Step 3.4 just wrote. If no proof hashes were
computed during this audit, skip the prune entirely.

## Step 4 — Refresh Status and Report Both Gauges

After the audit report is complete and the cache has been written, call `sync_status` to compute the integrity score and refresh the dashboard:

```
sync_status()
```

The `sync_status` output includes both gauge percentages (computed by `_compute_integrity()` and `_compute_design()` in `purlin_server.py`), each with its measurement coverage and its own age. **Do not compute either percentage yourself** — always read them from the `sync_status` output. This ensures the audit CLI and the dashboard always show the same values from the same computation.

After `sync_status` completes, report both scores it returned, Design first:

```
PROOF DESIGN SCORE: <N>% (from sync_status, coverage-weighted)
  Formula: PROVABLE / (PROVABLE + LOOSE + UNPROVABLE) — STRUCTURAL excluded.
  Assessed score <A>%, measured over <M> of <T> declared proof descriptions.

INTEGRITY SCORE: <N>% (from sync_status, coverage-weighted)
  Formula: (STRONG + MANUAL) / (STRONG + WEAK + HOLLOW + MANUAL) — proof quality only.
  Assessed score <A>%, measured over <M> of <T> executed proofs.
```

Report both numbers. `<N>` is what sync_status prints: the assessed score weighted by
measurement coverage, so it cannot claim more than was looked at. `<A>` is the assessed score
the formula above produces over the cache's own entries. They are equal at full coverage. Below
it, reporting `<A>` alone is the difference between a measurement and a claim — 100% Integrity
from 11 graded proofs while every feature row reads `not audited`. See
`references/audit_criteria.md` § Assessed score vs reported score.

## Which Lever Moves Which Assessment

Full criteria: `references/audit_criteria.md` § Pass D and § Scoring. The short version, because
agents guess this wrong and the guess is expensive:

| Level | Decided by | What moves it |
|-------|-----------|---------------|
| HOLLOW | Pass 1 reading test code | Editing the test, via `purlin:build`. Nothing else. |
| EXCLUDED | The test's shape — did setup run code that produced the asserted artifact? | New test code. Rewording a rule does not make a source-grep test behavioural. |
| WEAK | Pass 2 comparing test to description | A better test. Narrowing the description "fixes" it only by lowering the claim — never do this, and never on an anchor rule. |
| PROVABLE / LOOSE / UNPROVABLE | Pass D reading the description | Editing the proof description. This is the gauge prose is *supposed* to move. |

Two consequences worth stating outright:

- **Marking something EXCLUDED or STRUCTURAL shrinks the denominator rather than improving
  anything.** Never reclassify to raise a score.
- **A high Proof Integrity score over LOOSE descriptions means nothing.** Most WEAK criteria are
  comparisons against the description, so a vague description leaves them unable to fire. Fix
  Design first or the Integrity number is measuring an unfalsifiable spec.

**Both figures move differently.** Rewriting a test moves the assessed score. Grading more
proofs moves the reported one, even with no test touched, because it shrinks the unmeasured part
of the denominator. A project stuck at a low reported score with a high assessed score needs a
wider audit, not better tests.

**Reaching a target Integrity score.** With `N` behavioural proofs and `H` HOLLOW: the ceiling is
`(N − H) / N`, a target `T` is reachable iff `H ≤ (1 − T) × N`, and the number of tests that must
be rewritten is `max(0, H − floor((1 − T) × N))`. For 287 proofs with 57 HOLLOW the ceiling is
80%, and a 90% target needs 29 tests rewritten. Answer this arithmetic before starting work, not
after a full audit.

## Key Principles

- **Read-only.** Never modify code or test files.
- **Independent.** When spawned as a subagent, has fresh context — no memory of writing the tests.
- **Criteria-driven.** All judgments reference the criteria document, not ad hoc opinions.
- **Transparent.** The report shows the criteria version and source so anyone can verify the assessment was made against known standards.
- **Actionable recommendations.** Every HOLLOW or WEAK finding includes three parts:
  - **Criterion** — which specific criterion was violated (name it from audit_criteria.md)
  - **Why** — what real problem this creates (what bug or failure would slip through)
  - **Fix** — a specific, concrete change the build loop should make (not "improve the test" but "replace `expected = hash_func(input)` with `expected = '5e884898da28...'`")

  Bad fix recommendation: "Make the test stronger"
  Good fix recommendation: "Remove the bcrypt.checkpw mock. Store a password via `create_user('alice', 'secret')`, retrieve the stored hash, assert `bcrypt.checkpw(b'secret', stored_hash)` returns True"
