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
| `purlin: evidence at <commit7>` | The evidence a run wrote, under `.purlin/evidence/` | `purlin:test --commit`, `purlin:audit --commit`, and a project's own run on another system |
| `sign(<version>): <signer email>` | One sign-off over a version's evidence package, signed; the first of a version carries the package too | `purlin:sign` |
| `anchor(<name>): create` | A new local anchor | `purlin:anchor create` |
| `anchor(<name>): sync (<sha>)` | Advancing a pin to that commit | `purlin:anchor sync` |
| `chore(update): migrate to <VERSION> (<ids>)` | Migrating a project to the installed plugin | `purlin:init --update` |
| `chore(init): set up Purlin` | The files setup wrote, once a person agrees or `--yes` is passed | `purlin:init` |
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

Both commits are yours, made under your own git identity. Neither is pushed for you.
`references/formats/evidence_format.md`, "The two commits", gives the lines the run prints.

**The first commit** holds whichever of these changed:

- each spec of the features the run covered;
- the test files carrying their markers;
- `.purlin/config.json`.

With nothing to commit there is no first commit.

A run that selected nothing to run still makes the first commit. It holds every spec, every test
file carrying a marker and `.purlin/config.json` that changed. Its subject names each feature
whose spec or marked tests it holds. Where it holds only the settings, the subject is
`purlin: specs, tests and settings`.

**The second commit** holds the evidence and nothing else:

- the files under `.purlin/evidence/local/`;
- any evidence file the run removed because its feature has no spec.

`<commit7>` is the first seven characters of the first commit, or of HEAD when there was nothing
to commit. It names the commit of the code the results describe, not the evidence commit itself.
Each section of the evidence records that same commit. A sign-off counts a result only when
nothing but Purlin's own records under `.purlin/` changed after it and the `tests` setting is as
it was.

Never fold the evidence into a `feat(...)` commit. The evidence must be able to say which commit
the tests ran against.

A run on another system with `--commit` makes the second commit alone:

- It holds that run's files under `.purlin/evidence/ci/` and any evidence file the run removed,
  and nothing else.
- Its subject is the same, and `<commit7>` names HEAD when the run started.
- It is made under the git identity its checkout sets.
- The run itself pushes nothing.

No run writes a sign-off, so an evidence commit never carries one.

## The sign-off commit

```
sign(<version>): <signer email>
```

Signed, always: one commit per sign-off. The first sign-off of a version carries the evidence
package, `.purlin/evidence/package/<version>.json`, and the sign-off,
`.purlin/evidence/package/<version>.signoffs/<signer-slug>.json`; a later one adds its own file
and nothing else. `purlin:sign` makes it with your git identity, and the sign-off counts when the
commit's signature verifies and the file carries the committed package's fingerprint
(`references/evidence_and_signoff.md`, "When a sign-off counts").

## The tag

```
signed/<version>         by the first sign-off of a version
```

`signed/<version>` is signed (`git tag -s`, with the key you sign commits with), on the first
sign-off's commit; a later sign-off adds its file after it, and the tag does not move. What it
means is defined once, in `references/evidence_and_signoff.md`, which also says where the version
is read from. The message names the version and the commit the package describes:

```
Signed <version>.

Commit: <full sha>
```

No tag is written over one that is already there. Nothing is pushed: the sign-off prints
`Tagged signed/<version> at <sha7>.`, then
`Push the branch and the tag: git push origin <branch> signed/<version>`.

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
| A run you want to keep, with `--commit` | The work the results describe, then the evidence, alone | The evidence names the commit the tests ran against |
| The work is ready for a sign-off | The same two commits, by `purlin:test --all --commit` | A sign-off counts only results taken on this version of the code |
| A sign-off walk ended with yes | The sign-off, signed, in one commit, with the package where it is the version's first | One person's signature over one package |
| A pin advanced | The anchor spec | Staleness is read from the committed pin |

Do not commit after each failed test iteration, do not batch two skills' output into one commit,
and do not commit without reading `sync_status` first.

## General rules

Keep the scope inside the parentheses equal to the feature name, one feature per commit where
you can, and commit at logical milestones rather than at the end of a session. A project that
requires trailers of its own adds them on top of these prefixes; nothing here replaces them.
