---
name: build
description: Inject spec rules into context, then implement
---

Read a spec, load all its rules (including from `> Requires:` dependencies), and implement the feature.

## Usage

```
purlin:build <name>             Build a feature from its spec
purlin:build                    Resume building the current feature
```

## Step 1 — Load the Spec

1. Find the spec: `specs/**/<name>.md`.
2. Read the spec. Extract all `RULE-N` entries from `## Rules` and all `PROOF-N` entries from `## Proof`.
3. Read all `> Requires:` specs (including anchors in `specs/_anchors/`). Extract their `RULE-N` and `PROOF-N` entries too — both rules and proof descriptions are needed for implementation.
4. **Read External References:** For each required anchor (and global anchors) with `> Source:`, read the external reference:
   - **Figma URL:** Call `get_design_context` and `get_screenshot` via Figma MCP for full visual fidelity.
   - **Git URL:** Fetch the file content from the repository.
   - **HTTP URL:** Fetch the page content.
   Use the external reference content as context when implementing — it provides the full fidelity behind the anchor's rules. If a fetch fails: report the error and ask the user whether to continue without the external reference or fix and retry.
5. If the feature spec itself or any required spec has a `> Visual-Reference:` field, load the visual reference at **full fidelity**:
   - `figma://fileKey/nodeId` → call `get_design_context` and `get_screenshot` MCP tools
   - `./path/to/image.png` → read the image file
   - `./path/to/file.html` → read the HTML file
   - `https://url` → take a screenshot via Playwright MCP if available
   - Display: `Visual reference loaded from: <source>`

Display the combined rule set with proof descriptions:

```
Building: <name>
Own rules: RULE-1, RULE-2, RULE-3
Required from api_rest_conventions:
  RULE-1: All endpoints return JSON with {data, error, meta} envelope
  PROOF-1: GET /endpoint returns {data: ..., error: null, meta: {}}
Required from design_modal:
  RULE-1: Implementation must visually match the Figma design
  PROOF-1: Screenshot comparison against Figma reference @e2e
  Visual reference loaded from: figma://ABC123/1:234
Scope: src/auth.js, src/auth.test.js
```

## Step 2 — Implement

Write code that satisfies all rules. Use `> Scope:` paths as guidance for where to write.

- Implement the feature naturally — there is no required order or ceremony.
- Keep the rules visible. If a rule constrains behavior, make sure the code satisfies it.
- If implementation reveals that a rule is wrong or missing, update the spec (this is expected).
- **When building a feature that requires a design anchor with `> Visual-Reference:`:**
  - Read the visual reference at FULL FIDELITY (Figma MCP, image file, etc.)
  - Build from the visual reference, not from rules — the anchor's rule just says "match the design," so the visual reference IS the spec
  - The visual reference captures everything: layout relationships, alignment, visual hierarchy, spacing proportions, colors, typography
  - Feature spec rules describe behavioral requirements — build those from the rules
  - When the visual reference and a behavioral rule conflict, the visual reference wins for visual implementation — but the behavioral rule must still be satisfied for verification

## Step 3 — Write Tests with Proof Markers

Write tests that prove each rule. Use proof markers so the test runner emits proof files. For marker syntax (pytest, Jest, Shell), see `references/formats/proofs_format.md`.

Each RULE must have at least one PROOF — both own rules AND required rules. For required rules, use the **required spec's feature name** in the proof marker, not your own feature name:

```python
# Own rule — uses YOUR feature name
@pytest.mark.proof("login", "PROOF-1", "RULE-1")

# Required rule from api_rest_conventions — uses THE ANCHOR's name
@pytest.mark.proof("api_rest_conventions", "PROOF-1", "RULE-1")
```

**Tier review (mandatory before running tests):**
Review every proof marker just written. Apply tier heuristics from `references/spec_quality_guide.md`:
- Test hits API/database/filesystem/subprocess → `@integration`
- Test needs browser/UI rendering → `@e2e`
- Test needs human judgment → `@manual`
- Pure logic/in-memory → unit (no tag)

If ANY proof marker is missing a tier tag and the test clearly isn't unit tier (it calls subprocess, hits a network endpoint, etc.), add the tag before running.

After writing tests, ALWAYS spawn a purlin-auditor teammate to review proofs. Do NOT audit your own tests in the same context — the auditor must be independent. This applies regardless of the number of proofs.

## Step 4 — Run Tests and Iterate

The iteration loop is: **write code → write tests → run `purlin:unit-test` → read coverage output → fix → repeat**. The loop does NOT end until coverage output shows PASSING for the target feature (all behavioral rules proved). PARTIAL means more tests are still needed.

```
purlin:unit-test <name>   # runs tests, emits proofs, calls sync_status, reports coverage
```

`purlin:unit-test` handles test framework detection, proof file emission, freshness checks, and `sync_status`. Calling `sync_status` after tests is not optional — `purlin:unit-test` does this automatically. Do NOT call `sync_status` separately — it would be redundant. Read the coverage output from `purlin:unit-test` and follow any `→` directives for uncovered rules.

**When a test fails, diagnose the root cause before fixing:**
1. Read the failing assertion — what did the test expect vs what did it get?
2. Read the spec rule the proof is linked to — is the test asserting the right behavior?
3. If the test is correct and the code is wrong → fix the code
4. If the test has a bug (wrong mock, wrong expected value) → fix the test
5. If the rule itself is wrong → update the spec first, then fix code and test

**Never weaken an assertion to make it pass.** If `assert response.status == 401` fails because the code returns 200, the code is wrong. See `references/spec_quality_guide.md` "When Tests Fail" for the full diagnostic guide.

**Assertion change detection (mandatory after fixing a failing test):**
After fixing a failing test, before running tests again, re-read the original proof description from the spec's `## Proof` section. Verify the assertion still matches. If the fix changed WHAT the test asserts (different status code, different field, looser check), flag it:

```
WARNING: Assertion for PROOF-2 (RULE-2) was changed during iteration.
Original proof description: "POST invalid password; verify 401"
New assertion: assert status == 400
Reason: API returns 400 for validation errors, not 401. Spec rule may need updating.
→ Run: purlin:spec <name> to review RULE-2
```

If you changed what a test asserts (not just how), the proof description in the spec may be wrong. The commit message MUST explain why the assertion changed.

## Step 5 — Changeset Summary (mandatory)

After the build/test loop reaches a stable state (all behavioral rules pass), output the changeset summary as a visible block in your response to the user. This is the engineer's primary review artifact — it must be visible in the conversation, not buried silently in git history. The same text is then reused as the commit message body in Step 6.

The summary has three sections:

**Changeset** — maps each rule to the file(s) and line(s) where it was implemented, with a one-line description of the change. Every rule addressed in this session must appear. Format: `RULE-N → file:line   description`. Rules satisfied by existing code (no changes needed): `RULE-N → (already satisfied)`. Rules mapping to multiple files get multiple lines.

```
── Changeset ──────────────────────────────────────

RULE-1 → src/auth.py:34         Added sanitize_input() before query
RULE-2 → src/auth.py:71         Sliding window rate limiter (60/min)
         tests/test_auth.py:12  2 proofs covering RULE-1 and RULE-2
```

**Decisions** — judgment calls where the agent chose between alternatives. Only genuine decisions, not mechanical translations. If there are no judgment calls: `(No judgment calls — all rules had unambiguous implementations)`.

```
── Decisions ──────────────────────────────────────

• Middleware pattern over inline validation for RULE-1 — reusable across routes
• 60 req/min hardcoded — spec says "rate limit" with no threshold
```

**Review** — curated list of areas where the engineer should focus attention. Flag security-sensitive code, spec ambiguities, performance-critical paths, and anything non-obvious. Not a list of every change — just the parts that need human eyes. If nothing notable: `(No notable risk areas — straightforward implementation)`.

```
── Review ─────────────────────────────────────────

→ src/auth.py:45   Regex for SQL injection — security-sensitive
→ Spec gap: RULE-3 says "rate limit" but doesn't specify the window size
```

**Corner cases:**
- If no code changes were needed (tests already pass), show `RULE-N → (already satisfied)` for each rule
- For specs with 10+ rules, list every rule in Changeset but keep Decisions and Review curated (3–5 items max)

## When Running as Proof Fixer

When spawned by the auditor to fix HOLLOW or WEAK proofs:

1. Read the audit findings — each has a PROOF-ID, issue description, and suggested fix
2. Read the spec rule and current test code
3. Fix the test to address the specific issue
4. Run purlin:unit-test to verify the fix works
5. Report back: "Fixed PROOF-N — now uses real bcrypt instead of mock. Re-audit please."
6. Print a changeset summary mapping fixed proofs: `PROOF-N → file:line  description of fix`. Skip the Decisions section — proof fixes are mechanical, not judgment calls.

Do NOT weaken assertions to satisfy audit — if the audit says a proof is HOLLOW because it mocks bcrypt, replace the mock with real bcrypt. Don't remove the assertion.
If fixing a proof requires changing the spec rule (because the rule is wrong), report the issue: "RULE-N in <feature> needs updating — <reason>."

## Step 6 — Commit (mandatory)

After the changeset summary, commit all changed files. Use the changeset summary as the commit message body per `references/commit_conventions.md` ("Build Commit Body"):

```
git add <source files> <test files> specs/**/*.proofs-*.json
git commit  # message body = changeset summary from Step 5
```

Do NOT commit after each failed iteration — only when stable. Do NOT defer the commit to a later step. Uncommitted proof files are invisible to drift detection and verification.

## Exit Criteria

The build is NOT complete until all of the following are true. Verify each one before responding to the user.

1. **Tests pass.** The last `purlin:unit-test` run shows the target feature as PASSING or better.
2. **Changeset summary visible.** The three-section summary (Changeset, Decisions, Review) was output as visible text in your response — not only in the commit message. The engineer reviews it in the conversation before looking at git.
3. **All changes committed.** Run `git status`. If any source files, test files, or `specs/**/*.proofs-*.json` files are uncommitted, commit them now using the changeset summary as the commit message body per Step 6.
4. **No uncommitted proof files.** `git status` must not show any modified or untracked `.proofs-*.json` files. These are invisible to `sync_status` until committed.
