# Purlin in Regulated Environments

**Purlin is a development productivity tool, not a compliance system.** It does not replace a Quality Management System (QMS), does not provide legally binding electronic signatures, and does not produce audit trails that satisfy FDA 21 CFR Part 11, HIPAA, SOC2, or similar regulatory frameworks on its own.

What Purlin does provide: **structured, machine-readable artifacts** (specs with rules, proof results, verification receipts) that can feed into an external compliance pipeline. The rule-proof-receipt model gives your compliance infrastructure something concrete to validate — not just "tests passed" but "these specific rules were proved by these specific tests at this specific point in time."

---

## What Purlin Is NOT

- **Not a QMS.** Purlin does not manage document control, change control, or approval workflows.
- **Not a signature system.** `@manual` stamps and `git config user.email` are developer conveniences, not legally binding electronic signatures. GPG-signed commits prove key possession, not identity or intent.
- **Not tamper-proof.** Everything Purlin produces lives in the git repository, which is mutable. `git push --force` can erase any receipt.
- **Not an audit trail.** Git history is a development log, not an immutable compliance record.
- **Not a test quality gate.** Purlin proves that a test executed and passed. It does not prove that the test contains meaningful assertions. An AI agent can write `assert True` and produce a valid proof. Regulated teams must enforce independent human review of test logic (e.g., via CODEOWNERS or QMS-managed test approval) before accepting proof artifacts.

---

## What Purlin Produces (integration points)

Purlin generates structured artifacts that a real compliance system can consume:

| Artifact | Location | What it contains | How compliance uses it |
|----------|----------|-----------------|----------------------|
| **Spec files** | `specs/<category>/<name>.md` | Numbered rules (`RULE-N`) defining required behavior | Input to requirements traceability matrix |
| **Proof files** | `specs/<category>/<name>.proofs-*.json` | Test results linked to specific rules | Evidence of verification, consumed by QMS |
| **Verification receipts** | Git commit messages (`verify: [Complete:all] vhash=...`) | Hash of rules + proof results | Snapshot for compliance ledger to ingest |
| **Manual proof stamps** | `@manual(email, date, sha)` in spec | Record of human verification | Starting point — QMS must re-authenticate and countersign |
| **Invariant files** | `specs/_invariants/i_*.md` | External constraints with `> Pinned:` version | Source-of-truth tracking for external standards |

These artifacts are **inputs to your compliance pipeline**, not the pipeline itself.

### Purlin's enforcement layers

Purlin enforces proofs at three layers, each with different trust properties:

| Layer | Trust level | What it catches |
|-------|------------|----------------|
| **Layer 1: Git pre-push hook** | Low — local, bypassable with `--no-verify` | Developer mistakes (broken proofs before they reach remote) |
| **Layer 2: CI pipeline** | Medium — remote, configured by team | Code that doesn't pass tiered proof checks |
| **Layer 3: Deploy gate (`--audit`)** | Higher — clean-room re-execution | Tampered proof files, weakened tests, stale receipts |

**For regulated environments, Layer 3 is required but not sufficient.** The `--audit` re-execution proves the tests pass in CI, but it doesn't prove the tests are meaningful (see "Not a test quality gate" above). Your QMS must independently verify test quality.

---

## How a Regulated Pipeline Would Use Purlin

In a compliant architecture, Purlin operates inside a larger system where trust lives outside the repository:

```
Developer / AI Agent
    ↓
  Purlin (writes specs, code, tests, proof files)
    ↓
  Git Repository (untrusted — mutable, accessible to agents)
    ↓
  CI/CD Pipeline (pulls from git, applies external policy)
    ↓
  External Compliance Infrastructure:
    - Policy vault (compliance rules — NOT in repo, NOT editable by agents)
    - Identity provider (Okta/SAML — MFA-backed signatures for human approvals)
    - QMS / compliance ledger (immutable audit trail, external to git)
    - Test lock registry (approved test hashes stored outside repo)
```

### Key principles

1. **Policy lives outside the repo.** Compliance rules, required verification levels, and approval requirements are enforced by CI/CD infrastructure — not by config files the agent can edit.

2. **Signatures come from an identity provider.** Human approvals (manual proofs, invariant syncs, test lock sign-offs) go through MFA-backed authentication, not `git config user.email` or GPG keys.

3. **Audit trail lives outside git.** Verification receipts are ingested into an immutable external ledger. Git history is a convenient view, not the compliance record.

4. **Test lock hashes live outside the repo.** Approved test hashes are stored in the external QMS or compliance ledger, not in `.test-lock.json` inside the repo where the agent can modify them.

---

## Integration Points (not extensions)

These are not Purlin features to enable via config flags. They are interfaces where Purlin's output connects to external compliance infrastructure. Your compliance team builds and owns these integrations.

### Requirements Traceability

Purlin's `RULE-N` lines in specs and `PROOF-N` entries in proof files create a machine-readable traceability matrix. A compliance tool can parse `specs/**/*.md` for rules and `specs/**/*.proofs-*.json` for proof results to generate the traceability documentation your QMS requires.

### Verification Evidence

The `vhash` in verification receipts is a deterministic hash of rule IDs + proof statuses. Your CI pipeline can use the `vhash` to verify that the developer's local state matches the CI environment, before the CI runner executes its own clean-room verification to submit to the QMS. The local `vhash` is evidence that the developer ran the tests — the CI `--audit` run is the evidence that the tests pass in a trusted environment.

### Human Approval Workflow

When `@manual` stamps are required, the compliant flow is:
1. Purlin flags the rule as needing manual verification (`sync_status` shows "MANUAL PROOF NEEDED")
2. The human performs the verification
3. Instead of `purlin:verify --manual` (which only writes a markdown stamp), the human approves through the QMS — which authenticates via MFA, records intent, and issues a signed approval token
4. The QMS (or CI pipeline) injects the cryptographically signed approval token into the spec file or a locked artifact, which Purlin reads to satisfy the local `sync_status` check — stopping the `→ MANUAL PROOF NEEDED` directives
5. CI verifies the QMS approval token before accepting the manual proof

### External Invariant Validation

Invariant `> Pinned:` SHAs track which version of an external standard is in use. Your CI pipeline can compare the pinned SHA against the authoritative source and fail the build if the invariant is stale — enforced by CI policy, not by Purlin config.

---

## The Bottom Line

Purlin's rule-proof model is a good foundation for regulated development — it produces the structured artifacts that compliance systems need. But the trust boundary must be outside the repository. Purlin is the compiler. Your QMS, identity provider, and CI/CD infrastructure are the compliance system.

Consult your compliance team about integrating Purlin's output into your existing quality management infrastructure.
