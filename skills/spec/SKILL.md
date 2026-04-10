---
name: spec
description: Scaffold or edit feature specs in 3-section format
---

Create or edit a spec from any input — plain English, PRDs, customer feedback, code files, or existing specs. The agent extracts structured rules from unstructured input. The user describes what they want; the agent writes the spec.

For **syntax**: `references/formats/spec_format.md`. For **quality**: `references/spec_quality_guide.md`.

## Usage

```
purlin:spec <name>              Create or edit a spec
purlin:spec <name> --anchor     Delegate to purlin:anchor create
purlin:spec <name> --review     Review an existing spec for rule quality
purlin:spec                     (no name — extract from user's input)
```

---

## --review Mode

Lightweight rule quality check. Reads an existing spec and evaluates each rule — no test execution, no file modifications, no proof files. Use this to catch quality problems before anyone writes tests.

### Step 1 — Load the spec

Find `specs/**/<name>.md`. If not found, error: "Spec not found. Run `purlin:spec <name>` to create it."

Read the spec in full. Also read the source files listed in `> Scope:` (if any) for context on what the code actually does.

### Step 2 — Evaluate each rule

For each `RULE-N:` line, apply the three tests from `references/spec_quality_guide.md` ("The rebuild test"):

1. **Rebuild test:** "If an engineer rebuilt this feature from only this spec, would they get this wrong without this rule?" If the answer is no — flag as `NOISE`.
2. **Behavior test:** Does this describe what the feature does, or how the code does it? Check for signals: names a library, hook, CSS value, token, internal function, or specific technique. If yes — flag as `IMPLEMENTATION`.
3. **Overlap test:** Would this rule always pass or fail together with another rule in the same spec? If yes — flag as `OVERLAP` and name the paired rule.

Also check:
- **Missing coverage:** Read the source code in `> Scope:` and identify behavioral aspects not covered by any rule. Flag each as `GAP` with a suggested rule.
- **Vague rules:** Rules that say "handle errors" or "work correctly" without specifying what happens. Flag as `VAGUE`.

### Step 3 — Report

```
Spec review: <name> (<N> rules)

  ✓ RULE-1: Returns 200 with JWT on valid credentials
  ✓ RULE-2: Returns 401 on invalid password
  ⚠ RULE-3: Uses bcrypt for password hashing — IMPLEMENTATION (names library; rewrite as: "Passwords are hashed before storage")
  ⚠ RULE-4: Locks account after 5 failures — OVERLAP with RULE-5 (same trigger condition)
  ✗ RULE-5: Handles rate limiting — VAGUE (what status code? what error message? what threshold?)

Suggested rules (GAP):
  + "Returns 429 with Retry-After header when rate limit exceeded" (rate limit response not specified)
  + "Login audit log records every attempt with timestamp, IP, and success/failure" (audit trail in code but not in spec)

Summary: 2 clean, 2 warnings, 1 vague, 2 gaps suggested
```

For bad→good rewrite examples, reference `references/rule_examples.md`.

### No writes

This mode is read-only. It does not modify the spec, create files, or run tests. The user takes the findings and applies them manually or via `purlin:spec <name>`.

---

## Step 1 — Accept Input

Accept ANY of these input types without asking which format it is:
- Plain English description ("users should be able to reset their password via email")
- PRD or requirements document (pasted or referenced)
- Customer feedback or feature request
- Slack/email thread describing a problem
- Existing spec name to update
- A file path to code that needs a spec
- **Image** (screenshot, mockup, design comp, whiteboard photo) — create a **design anchor**. Images are locally owned. See "Image-Based Design Anchors" below.

**If a spec name was given**, search `specs/**/<name>.md`:
- **Found:** Read the spec. Call `sync_status` for coverage. Go to Step 7 (Update Existing Spec).
- **Not found:** Use the name and any additional input to draft a new spec.

**If no name was given**, read the user's input and infer the feature name from the topic.

## Step 2 — Extract Everything Before Asking

If the input is substantial (more than a sentence or two), extract as much as possible BEFORE asking any questions:

- **Feature name** — infer from the topic
- **Category** — infer from the domain per `references/spec_quality_guide.md` ("Spec Categories"):
  - Auth, security → `security/` or component dir with `security_` anchor
  - File formats, contracts, cross-cutting standards → `schema/`
  - Reference docs, skill definitions, agent definitions → `instructions/`
  - End-to-end flows → `integration/`
  - Executable code → category matching the source directory
- **Rules** — extract every testable constraint mentioned or implied (see Step 5 heuristics)
- **Proof descriptions** — generate observable assertions with concrete inputs/outputs for each rule, with tier tags per the quality guide
- **Anchors** — if the input mentions security, compliance, design standards, check `specs/` for matching anchors to reference via `> Requires:`
- **Scope** — if code files are mentioned or inferable
- **Stack** — if technologies are mentioned

Present the **complete draft spec** to the user, followed by the approval block. Assumed rules should be visually obvious in the draft:

```
RULE-1: Fetches weather from OpenWeatherMap
RULE-2: Shows temperature in Fahrenheit
RULE-3: Cache results for 10 minutes (assumed — user said "don't hit the API too much")
RULE-4: Show error message on API failure
```

The PM sees the assumed tag and either confirms, changes the value, or asks a gap question.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ REVIEW DRAFT — Does this look right?

  [y] Looks good — continue to metadata
  [n] Start over
  [edit] I want to change specific rules or proofs

Waiting for your response...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Use `AskUserQuestion` to pause and wait. Do NOT skip this step. Then go to Step 3 for gap questions.

## Step 3 — Gap Questions (only what's missing)

After presenting the draft, ask ONLY about gaps — don't re-ask things the input already answered:
- "I couldn't determine the tech stack. What framework are you using?"
- "The input mentions authentication but I don't see a security anchor in your project. Should I create one?"
- "You mentioned 'fast response times' — what's the specific threshold? Under 200ms? Under 1 second?"
- "Is the email notification handled by your app or a third-party service?"
- "Your PRD mentions 3 requirements — are there others I missed?"

Questions must be **specific and gap-filling**, not generic ("what are the rules?" or "what are your requirements?").

## Step 4 — Show an Example First (for novice users)

If the input is **vague or minimal** (e.g., "write a spec for password reset" with no details), show a brief example BEFORE generating:

> Here's what a spec looks like:
>
> **Feature: password_reset**
>
> *What it does* — Allows users to reset their password via a time-limited email link.
>
> *Rules:*
> - RULE-1: POST /reset with valid email sends a reset link
> - RULE-2: Reset link expires after 24 hours
> - RULE-3: Clicking a valid link allows setting a new password
> - RULE-4: Clicking an expired link shows an error message
>
> *Proofs:*
> - PROOF-1 (RULE-1): POST /reset with registered email; verify 200 and email sent @integration
> - PROOF-2 (RULE-2): Create a link, advance clock 24h; verify link returns 410 Gone
> - PROOF-3 (RULE-3): Click valid link, submit new password; verify password changed @integration
> - PROOF-4 (RULE-4): Click expired link; verify error message displayed
>
> Now tell me about your feature and I'll draft the spec.

**Skip the example** if the input is already detailed (PRD, substantial description, pasted requirements).

## Step 5 — Rule Extraction Heuristics

When extracting rules from unstructured input, look for:

| Signal in input | Rule type | Example |
|----------------|-----------|---------|
| "must", "should", "needs to", "has to" | Direct constraint | RULE: Return 200 with session token on valid login |
| "never", "don't", "cannot", "forbidden" | FORBIDDEN pattern | RULE: FORBIDDEN — No plaintext password storage |
| Error cases, "what if", "fails when" | Error handling | RULE: Return 404 when user ID does not exist |
| "fast", "under N seconds", "real-time" | Boundary condition | RULE: API response time under 200ms at p95 |
| "first... then... finally" | Multi-step workflow | RULE: After email verification, account status changes to active |
| "only admins", "users with role X" | Access control | RULE: Only users with admin role can delete accounts |
| "stores", "saves", "records", "tracks" | Data persistence | RULE: Audit log records every login attempt with timestamp and IP |
| Sequences with conditions | State machine | RULE: Order status transitions: pending → paid → shipped → delivered |

For each extracted rule, generate an observable proof description with concrete inputs and expected outputs. Apply tier tags per `references/spec_quality_guide.md` ("Tier Tags on Proofs").

**Assumption tagging (mandatory):** After extracting rules, review each one. If the rule contains a specific number, threshold, algorithm, or constraint that the user did NOT explicitly state, add the `(assumed)` tag with context:

- User said "fast" → `RULE-3: Under 500ms (assumed — user said "fast")`
- User said "secure" → `RULE-4: bcrypt hashing (assumed — user said "secure")`
- User said "handles errors" → `RULE-5: Returns 500 with error body (assumed — user said "handles errors")`

If the user WAS explicit, no tag:
- User said "must return in under 200ms" → `RULE-3: Under 200ms` (no tag)
- User said "use argon2" → `RULE-4: argon2 hashing` (no tag)

## Step 6 — Enhance with Metadata

After the core spec (What it does, Rules, Proof) is solid, add metadata:

1. **Scan for matching anchors** in `specs/` and suggest `> Requires:` based on scope overlap:
   - For each anchor (specs in `specs/_anchors/`), read its `> Scope:` patterns
   - If the feature's `> Scope:` files overlap with the anchor's scope, suggest requiring it
   - Also note any global anchors (these are auto-applied and don't need `> Requires:`)
   - Present suggestions:
     ```
     Suggested > Requires: based on file overlap:
       api_rest_conventions — your Scope overlaps with src/api/
       security_no_eval — global anchor (auto-applied, no action needed)
     Add api_rest_conventions to > Requires:? [y/n]
     ```
2. If the user mentioned code files, populate `> Scope:` (verify paths exist)
3. If the user mentioned technologies, populate `> Stack:`
4. Apply tier tags to proofs per `references/spec_quality_guide.md`
5. Check if any rules are FORBIDDEN patterns and format proofs as grep-based assertions per "FORBIDDEN Grep Precision"
6. Suggest the category per `references/spec_quality_guide.md` ("Spec Categories")

**Rule quality check (mandatory):** Before presenting, apply the `--review` logic internally: evaluate every rule against the rebuild/behavior/overlap tests. Fix any IMPLEMENTATION or NOISE rules in the draft — don't present rules that fail the rebuild test.

Present the enhanced spec with metadata added and ask "anything to adjust?"

### Structural-Only Proof Check

After drafting the rules and proofs, if the spec covers files in `references/`, `skills/`, or `agents/` (instruction files), check: are ALL proofs grep-based or existence checks? If yes, suggest adding behavioral rules to **this same spec** — not a separate spec:

```
All proofs for this spec are structural (grep/existence checks). This catches
deletions and drift but doesn't prove the instructions work.

Consider adding behavioral rules to this spec. For example:
  RULE-N: Agent follows the core loop when given "build X" @e2e
  RULE-N+1: Agent uses purlin:spec when asked to "update the spec" @e2e
```

### NEVER Create Test-Only Specs

**Tests must prove rules in the feature they validate — not in a separate spec.**

Do NOT create specs whose sole purpose is to be a container for tests (e.g., `e2e_feature_scoped_overwrite`, `e2e_audit_cache_pipeline`). If a test validates that proof plugins preserve other features during overwrite, that test proves `proof_plugins` RULE-4 — wire it there.

When the user asks for "an e2e spec" or "integration tests for X":
1. Identify which existing feature spec the behavior belongs to
2. Add rules to THAT spec if they don't already exist
3. Write proof descriptions under THAT spec's `## Proof` section
4. Never create a parallel spec just because the tests are e2e tier

If the rule already exists in the target spec, the test just needs a proof marker pointing to it — no new rule or spec needed.

### Validate Before Commit

Before committing, verify:
- `## What it does` has at least one full sentence
- `## Rules` has at least one `RULE-N:` line, all numbered sequentially
- `## Proof` has at least one `PROOF-N (RULE-N):` line, each mapping to a rule
- Proof descriptions are observable assertions, not vague instructions
- Every proof description has an appropriate tier tag per `references/spec_quality_guide.md` ("Tier Tags on Proofs")
- All `> Scope:` file paths exist on disk
- **`> Requires:` validation (blocking):** For EACH reference in `> Requires:`, glob `specs/**/<name>.md`. If any referenced spec does not exist on disk, DO NOT commit the spec with the broken reference. Remove the broken reference from `> Requires:` and print: `Removed > Requires: <name> — spec not found. Create it first with purlin:spec <name>, then add the reference back.`

### Commit (mandatory)

After the spec is approved, commit immediately. Do not batch with other changes.

```
git add specs/<category>/<name>.md
git commit -m "spec(<name>): <description of change>"
```

This commit is mandatory — drift detection and staleness checks depend on committed spec state. Do not skip or defer.

## Step 7 — Update Existing Spec

When updating a spec that already exists on disk:

### 7a — Understand what changed

1. Call the `drift` MCP tool to see what changed since the last verification
2. Read the CURRENT spec in full — every rule, every proof, every metadata line
3. Read the changed source files referenced in the diff or in `> Scope:`
4. Read changed skill/reference files if the feature covers instructions

### 7b — Identify deltas

Compare the current spec against the code changes. Categorize each finding:

| Category | What it means | Action |
|----------|--------------|--------|
| NEW RULE NEEDED | Code added behavior not covered by any existing rule | Propose adding a new RULE-N |
| RULE OUTDATED | Existing rule describes behavior that changed | Propose updating the rule text |
| RULE OBSOLETE | Existing rule describes behavior that was removed | Propose removing the rule |
| PROOF OUTDATED | Proof description no longer matches the rule | Propose updating the proof text |
| METADATA STALE | `> Scope:` or `> Stack:` no longer accurate | Propose updating metadata |
| NO CHANGE | Existing rule still matches code | Keep as-is (explicitly note this) |

### 7c — Present the delta report

Show the user EXACTLY what will change and what will stay:

```
Spec: specs/mcp/sync_status.md (15 rules currently)

KEEPING (unchanged):
  RULE-1: sync_status tool returns valid report ✓
  RULE-2: Proof files are parsed correctly ✓
  RULE-3: Coverage is computed for all features ✓
  ...

ADDING:
  RULE-23 (new): sync_status scans specs/_anchors/ for anchor specs
    Reason: Anchor directory support added
    Proposed proof: PROOF-23 (RULE-23): Create anchor in specs/_anchors/, run sync_status, verify anchor rules appear

UPDATING:
  RULE-20 (changed): Global anchors auto-apply to all features
    Was: "Global specs with > Global: true auto-apply"
    Now: "Anchor specs in specs/_anchors/ with > Global: true auto-apply to all non-anchor features"
    Reason: Anchor unification

REMOVING:
  (none)

METADATA:
  ▎ Stack: unchanged
  ▎ Scope: unchanged
  ▎ Requires: unchanged

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ APPROVAL REQUIRED — Review the changes above.

  [y] Approve and apply all changes
  [n] Cancel — make no changes
  [edit] I want to adjust specific items

Waiting for your response...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**This approval block is MANDATORY.** The agent MUST use `AskUserQuestion` to pause and wait for the user's response. Do NOT auto-approve. Do NOT proceed without an explicit answer. The bordered block above is the exact format to use — it must be visually distinct from the rest of the output so the user doesn't scroll past it.

### 7d — Apply approved changes

1. Preserve ALL unchanged rules exactly as they are — same text, same numbering
2. Add new rules at the end of the existing sequence (RULE-9 after RULE-8)
3. Update changed rules in place — same RULE-N number, new text
4. For removed rules: renumber remaining rules sequentially (no gaps)
5. For each new or updated rule, add or update the corresponding PROOF-N line
6. Apply tier tags to new proofs per `references/spec_quality_guide.md`
7. Preserve any existing `@manual` stamps — do NOT remove manual proof stamps unless the rule they reference was removed
8. Preserve rule tags on unchanged rules — `(assumed)`, `(confirmed)`, `(deferred)` stay as-is
9. If updating a rule that had `(confirmed)`, change the tag to `(assumed)` since the new value hasn't been confirmed yet
10. Update `> Scope:` if new files were added to the feature
11. Update `> Stack:` if new dependencies were introduced

### 7e — Validate and commit

Same validation as new specs: no empty sections, sequential numbering, observable proofs, valid references, tier tags.

### Commit (mandatory)

After the spec update is approved, commit immediately. Do not batch with other changes.

```
git add specs/<category>/<name>.md
git commit -m "spec(<name>): update rules for <description>"
```

This commit is mandatory — drift detection and staleness checks depend on committed spec state. Do not skip or defer.

### Key principles for updates

- **Never silently change existing rules.** Every change must be shown to the user.
- **Never remove `@manual` stamps** unless the rule was deleted.
- **Preserve rule numbering** when possible — renumber only when rules are removed.
- **Show what's staying, not just what's changing.** The user needs to see the full picture to approve confidently.
- **Ask before applying.** The delta report is a proposal, not a fait accompli.

---

## Anchor Specs

When `--anchor` is specified, delegate to `purlin:anchor create` with the same arguments. Do not create the anchor directly in this skill.

See `references/formats/anchor_format.md` for format, `references/spec_quality_guide.md` for when to create anchors and FORBIDDEN pattern guidance.

### Image-Based Design Anchors

When the user provides an image (screenshot, mockup, design comp, whiteboard photo):

1. Save the image to `specs/_anchors/screenshots/<name>.png` (create the screenshots directory if needed).

2. Compute and store the image hash in the spec metadata:
   ```
   > Visual-Reference: ./specs/_anchors/screenshots/<name>.png
   > Visual-Hash: sha256:a1b2c3d4e5f6...
   ```
   This enables staleness detection — if the image is later replaced, `sync_status` will warn that the anchor may need review.

3. Create an anchor spec with:
   - `> Visual-Reference:` and `> Visual-Hash:` as above
   - `> Scope:` pointing to the code files that will implement the design
   - One visual match rule: `RULE-1: Implementation must visually match the reference image`
   - One screenshot comparison proof (using the project's test framework) tagged `@e2e`
   - If the user describes behavioral requirements alongside the image, add those as additional rules

4. Commit the image AND the spec together.

---

## Key Principles

- The user describes what they want in **their** language. The agent writes RULE-N format.
- Extract everything possible from the input before asking questions.
- Questions are specific and gap-filling, not generic.
- Show, don't tell. Present the draft spec, then refine — don't ask the user to write rules.
- Progressive disclosure: core spec first, metadata second, anchors third.

## Exit Criteria

The spec operation is NOT complete until all of the following are true. Verify each one before responding to the user.

1. **Spec file committed.** Run `git status`. If the spec `.md` file is uncommitted, commit it now per the commit instructions above.
2. **No uncommitted spec files.** `git status` must not show any modified or untracked `specs/**/*.md` files from this session.

If any criterion is not met, fix it before completing. Do not respond to the user with "done" or "complete" until both are verified.
