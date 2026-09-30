# Commit conventions

Every commit Purlin makes, or asks you to make, uses one of these. There is no other prefix.

## Prefixes

| Prefix | When | Who commits it |
|--------|------|----------------|
| `spec(<name>):` | Creating or editing a spec or an anchor's local rules; from `purlin:spec-from-code`, with the comments it adds above the project's existing tests | `purlin:spec` |
| `feat(<name>):` | Implementing a feature, with the changeset in the body | `purlin:build` |
| `fix(<name>):` | Fixing a bug | `purlin:build` |
| `test(<name>):` | Writing or changing tests without changing behaviour | `purlin:build` |
| `purlin: specs, tests and settings for <feature>[, <feature>...]` | The specs of the features a run covered, the test files carrying their markers, and `.purlin/config.json`: the work the run's results describe | `purlin:test --commit`, `purlin:audit --commit` |
| `purlin: evidence at <commit7>` | The evidence a run wrote, under `.purlin/evidence/` with `.purlin/tests.md`, or the evidence package | `purlin:test --commit`, `purlin:audit --commit`, `purlin:export --commit`, `purlin:test --release` for the package of the release, and a remote runner |
| `sign(<version>): <signer email>` | One sign-off over a release's evidence package, signed | `purlin:sign` |
| `anchor(<name>): create` | A new local anchor | `purlin:anchor create` |
| `anchor(<name>): sync (<sha>)` | Advancing a pin to that commit | `purlin:anchor sync` |
| `chore(update): migrate to <VERSION> (<ids>)` | Migrating a project to the installed plugin | `purlin:init --update` |
| `chore(init): set up Purlin at the gate <gate>` | The files setup wrote, once a person agrees or `--yes` is passed | `purlin:init` |
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
sign(1.2.0): quinn.qa@labconnect.example
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

A run that selected nothing to run still commits, in the first commit, every spec, every test
file carrying a marker and `.purlin/config.json` that changed. Its subject names each feature
whose spec or marked tests it holds, and reads `purlin: specs, tests and settings` where it
holds only the settings.

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
else. No run writes a sign-off, so an evidence commit never carries one.

## The release commit

`purlin:test --release` makes the two commits of a run, then one more carrying the evidence
package alone, `.purlin/evidence/package/<version>.json`:

```
purlin: evidence at <commit7>
```

`<commit7>` is the commit the package describes. The commit is signed where `commit.gpgsign` is
on, and plain otherwise.

## The sign-off commit

```
sign(<version>): <signer email>
```

Signed, always: one commit per sign-off, adding
`.purlin/evidence/package/<version>.signoffs/<signer-slug>.json` and nothing else. `purlin:sign`
makes it with your git identity, and the sign-off counts when the commit's signature verifies and
the file carries the committed package's fingerprint (`references/hard_gates.md`, "When a
sign-off counts").

## The tags

```
passed/<version>         at the gate passed, by purlin:test --release
signed/<version>         at the gate signed, by the first sign-off
```

`passed/<version>` is annotated and unsigned (`git tag -a`), on the release commit.
`signed/<version>` is signed (`git tag -s`, with the key you sign commits with), on the first
sign-off's commit; a later sign-off adds its file after it, and the tag does not move. What each
means is defined once, in `references/hard_gates.md`, which also says where the version is read
from. The message names the commit the package describes and the gate:

```
Released at the gate <gate>.

Commit: <full sha>
Gate: <gate>
```

No tag is written over one that is already there. Nothing is pushed: the run prints
`Tagged <tag> at <sha7>.`, then `Nothing left to do. Push the tag to release it: git push origin <tag>`.
Where the project has a remote runner, pushing `signed/<version>` starts the run that reruns the
tests on a clean machine; `passed/<version>` starts none.

## The build commit body

`purlin:build` puts the changeset in the body: what it built, where, and why. This is the
developer's review artefact and it stays in git history.

```
feat(auth_login): implement RULE-1, RULE-2, RULE-3

Changeset:
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
| A release is made | The evidence package, alone, by `purlin:test --release` | The package describes one commit |
| A sign-off walk ended with yes | The sign-off, signed, in one commit | One person's signature over one package |
| A pin advanced | The anchor spec | Staleness is read from the committed pin |

Do not commit after each failed test iteration, do not batch two skills' output into one commit,
and do not commit without reading `sync_status` first.

## General rules

Keep the scope inside the parentheses equal to the feature name, one feature per commit where
you can, and commit at logical milestones rather than at the end of a session. A project that
requires trailers of its own adds them on top of these prefixes; nothing here replaces them.
