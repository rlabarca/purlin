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

## What it does
User authentication with email and password.

## Rules
- RULE-1: Passwords are hashed with bcrypt before storage
- RULE-2: Failed logins are rate-limited to 5 per minute

## Proof
- PROOF-1 (RULE-1): Store a password; verify bcrypt hash in database
- PROOF-2 (RULE-2): Submit 6 invalid passwords; verify the 6th returns 429
```

**`## Rules`** — parsed by `sync_status`. Must use `RULE-N:` format.
**`## Proof`** — NOT parsed (except `@manual` stamps). Blueprint for the agent writing tests.
**`> Requires:`** — other specs/invariants whose rules also apply.
**`> Scope:`** — files this feature covers. Documentation only.

Full format: [references/formats/spec_format.md](../references/formats/spec_format.md)

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

![PM Workflow](../assets/lifecycle-pm-workflow.svg)

### Quick commands

| What you want | What you type |
|---------------|---------------|
| See what changed | `/purlin:changelog --role pm` |
| See rule coverage | `/purlin:status` |
| Write a new spec | `write a spec for notifications` |
| Add a rule to a spec | `add a rule to login: passwords must expire after 90 days` |
| Stamp a manual proof | `/purlin:verify --manual login PROOF-3` |
| Find a spec | `/purlin:find login` |

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

![Engineer Workflow](../assets/lifecycle-eng-workflow.svg)

### Quick commands

| What you want | What you type |
|---------------|---------------|
| See what needs work | `/purlin:changelog --role eng` |
| Build a feature | `build login` |
| Test a feature | `test login` |
| Fix failing tests | `fix the engineer priorities` after changelog |
| Work through all gaps | `work through the engineer priorities` after changelog |
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

![QA Workflow](../assets/lifecycle-qa-workflow.svg)

### Quick commands

| What you want | What you type |
|---------------|---------------|
| See what needs testing | `/purlin:changelog --role qa` |
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
