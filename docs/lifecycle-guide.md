# The Purlin Lifecycle

How PM, Engineer, and QA collaborate through specs, code, and proofs.

## The Big Picture

```mermaid
graph LR
    PM[PM writes spec] --> ENG[Engineer builds code + tests]
    ENG --> STATUS{sync_status}
    STATUS -->|all rules proved| QA[QA verifies]
    STATUS -->|gaps exist| ENG
    QA -->|manual proofs needed| QA
    QA -->|all proofs pass| VERIFY[purlin:verify]
    VERIFY --> RECEIPT[Verification Receipt]
    RECEIPT --> DEPLOY[Deploy]

    PM -.->|reviews changelog| STATUS
    PM -.->|updates rules| PM
    ENG -.->|writes specs too| PM
    QA -.->|writes tests too| ENG
```

Every role can do every job. The arrows show the typical flow, not restrictions.

## How It Works

1. **Specs define rules.** A PM (or engineer, or anyone) writes `RULE-1: passwords must be hashed with bcrypt`.
2. **Tests prove rules.** An engineer writes a test marked `@pytest.mark.proof("login", "PROOF-1", "RULE-1")`.
3. **`sync_status` shows the gaps.** 3/5 rules proved means 2 rules need tests.
4. **`purlin:verify` locks it in.** All rules proved = verification receipt with a tamper-evident hash.

That's it. No tracking system, no ledger, no state files. The filesystem is the state.

---

## PM Workflow

```mermaid
graph TD
    START[Start session] --> CL[purlin:changelog --role pm]
    CL --> REVIEW{What needs attention?}
    REVIEW -->|new code without specs| SPEC[Write specs with rules]
    REVIEW -->|spec drift| UPDATE[Update rules to match intent]
    REVIEW -->|manual proofs stale| MANUAL[Re-verify manual proofs]
    REVIEW -->|everything clean| DONE[Done]
    SPEC --> COMMIT[Commit spec]
    UPDATE --> COMMIT
    MANUAL --> STAMP["purlin:verify --manual feature PROOF-N"]
    STAMP --> COMMIT
    COMMIT --> STATUS[purlin:status to confirm]
    STATUS --> DONE
```

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

```mermaid
graph TD
    START[Start session] --> CL[purlin:changelog --role eng]
    CL --> PICK{Pick a priority}
    PICK -->|failing tests| FIX[Fix code or tests]
    PICK -->|unproved rules| BUILD[Write code + tests]
    PICK -->|new unspecced code| SPEC[Write spec first]
    FIX --> TEST[purlin:unit-test]
    BUILD --> TEST
    SPEC --> BUILD
    TEST -->|failures| FIX
    TEST -->|all pass| STATUS[purlin:status]
    STATUS -->|gaps remain| PICK
    STATUS -->|all READY| VERIFY[purlin:verify]
    VERIFY --> DONE[Done]
```

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

```mermaid
graph TD
    START[Start session] --> CL[purlin:changelog --role qa]
    CL --> PICK{Pick a priority}
    PICK -->|stale manual proofs| MANUAL[Re-verify manually]
    PICK -->|features READY| VERIFY[purlin:verify]
    PICK -->|coverage gaps| TEST[Write more tests]
    MANUAL --> STAMP["purlin:verify --manual feature PROOF-N"]
    TEST --> RUN[purlin:unit-test]
    RUN -->|failures| FIX[Fix tests]
    FIX --> RUN
    RUN -->|pass| STATUS[purlin:status]
    STAMP --> STATUS
    STATUS -->|gaps remain| PICK
    STATUS -->|all READY| VERIFY
    VERIFY --> DONE[Done]
```

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

```mermaid
sequenceDiagram
    participant PM
    participant Engineer
    participant QA

    PM->>PM: write spec with rules
    PM->>PM: commit and push
    Engineer->>Engineer: purlin:changelog --role eng
    Engineer->>Engineer: build code + tests
    Engineer->>Engineer: iterate until READY
    Engineer->>Engineer: commit and push
    QA->>QA: purlin:changelog --role qa
    QA->>QA: verify manual proofs
    QA->>QA: purlin:verify
    QA->>QA: commit receipt and push
    PM->>PM: purlin:changelog --role pm
    PM->>PM: sees all features verified
```

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
