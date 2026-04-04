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
| Spec approved | The spec .md file | Drift detection compares committed specs |
| Build/test stable | Code + test files + proof .json files | Proof files are project records |
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
