---
name: spec
description: Scaffold or edit feature specs in 3-section format
---

Create or edit a spec from any input — plain English, PRDs, customer feedback, code files, or existing specs. The agent extracts structured rules from unstructured input. The user describes what they want; the agent writes the spec.

For **syntax**: `references/formats/spec_format.md`. For **quality**: `references/spec_quality_guide.md`.

## Usage

```
purlin:spec <name>              Create or edit a spec
purlin:spec <name> --anchor     Create an anchor spec (design_, api_, etc.)
purlin:spec <name> --invariant  Create an invariant spec (i_<prefix>_<name>)
purlin:spec                     (no name — extract from user's input)
```

---

## Step 1 — Accept Input

Accept ANY of these input types without asking which format it is:
- Plain English description ("users should be able to reset their password via email")
- PRD or requirements document (pasted or referenced)
- Customer feedback or feature request
- Slack/email thread describing a problem
- Existing spec name to update
- A file path to code that needs a spec

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

Present the **complete draft spec** to the user. Then go to Step 3 for gap questions.

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
> - PROOF-1 (RULE-1): POST /reset with registered email; verify 200 and email sent @slow
> - PROOF-2 (RULE-2): Create a link, advance clock 24h; verify link returns 410 Gone
> - PROOF-3 (RULE-3): Click valid link, submit new password; verify password changed @slow
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

## Step 6 — Enhance with Metadata

After the core spec (What it does, Rules, Proof) is solid, add metadata:

1. Check for matching anchors in `specs/` and suggest `> Requires:` if relevant
2. If the user mentioned code files, populate `> Scope:` (verify paths exist)
3. If the user mentioned technologies, populate `> Stack:`
4. Apply tier tags to proofs per `references/spec_quality_guide.md`
5. Check if any rules are FORBIDDEN patterns and format proofs as grep-based assertions per "FORBIDDEN Grep Precision"
6. Suggest the category per `references/spec_quality_guide.md` ("Spec Categories")

Present the enhanced spec with metadata added and ask "anything to adjust?"

### Structural-Only Proof Check

After drafting the rules and proofs, if the spec covers files in `references/`, `skills/`, or `agents/` (instruction files), check: are ALL proofs grep-based or existence checks? If yes, suggest:

```
All proofs for this spec are structural (grep/existence checks). This catches
deletions and drift but doesn't prove the instructions work.

Want me to also create an E2E spec in specs/integration/ that tests actual
behavior? For example:
  RULE-1: Agent follows the core loop when given "build X" @e2e
  RULE-2: Agent uses purlin:spec when asked to "update the spec" @e2e
```

Only suggest — do not create the E2E spec unless the user confirms.

### Validate Before Commit

Before committing, verify:
- `## What it does` has at least one full sentence
- `## Rules` has at least one `RULE-N:` line, all numbered sequentially
- `## Proof` has at least one `PROOF-N (RULE-N):` line, each mapping to a rule
- Proof descriptions are observable assertions, not vague instructions
- Every proof description has an appropriate tier tag per `references/spec_quality_guide.md` ("Tier Tags on Proofs")
- All `> Scope:` file paths exist on disk
- **`> Requires:` validation (blocking):** For EACH reference in `> Requires:`, glob `specs/**/<name>.md`. If any referenced spec does not exist on disk, DO NOT commit the spec with the broken reference. Remove the broken reference from `> Requires:` and print: `Removed > Requires: <name> — spec not found. Create it first with purlin:spec <name>, then add the reference back.`

```
git commit -m "spec(<name>): <description of change>"
```

## Step 7 — Update Existing Spec

When updating a spec that already exists on disk:

### 7a — Understand what changed

1. Call the `changelog` MCP tool to see what changed since the last verification
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
Spec: specs/hooks/gate_hook.md (8 rules currently)

KEEPING (unchanged):
  RULE-1: The hook triggers on Write, Edit, and NotebookEdit ✓
  RULE-2: Files not matching specs/invariants/i* pass through ✓
  RULE-3: When no bypass lock exists, writes are blocked ✓
  ...

ADDING:
  RULE-9 (new): Agent must re-read proof description after fixing a failing test
    Reason: New guardrail added to build skill
    Proposed proof: PROOF-9 (RULE-9): Fix a test, verify build skill re-reads the original proof description from the spec

UPDATING:
  RULE-5 (changed): Error message includes specific corrective action
    Was: "Error message is written to stderr"
    Now: "Error message is written to stderr AND includes the exact purlin:invariant sync command"
    Reason: gate.sh error messages were enhanced

REMOVING:
  (none)

METADATA:
  ▎ Stack: unchanged
  ▎ Scope: unchanged
  ▎ Requires: unchanged

Approve these changes? [y/n/edit]
```

### 7d — Apply approved changes

1. Preserve ALL unchanged rules exactly as they are — same text, same numbering
2. Add new rules at the end of the existing sequence (RULE-9 after RULE-8)
3. Update changed rules in place — same RULE-N number, new text
4. For removed rules: renumber remaining rules sequentially (no gaps)
5. For each new or updated rule, add or update the corresponding PROOF-N line
6. Apply tier tags to new proofs per `references/spec_quality_guide.md`
7. Preserve any existing `@manual` stamps — do NOT remove manual proof stamps unless the rule they reference was removed
8. Update `> Scope:` if new files were added to the feature
9. Update `> Stack:` if new dependencies were introduced

### 7e — Validate and commit

Same validation as new specs: no empty sections, sequential numbering, observable proofs, valid references, tier tags.

```
git commit -m "spec(<name>): update rules for <description>"
```

### Key principles for updates

- **Never silently change existing rules.** Every change must be shown to the user.
- **Never remove `@manual` stamps** unless the rule was deleted.
- **Preserve rule numbering** when possible — renumber only when rules are removed.
- **Show what's staying, not just what's changing.** The user needs to see the full picture to approve confidently.
- **Ask before applying.** The delta report is a proposal, not a fait accompli.

---

## Anchor Specs

Anchors are regular specs with type-prefixed names. Use `--anchor` flag.
Type prefixes: `design_`, `api_`, `security_`, `brand_`, `platform_`, `schema_`, `legal_`, `prodbrief_`.
See `references/formats/anchor_format.md` for format, `references/spec_quality_guide.md` for when to create anchors and FORBIDDEN pattern guidance.

## Invariant Specs

Invariants live in `specs/_invariants/i_<prefix>_<name>.md`. Use `--invariant` flag.
See `references/formats/invariant_format.md` for the invariant format with `> Source:` and `> Pinned:` metadata.

---

## Key Principles

- The user describes what they want in **their** language. The agent writes RULE-N format.
- Extract everything possible from the input before asking questions.
- Questions are specific and gap-filling, not generic.
- Show, don't tell. Present the draft spec, then refine — don't ask the user to write rules.
- Progressive disclosure: core spec first, metadata second, anchors/invariants third.
