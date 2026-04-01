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
- **Found:** Read the spec. Call `sync_status` for coverage. Ask the user what to change. Go to Step 7 (Update).
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

### Validate Before Commit

Before committing, verify:
- `## What it does` has at least one full sentence
- `## Rules` has at least one `RULE-N:` line, all numbered sequentially
- `## Proof` has at least one `PROOF-N (RULE-N):` line, each mapping to a rule
- Proof descriptions are observable assertions, not vague instructions
- All `> Requires:` references point to existing specs
- All `> Scope:` file paths exist on disk

```
git commit -m "spec(<name>): <description of change>"
```

## Step 7 — Update from Code Changes

When updating an existing spec (the user says "update the login spec" or "the code changed"):

1. Call the `changelog` MCP tool to see what changed since last verification
2. Read the current spec and changed source files
3. Propose additions/modifications — new error paths, changed boundaries, new config options
4. Present the diff: "I'd add RULE-5 and update PROOF-2. Here's the updated spec."
5. Validate and commit as above

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
