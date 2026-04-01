# Purlin for Regulated Environments

Purlin is designed for general-purpose spec-driven development. For teams operating under regulatory frameworks (FDA 21 CFR Part 11, HIPAA, SOC2, PCI-DSS, etc.), the following extensions can be added without changing the core architecture.

All extensions share a pattern: **they add strictness via configuration flags.** The core rule-proof-receipt pipeline stays the same. The base system works for 95% of teams. Regulated teams enable the flags they need.

---

## Signed Manual Proofs

**The problem:** Manual proof stamps (`@manual(email, date, sha)`) use `git config user.email`, which is spoofable. A developer or AI agent can set any email and forge a QA verification stamp. Under FDA 21 CFR Part 11, electronic signatures require non-repudiation — you must prove that the person who signed off is actually who they claim to be.

**The extension:** A `require_signed_manual_proofs` configuration flag.

When enabled:
- `purlin:verify --manual` requires `git commit -S` (GPG or SSH signed commit) for the stamp commit
- The signature is cryptographically bound to the committer's key — unforgeable without the private key
- Alternatively, integrate with an identity provider (Okta, SSO) to generate a cryptographically signed token embedded in the stamp

**What changes for the team:**
- Every person who stamps manual proofs must have GPG/SSH keys configured
- CI can verify signatures via `git log --show-signature`
- The stamp in the spec looks the same to humans — the signature lives in the git commit, not the markdown

---

## Repository Tree-Hash Verification

**The problem:** `> Scope:` is documentation, not enforcement. It lists the files a feature covers, but it doesn't track transitive dependencies. If a shared utility (`src/utils/crypto.js`) changes and `login` depends on it but didn't list it in `> Scope:`, login's verification receipt remains valid. The tests would catch the breakage — but only if someone runs them.

In medical or safety-critical software, every code change must mathematically invalidate all dependent features, forcing re-verification.

**The extension:** A `vhash_mode: tree` configuration flag.

When enabled:
- The vhash includes `git rev-parse HEAD` (the full repository commit SHA) in addition to rule IDs and proof statuses
- Any commit to the repo — anywhere, any file — invalidates ALL receipts
- `purlin:verify --audit` must re-run the entire test suite before deployment
- This is expensive (full suite on every deploy) but mathematically correct

**What changes for the team:**
- No receipt caching between deploys. Every deploy runs every test.
- CI pipelines need sufficient compute for full test suites
- The trade-off is explicit: total assurance at the cost of CI time

**When to use:** Medical devices (FDA Class II/III), avionics (DO-178C), safety-critical embedded systems, any environment where "the tests would catch it" isn't sufficient — you need proof that the tests actually ran against this exact code state.

---

## Test Lock Mechanism

**The problem:** The AI writes the code AND writes the test. It can write `assert True` and get a passing proof. The verification receipt will be perfect. CODEOWNERS review catches most cases, but a fatigued reviewer might approve a tautological test for a critical security invariant.

**The extension:** A test lock for invariant-linked tests.

How it works:
1. Tests that prove invariant rules (`i_security_*`, `i_legal_*`, `i_compliance_*`) get a separate `test_hash` — a SHA of the test file content — generated when a human reviewer approves the test
2. The test hash is stored alongside the spec (e.g., in a `.test-lock.json` file)
3. The CI `--audit` gate verifies the test file being executed matches the approved `test_hash` before counting its results
4. If the test file changed since approval (the AI modified it), the proof is rejected until a human re-approves

**What changes for the team:**
- A human must review and approve test files for security/compliance invariants
- The AI can write the test, but it can't be used for verification until a human signs off
- Test changes to locked files require re-approval — visible in PR reviews

**When to use:** Any environment where the test quality for specific invariants must be human-verified. Pairs well with GitHub CODEOWNERS or similar PR review requirements.

---

## Signed Invariant Sync

**The problem:** Invariant bypass locks use `git config user.email` to record who requested the sync. This is spoofable. A compromised AI agent could sync a modified invariant from a tampered source, and the audit trail would show a forged identity.

**The extension:** A `require_signed_invariant_sync` configuration flag.

When enabled:
- `purlin:invariant sync` requires `git commit -S` (GPG/SSH signed commit) for the sync commit
- The bypass lock's `requested_by` field is verified against the GPG/SSH key
- The invariant update has cryptographic non-repudiation — you know exactly who authorized the change

**What changes for the team:**
- Invariant syncs require GPG/SSH keys
- The audit trail for invariant changes is cryptographically verifiable
- Pairs with signed manual proofs — same key infrastructure, same `git commit -S` requirement

---

## Immutable Audit Log

**The problem:** Git history can be rewritten with `git push --force`. A malicious insider could alter or remove verification receipts from the git log. Force-push protection on branches helps, but isn't sufficient for regulatory audit trails.

**The extension:** Append-only external audit log.

On each `purlin:verify`:
1. The receipt (vhash, feature list, proof summary) is appended to an external, immutable store
2. Options: signed S3 object, append-only database, compliance SaaS (e.g., Drata, Vanta), or even a simple append-only file on a write-once share
3. The CI `--audit` gate checks both the git history AND the external log
4. If the git receipt was altered or removed but the external log shows the original, the discrepancy is flagged

**What changes for the team:**
- Infrastructure setup: an external store with append-only semantics
- Configuration: point Purlin at the audit endpoint
- Receipts exist in two places — git (convenient, human-readable) and external (immutable, tamper-proof)

**When to use:** Regulated environments requiring audit trails that survive git history rewrites. SOC2 Type II, HIPAA, FDA 21 CFR Part 11, FedRAMP, or any framework requiring immutable evidence of verification.

---

## Combining Extensions

Extensions are independent flags. Enable any combination:

| Scenario | Extensions |
|----------|------------|
| **Standard development** | None (default) |
| **Security-conscious team** | Signed manual proofs + CODEOWNERS |
| **Healthcare / medical device** | All five extensions |
| **Financial services (SOC2)** | Signed manual proofs + immutable audit log |
| **Government / FedRAMP** | Tree-hash verification + immutable audit log + signed invariant sync |

The core pipeline is unchanged. Rules, proofs, receipts, `sync_status` — all work the same. The extensions add cryptographic assurance, mandatory re-verification, and tamper-proof audit trails on top.

---

## Implementation Status

These extensions are documented designs, not yet implemented. They require no changes to the core Purlin architecture — each is a configuration flag that adds a check to an existing step (verify, sync, or audit).

If your team needs any of these extensions, [open an issue](https://github.com/rlabarca/purlin/issues) describing your regulatory requirements and we'll prioritize accordingly.
