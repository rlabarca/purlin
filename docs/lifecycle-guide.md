# The Purlin Lifecycle

How PM, Engineer, and QA collaborate through specs, code, and proofs.

## The Big Picture

![Purlin Lifecycle](../assets/lifecycle-big-picture.svg)

Every role can do every job. The arrows show the typical flow, not restrictions.

## How It Works

1. **Specs define rules.** A PM (or engineer, or anyone) writes `RULE-1: passwords must be hashed with bcrypt`.
2. **Tests prove rules.** An engineer writes a test marked `@pytest.mark.proof("login", "PROOF-1", "RULE-1")`.
3. **`sync_status` shows the gaps.** 3/5 rules proved means 2 rules need tests.
4. **`purlin:verify` locks it in.** All rules proved = verification receipt with a tamper-evident hash.

That's it. No tracking system, no ledger, no state files. The filesystem is the state.

### Spec Format

```markdown
# Feature: login

> Requires: i_security_policy
> Scope: src/auth/login.js, src/auth/session.js
> Stack: node/express, bcrypt, jsonwebtoken

## What it does
User authentication with email and password.

## Rules
- RULE-1: Passwords are hashed with bcrypt before storage
- RULE-2: Failed logins are rate-limited to 5 per minute

## Proof
- PROOF-1 (RULE-1): Store a password; verify bcrypt hash in database @slow
- PROOF-2 (RULE-2): Submit 6 invalid passwords; verify the 6th returns 429 @slow
```

**`## Rules`** — parsed by `sync_status`. Must use `RULE-N:` format.
**`## Proof`** — NOT parsed (except `@manual` stamps). Blueprint for the agent writing tests.
**`> Requires:`** — other specs/invariants whose rules also apply.
**`> Scope:`** — files this feature covers. Documentation only.

Full format: [references/formats/spec_format.md](../references/formats/spec_format.md)
Quality guide: [references/spec_quality_guide.md](../references/spec_quality_guide.md) — how to write good rules, proofs, and anchors

### Coverage States

| State | Meaning |
|-------|---------|
| READY | All rules proved |
| PASS | Rule has a passing proof |
| FAIL | Rule has a failing proof |
| NO PROOF | No test linked to this rule |
| MANUAL PROOF STALE | Manual stamp exists but code changed since |
| MANUAL PROOF NEEDED | Manual proof declared but not stamped |

### Verification Receipts

`purlin:verify` runs all tests and issues a receipt: `verify: [Complete:all] features=3 vhash=f7a2b9c1`. The `vhash` proves these rules had these test outcomes. CI `--audit` re-runs everything independently.

---

## PM Workflow

**The PM defines what the software must do.** They own the rules — the testable constraints that the code must satisfy. Purlin helps PMs transform raw ideas (PRDs, customer feedback, Slack threads) into structured specs with numbered rules and proof descriptions. When engineers build and test, the PM sees exactly which rules are proved and which aren't via `sync_status`. No more "is this feature done?" — the coverage number answers it.

![PM Workflow](../assets/lifecycle-pm-workflow.svg)

### Quick commands

| What you want | What you type |
|---------------|---------------|
| See what changed | `/purlin:changelog --role pm` |
| Handle all PM work | `handle PM items` |
| See rule coverage | `/purlin:status` |
| Write a new spec | `write a spec for notifications` |
| Add a rule to a spec | `add a rule to login: passwords must expire after 90 days` |
| Update a spec after code changed | `update the spec for login to reflect the recent changes` |
| Stamp a manual proof | `/purlin:verify --manual login PROOF-3` |
| Find a spec | `/purlin:find login` |

### Turning ideas into specs

You don't need to know Purlin's format. Just give Claude your raw input — a PRD, customer feedback, a Slack thread, or a plain English description — and it extracts the spec for you.

**From a plain description:**
```
I need password reset. Users click "forgot password", get an email with a link,
click it, set a new password. The link should expire after 24 hours.
```

Claude drafts a complete spec with rules (`RULE-1: POST /reset sends email with link`, `RULE-2: Link expires after 24 hours`, ...) and proof descriptions. Review the draft, adjust, done.

**From a PRD or requirements doc:**
```
Here's our PRD for the checkout flow: [paste or reference the doc]
```

Claude reads the entire document, extracts every testable constraint as a rule, generates proof descriptions, suggests anchors if it detects cross-cutting concerns (API conventions, security requirements), and presents the complete spec. It only asks follow-up questions about genuine gaps — not things already answered in the PRD.

**From customer feedback:**
```
Customers are complaining that search is slow and doesn't handle typos.
```

Claude translates complaints into rules: `RULE-1: Search returns results in under 500ms`, `RULE-2: Search handles common typos via fuzzy matching`. The PM refines the thresholds and priorities.

**What the PM DOESN'T do:**
- Write `RULE-N:` format — Claude does that
- Know what `> Requires:`, `> Scope:`, or `> Stack:` mean — Claude fills metadata automatically
- Decide on proof tiers (`@slow`, `@e2e`, `@manual`) — Claude applies the heuristics
- Write proof descriptions — Claude generates observable assertions from the rules

**What the PM DOES do:**
- Describe what the feature should do in their own words
- Review the drafted rules — are they right? Are any missing?
- Answer gap questions — "You mentioned 'fast.' Under 200ms? Under 1 second?"
- Stamp manual proofs for things automation can't check (brand voice, UX feel)

### Updating specs when code changes

Engineers change code. The PM needs to know: do the specs still match? Here's the workflow:

**Step 1: See what changed**
```
/purlin:changelog --role pm
```

The changelog shows NEEDS ATTENTION items and ends with ACTION ITEMS — a complete list of everything the PM needs to do:

```
ACTION ITEMS (PM):
  1. Spec drift: purlin_skills — 7 new behaviors not covered by existing rules → Run: purlin:spec purlin_skills
  2. Spec drift: purlin_references — 3 new sections not covered → Run: purlin:spec purlin_references
  3. Missing spec: notifications — new code with no spec → Run: purlin:spec notifications
```

**Step 2: Handle all items at once**

Instead of updating specs one by one, just say:
```
handle PM items
```

Claude runs through every item in the ACTION ITEMS list, invoking `purlin:spec` for each affected feature. Or update one at a time:
```
update the spec for login to reflect the recent changes
```

Claude reads the existing spec and the code diff, then presents a **delta report** — showing exactly what will change and what stays:

```
Spec: specs/auth/login.md (5 rules currently)

KEEPING (unchanged):
  RULE-1: Returns 200 with JWT on valid credentials ✓
  RULE-2: Returns 401 on invalid credentials ✓
  RULE-3: Passwords compared using bcrypt ✓

ADDING:
  RULE-6 (new): Rate limiting blocks after 10 failed attempts per minute
    Reason: rate_limit.js was added in recent commit

UPDATING:
  RULE-4 (changed): Session timeout after 60 minutes
    Was: "Session timeout after 30 minutes"
    Reason: config changed from 30 to 60

REMOVING:
  (none)

Approve these changes? [y/n/edit]
```

The PM reviews and approves. Existing rules stay intact. New rules are added at the end. Changed rules are updated in place. Nothing happens without PM approval.

**Step 3: Check coverage**
```
/purlin:status
```

After spec updates, new rules show as NO PROOF — which is correct. The engineer writes tests for the new rules.

**What the PM DOESN'T do:**
- Manually diff code against specs
- Renumber rules or write RULE-N format
- Figure out which specs are affected by code changes
- Write proof descriptions from scratch

**What the PM DOES do:**
- Run changelog to see what changed
- Say "update the spec for X" and review the proposed deltas
- Approve or adjust the changes

### What PMs own

- **Rules** in the `## Rules` section — what the code must do
- **Proof descriptions** in the `## Proof` section — what tests should verify (the blueprint, not the test code)
- **Manual proof stamps** — verifying things automation can't check (brand voice, UX feel)

### PMs can also

- Write code and tests (just ask Claude)
- Run tests (`test login`)
- Verify features (`/purlin:verify`)
- Create invariants from external sources (`/purlin:invariant sync`)

---

## Engineer Workflow

**The Engineer builds code that satisfies the rules and writes tests that prove it.** Purlin injects the spec's rules into the build context so the engineer always knows what constraints to satisfy. The build/test loop is simple: write code, write proof-marked tests, run them, iterate until `sync_status` shows READY. When rules and proofs align, the engineer ships with confidence — the verification receipt proves the code does what the spec says.

![Engineer Workflow](../assets/lifecycle-eng-workflow.svg)

### Quick commands

| What you want | What you type |
|---------------|---------------|
| See what needs work | `/purlin:changelog --role eng` |
| Build a feature | `build login` |
| Test a feature | `test login` |
| Handle all engineer work | `handle engineer items` |
| Work through all gaps | `work through the engineer action items` |
| See coverage | `/purlin:status` |
| Ship it | `/purlin:verify` |

### The build/test loop

This is the most common workflow. You say `test login` and Claude:

1. Reads the spec and its rules
2. Checks if code exists — builds it if not
3. Writes tests with proof markers
4. Runs `purlin:unit-test`
5. If tests fail, fixes and retries
6. Repeats until `sync_status` shows READY

You can also say `build login` to just write code (Claude injects the spec rules into context), then `test login` separately.

### Engineers can also

- Write and edit specs (`write a spec for notifications`)
- Stamp manual proofs (`/purlin:verify --manual login PROOF-3`)
- Create invariants (`/purlin:invariant sync`)
- Review changelogs for any role (`/purlin:changelog --role pm`)

---

## QA Workflow

**QA verifies that the code truly meets the spec — not just that tests pass, but that the right tests exist.** Purlin shows QA exactly which rules have proofs and which don't, which manual proofs are stale, and which features are ready for verification. QA stamps manual proofs for things automation can't check (visual quality, UX flow, brand voice) and runs `purlin:verify` to issue the final verification receipt. QA is the last gate before code ships.

![QA Workflow](../assets/lifecycle-qa-workflow.svg)

### Quick commands

| What you want | What you type |
|---------------|---------------|
| See what needs testing | `/purlin:changelog --role qa` |
| Handle all QA work | `handle QA items` |
| See coverage gaps | `/purlin:status` |
| Run all tests | `/purlin:unit-test` |
| Verify and ship | `/purlin:verify` |
| Stamp a manual proof | `/purlin:verify --manual checkout PROOF-4` |
| Write a test for an unproved rule | `write a test for login RULE-3` |

### Manual proof verification

Some rules can't be automated ("brand voice must be playful", "checkout flow is intuitive"). QA verifies these by hand:

1. Read the proof description in the spec: `PROOF-3 (RULE-3): Review error copy against brand guide @manual`
2. Perform the check
3. Stamp it: `/purlin:verify --manual login PROOF-3`
4. The stamp auto-captures your email, today's date, and the current commit SHA
5. If code changes later, `sync_status` flags the stamp as stale

### QA can also

- Write code (`fix the login bug`)
- Write specs (`write a spec for notifications`)
- Build features (`build login`)
- Everything an engineer or PM can do

---

## Cross-Role Collaboration

### The handoff pattern

![Cross-Role Handoff](../assets/lifecycle-handoff.svg)

### No handoff needed

The handoff pattern is typical but not required. A solo developer does all three:

```
write a spec for login with rules for auth, rate limiting, and session timeout
build it
test it
/purlin:verify
```

Four messages. Spec → code → tests → receipt.

---

## How AI Instructions Fit into Rule-Proof Design

Not all of Purlin's behavior lives in Python or shell scripts. Agent definitions (`agents/purlin.md`), skill definitions (`skills/*/SKILL.md`), and reference docs (`references/`) are instructions that control what the AI does. They're as much "code" as the MCP server — if someone changes the spec quality guide, Purlin's behavior changes.

But instructions aren't testable the same way executable code is. You can't call a function on a markdown file. So Purlin uses two levels of verification:

### Level 2: Structural specs (cheap, fast)

Spec the structure of instructions — verify sections exist, required content is present, naming conventions are followed.

```markdown
# Feature: purlin_references

> Scope: references/spec_quality_guide.md, references/formats/*.md

## Rules
- RULE-1: spec_quality_guide.md contains sections for Tier Tags, FORBIDDEN Grep Precision, and Edge Case Specificity
- RULE-2: Every format file in references/formats/ has a Template section with a complete example

## Proof
- PROOF-1 (RULE-1): Grep spec_quality_guide.md for "## Tier Tags", "## FORBIDDEN Grep Precision", "## Edge Case"; verify all present
- PROOF-2 (RULE-2): For each file in references/formats/, grep for "## Template"; verify present
```

These are default-tier tests. They catch accidental deletions and structural drift immediately.

### Level 3: E2E integration tests (expensive, nightly)

The real proof that instructions work is: **does the agent produce correct output when following them?**

```markdown
# Feature: e2e_purlin_lifecycle

> Scope: agents/purlin.md, skills/*/SKILL.md, references/**
> Requires: schema_spec_format, schema_proof_file

## Rules
- RULE-1: purlin:init creates .purlin/ and specs/ directories
- RULE-2: purlin:spec-from-code generates specs with numbered rules and observable proofs
- RULE-3: purlin:unit-test emits proof files next to specs
- RULE-4: purlin:status reports coverage with → directives
- RULE-5: purlin:verify issues receipts with valid vhash

## Proof
- PROOF-1 (RULE-1): Run purlin:init on empty project; verify directories exist @e2e
- PROOF-2 (RULE-2): Run purlin:spec-from-code; verify generated specs have RULE-N and PROOF-N lines @e2e
- PROOF-3 (RULE-3): Run tests with proof markers; verify .proofs-*.json files appear next to specs @e2e
- PROOF-4 (RULE-4): Run sync_status; verify output contains → directives @e2e
- PROOF-5 (RULE-5): Run purlin:verify; verify receipt.json with vhash @e2e
```

The E2E test exercises every instruction file in the system. If the agent definition is wrong, the E2E breaks. If the spec quality guide is missing a section, generated specs will lack that quality, and the structural spec catches it.

### Where these specs live

| Category | What goes there |
|----------|----------------|
| `specs/integration/` | E2E flows testing the full system |
| `specs/instructions/` | Structural specs for agent instructions (references, skills) |

### The bottom line

You don't need to write simulation tests for every reference doc. You need:
- **Structural specs** (cheap) that catch deletions and drift → `specs/instructions/`
- **One solid E2E flow** (expensive, `@e2e` tier, runs nightly) that proves the whole system works → `specs/integration/`

The structural specs are the smoke detector. The E2E is the fire drill.

`sync_status` flags features with structural-only proofs: `READY (structural only)`. This means the document's sections exist but no test verifies the system actually follows the instructions. When you see this, consider adding E2E proofs in `specs/integration/`.

---

## CI Integration

```yaml
# Fast gate — every push
on: push
  - run: purlin:unit-test

# Full proof — nightly
on: schedule (nightly)
  - run: purlin:verify

# Deploy gate
on: deploy
  - run: purlin:invariant sync --check-only
  - run: purlin:verify --audit
```

`--audit` is a clean-room re-execution: deletes all proof files, re-runs every test, recomputes the verification hash, and compares to the committed receipt. If they match, CI independently confirmed the developer's local verification.
