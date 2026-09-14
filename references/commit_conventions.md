# Commit conventions

Every commit Purlin makes, or asks you to make, uses one of these. There is no other prefix.

## Prefixes

| Prefix | When | Who commits it |
|--------|------|----------------|
| `spec(<name>):` | Creating or editing a spec or an anchor's local rules | `purlin:spec` |
| `feat(<name>):` | Implementing a feature, with the changeset in the body | `purlin:build` |
| `fix(<name>):` | Fixing a bug | `purlin:build` |
| `test(<name>):` | Writing or changing tests without changing behaviour | `purlin:build` |
| `purlin: record for <commit7>` | The record of one verify run, and on CI the approvals and briefs that run wrote | `purlin:verify`, or CI |
| `approve(<name>): RULE-N ...` | Approvals, signed | `purlin:approve` |
| `anchor(<name>): create` | A new local anchor | `purlin:anchor create` |
| `anchor(<name>): sync (<sha>)` | Advancing a pin to that commit | `purlin:anchor sync` |
| `anchor(<name>): propose` | The branch that becomes the pull request upstream | `purlin:anchor propose` |
| `chore(update): migrate to <VERSION> (<ids>)` | Migrating a project to the installed plugin | `purlin:init --update` |
| `chore:` | Project setup, config changes, renames, cleanup | Anyone |
| `docs:` | Documentation | Anyone |

## Examples

```
spec(auth_login): rules for single sign-on and the lockout window
feat(auth_login): implement the redirect and the callback
test(auth_login): a negative case for an expired token
fix(auth_login): reject a token whose issuer moved
purlin: record for a1b2c3d
approve(auth_login): RULE-3 RULE-4 RULE-7
anchor(design_tokens): sync (abc1234)
chore(update): migrate to 0.10.0 (legacy-proof-file, legacy-marker)
chore: rename login to authentication
```

## The record commit

One verify run writes one record and commits it as:

```
purlin: record for <commit7>
```

`<commit7>` is the first seven characters of the commit the tests ran against, not of the record
commit itself. The message is the same whether a developer or CI wrote it: what separates them
is who committed, which is what the label is read from. Under the `tested` gate you commit your
own records; under `recorded` and `approved` only the commit CI made through the git host's API
counts, and yours is a preflight.

A record commit carries the record file and, on a CI run, the approvals CI wrote for low-risk
rules and the briefs it wrote for the review list. It carries nothing else: never fold a record
into a `feat(...)` commit, because the record must be able to say which commit the tests ran
against.

## The approval commit

```
approve(<feature>): RULE-N RULE-M ...
```

Signed, always. `purlin:approve` makes it with your git identity, and the gate counts it only
when the signature verifies, the author's email is on the approver list as of that commit, and
that author is not the author of the commit that last touched the test. One commit may carry a
batch; the rule ids are all listed in the subject, in order.

## The build commit body

`purlin:build` puts the changeset in the body: what it built, where, and why. This is the
engineer's review artefact and it stays in git history.

```
feat(auth_login): implement RULE-1, RULE-2, RULE-3

RULE-1 → src/auth.py:34         Sanitize the input before the query
RULE-2 → src/auth.py:71         Sliding window, 60 requests per minute
         tests/test_auth.py:12  2 proofs, covering RULE-1 and RULE-2

Decisions:
  - Middleware rather than inline validation: reusable across routes
  - 60 per minute is hardcoded; the rule says "rate limit" with no number

Review:
  → src/auth.py:45  The pattern match on the query string is security-sensitive
```

| Section | What it holds | When to leave it out |
|---------|---------------|----------------------|
| Changeset | Rule to file and line, for every rule the commit addresses | Never |
| Decisions | Choices the agent made between alternatives | When every rule had one obvious implementation |
| Review | What the engineer should look at hardest | When nothing is risky |

## When to commit

| Boundary | What goes in | Why |
|----------|--------------|-----|
| The spec is agreed | The spec file | It is the contract the build reads |
| The build is stable | Code, tests, and the changeset in the body | Half a feature is not a milestone |
| A verify run finished | The record, alone | It names the commit the tests ran against |
| A review ended | The approvals, signed, in one commit | The batch is one attestation |
| A pin advanced | The anchor spec and any designs it pulled in | Staleness is read from the committed pin |

Do not commit after each failed test iteration, do not batch two skills' output into one commit,
and do not commit without reading `sync_status` first.

## General rules

Keep the scope inside the parentheses equal to the feature name, one feature per commit where
you can, and commit at logical milestones rather than at the end of a session. A project that
requires trailers of its own adds them on top of these prefixes; nothing here replaces them.
