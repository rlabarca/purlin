# Commit conventions

Every commit Purlin makes, or asks you to make, uses one of these. There is no other prefix.

## Prefixes

| Prefix | When | Who commits it |
|--------|------|----------------|
| `spec(<name>):` | Creating or editing a spec or an anchor's local rules | `purlin:spec` |
| `feat(<name>):` | Implementing a feature, with the changeset in the body | `purlin:build` |
| `fix(<name>):` | Fixing a bug | `purlin:build` |
| `test(<name>):` | Writing or changing tests without changing behaviour | `purlin:build` |
| `purlin: specs, tests and settings for <feature>[, <feature>...]` | The specs of the features a run covered, the test files carrying their markers, and `.purlin/config.json`: the work the run's results describe | `purlin:test --commit`, `purlin:audit --commit` |
| `purlin: evidence at <commit7>` | The evidence a run wrote, under `.purlin/evidence/` with `.purlin/tests.md`, or the evidence package | `purlin:test --commit`, `purlin:audit --commit`, `purlin:export --commit`, `purlin:sign` at the gate `signed` for the package the tag carries, and a remote runner |
| `sign(<name>): RULE-N ...` | Signatures, signed | `purlin:sign` |
| `sign(batch): <feature> RULE-N, ...` | Signatures, signed, in one commit covering more than one feature | `purlin:sign`, whenever the rules it signs belong to more than one feature |
| `anchor(<name>): create` | A new local anchor | `purlin:anchor create` |
| `anchor(<name>): sync (<sha>)` | Advancing a pin to that commit | `purlin:anchor sync` |
| `chore(update): migrate to <VERSION> (<ids>)` | Migrating a project to the installed plugin | `purlin:init --update` |
| `chore:` | Project setup, config changes, renames, cleanup | Anyone |
| `docs:` | Documentation | Anyone |

## Examples

```
spec(auth_login): rules for single sign-on and the lockout window
feat(auth_login): implement the redirect and the callback
test(auth_login): a negative case for an expired token
fix(auth_login): reject a token whose issuer moved
purlin: specs, tests and settings for auth_login, checkout
purlin: evidence at a1b2c3d
sign(auth_login): RULE-3 RULE-4 RULE-7
sign(batch): auth_login RULE-9, checkout RULE-2
anchor(security_baseline): sync (abc1234)
chore(update): migrate to 0.10.0 (markers, plugins)
chore: rename login to authentication
```

## The two commits of a run

`purlin:test` and `purlin:audit` write the evidence and commit nothing. With `--commit` they
make two commits in one step, the work and then the results that describe it:

```
purlin: specs, tests and settings for <feature>, <feature>
purlin: evidence at <commit7>
```

The first carries each spec of the features the run covered, the test files carrying their
markers and `.purlin/config.json`, where any of them changed. The run prints
`Committed <sha7>, the work these results describe:` and then each path on a line of its own,
indented two spaces. With nothing to commit there is no first commit.

The second carries the files under `.purlin/evidence/local/`, `.purlin/tests.md` and any
evidence file the run removed because its feature has no spec, and nothing else. `<commit7>`
is the first seven characters of the first commit, or of HEAD when there was nothing to commit:
the commit the results describe, not the evidence commit itself. Never fold it into a
`feat(...)` commit, because the evidence must be able to say which commit the tests ran
against. The run prints `Evidence committed.`, or `Evidence unchanged.` when nothing new was
seen. Both commits are yours, made under your own git identity, and neither is pushed for you.

A remote runner on a run branch commits its own section of `.purlin/evidence/ci/` with the same
subject, through the git host's API under the build identity, and always does, because its
evidence exists nowhere else. A tag run writes nothing at all: it runs the tests and nothing
else. No run writes a signature file, so an evidence commit never carries one.

## The signature commit

```
sign(<feature>): RULE-N RULE-M ...
sign(batch): <feature> RULE-N, <feature> RULE-M ...
```

Signed, always. `purlin:sign` makes the commit with your git identity, and at every gate the
signature counts when the commit carries a signature and what it was made over is unchanged,
on whatever branch carries it (`references/hard_gates.md`, "When a signature counts"). One
commit may carry a batch; the rule ids are all listed in the subject, in order.

## The tag

```
signed/<version>
signed/<name>            with --release <name>
```

Signed, never lightweight (`git tag -s`, with the key you sign commits with), and written by
`purlin:sign` at the gate `signed` when nothing is left to do and every result came from
committed work, and never below `signed`; what that means is defined once, in
`references/hard_gates.md`, which also says where the version is read from. The message names
the commit and the gate:

```
Nothing left to do at the gate signed.

Commit: <full sha>
Gate: signed
```

No tag is written while anything is left to do, and none is written over a tag that is
already there. Nothing is pushed: `purlin:sign` prints `Tagged signed/<version> at <sha7>.`,
then `Nothing left to do. Push the tag to release it: git push origin signed/<version>`. Where
the project has a remote runner, pushing it starts the run that reruns the tests on a clean
machine.

## The build commit body

`purlin:build` puts the changeset in the body: what it built, where, and why. This is the
developer's review artefact and it stays in git history.

```
feat(auth_login): implement RULE-1, RULE-2, RULE-3

RULE-1 → src/auth.py:34         Sanitize the input before the query
RULE-2 → src/auth.py:71         Sliding window, 60 requests per minute
RULE-3 → src/auth.py:102        Lock the account after five failed attempts
         tests/test_auth.py:12  3 proofs, covering RULE-1, RULE-2 and RULE-3

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
| Review | What the developer should look at hardest | When nothing needs a second pass |

## When to commit

| Boundary | What goes in | Why |
|----------|--------------|-----|
| The spec is agreed | The spec file | It is the contract the build reads |
| The build is stable | Code, tests, and the changeset in the body | Half a feature is not a milestone |
| A run you want to keep, with `--commit` | The work the results describe, then the evidence and the table, alone | The evidence names the commit the tests ran against |
| A signing walk ended | The signatures, signed, in one commit | The batch is one attestation |
| A pin advanced | The anchor spec | Staleness is read from the committed pin |

Do not commit after each failed test iteration, do not batch two skills' output into one commit,
and do not commit without reading `sync_status` first.

## General rules

Keep the scope inside the parentheses equal to the feature name, one feature per commit where
you can, and commit at logical milestones rather than at the end of a session. A project that
requires trailers of its own adds them on top of these prefixes; nothing here replaces them.
