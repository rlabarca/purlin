# Commit Conventions

## Prefixes

| Prefix | When |
|--------|------|
| `spec(<name>):` | Creating or editing a spec |
| `feat(<name>):` | Implementing a feature |
| `fix(<name>):` | Fixing a bug |
| `test(<name>):` | Writing or updating tests |
| `verify:` | Issuing verification receipts |
| `invariant(<name>):` | Syncing an invariant from upstream |
| `chore:` | Project setup, config changes, cleanup |
| `docs:` | Documentation updates |

## Examples

```
spec(auth_login): add rules for SSO and MFA flows
feat(auth_login): implement SSO redirect and callback
test(auth_login): 3/3 rules proved
fix(auth_login): handle expired tokens in callback
verify: [Complete:all] features=5 vhash=a1b2c3d4
invariant(i_design_tokens): sync from upstream (abc1234)
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

## General Rules

- Commit at logical milestones, not at session end.
- Keep scope in the parentheses matching the feature/spec name.
- One feature per commit when possible.
