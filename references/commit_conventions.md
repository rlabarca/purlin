# Commit Conventions

## Prefixes

| Prefix | When |
|--------|------|
| `spec(<name>):` | Creating or editing a spec |
| `feat(<name>):` | Implementing a feature |
| `fix(<name>):` | Fixing a bug |
| `test(<name>):` | Writing or updating tests |
| `verify:` | Issuing verification receipts |
| `anchor(<name>):` | Syncing an anchor from upstream |
| `chore:` | Project setup, config changes, cleanup |
| `docs:` | Documentation updates |

## Examples

```
spec(auth_login): add rules for SSO and MFA flows
feat(auth_login): implement SSO redirect and callback
test(auth_login): 3/3 rules proved
fix(auth_login): handle expired tokens in callback
verify: [Complete:all] features=5 vhash=a1b2c3d4
anchor(design_tokens): sync from upstream (abc1234)
chore: initialize purlin project
```

## Build Commit Body

When `purlin:build` commits, the commit message body contains the changeset summary — a structured record of what the agent built and why. This is the engineer's review artifact and lives in git history permanently.

Format:

```
feat(<name>): implement RULE-1, RULE-2, RULE-3

RULE-1 → src/auth.py:34         Added sanitize_input() before query
RULE-2 → src/auth.py:71         Sliding window rate limiter (60/min)
         tests/test_auth.py:12  2 proofs covering RULE-1 and RULE-2

Decisions:
  • Middleware over inline validation — reusable across routes
  • 60 req/min hardcoded — spec says "rate limit" with no threshold

Review:
  → src/auth.py:45  Regex for SQL injection — security-sensitive
```

The first line uses the standard `feat(<name>):` prefix. The body has three sections:

| Section | Purpose | When to omit |
|---------|---------|-------------|
| Changeset | Rule→file:line mapping for every rule addressed | Never — always present |
| Decisions | Judgment calls the agent made between alternatives | Omit if all rules had unambiguous implementations |
| Review | Risk areas the engineer should scrutinize | Omit if straightforward implementation |

## Verification Receipt Commit

The verify skill uses a specific format:

```
verify: [Complete:all] features=N vhash=<combined-hash>
```

Where `combined-hash` = `sha256(sorted individual vhashes joined by comma)[:8]`.

## Manual Stamp Commit

```
verify(<feature>): manual stamp PROOF-N
```

## When to commit

Skills commit at natural boundaries — after reaching a stable state, not after every file change.

| Boundary | What to commit | Why |
|----------|---------------|-----|
| Spec approved | The spec .md file | Exit criteria enforce this — agent verifies git status |
| Build stable | Code + tests + proofs + changeset summary in commit body | Exit criteria enforce this — agent verifies git status |
| Proof files written | .proofs-*.json files | sync_status reads committed proofs |
| Verification done | Receipt files + verify commit message | Already mandatory |
| Anchor synced | Updated anchor file | Staleness checks use committed Pinned SHA |

Do NOT commit:
- After each failed test iteration (pollutes history)
- Multiple skills' output in one batch commit (loses traceability)
- Without checking sync_status first (may miss uncommitted proof files)

## General Rules

- Commit at logical milestones, not at session end.
- Keep scope in the parentheses matching the feature/spec name.
- One feature per commit when possible.
