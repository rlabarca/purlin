# Commit conventions

Every commit Purlin makes, or asks you to make, uses one of these. There is no other prefix.

## Prefixes

| Prefix | When | Who commits it |
|--------|------|----------------|
| `spec(<name>):` | Creating or editing a spec or an anchor's local rules | `purlin:spec` |
| `feat(<name>):` | Implementing a feature, with the changeset in the body | `purlin:build` |
| `fix(<name>):` | Fixing a bug | `purlin:build` |
| `test(<name>):` | Writing or changing tests without changing behaviour | `purlin:build` |
| `purlin: tests at <commit7>` | The test results of one run: `.purlin/tests/` and `.purlin/tests.md` | `purlin:test` |
| `purlin: record for <commit7>` | The record of one CI run, and the briefs that run wrote | CI, and nothing else |
| `sign(<name>): RULE-N ...` | Signatures, signed | `purlin:sign` |
| `sign(batch): <feature> RULE-N, ...` | One signed commit covering more than one feature | `purlin:sign --batch` |
| `hold(<name>): RULE-N ...` | Holds on rules whose test does not prove the proof, signed | `purlin:sign --hold` |
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
purlin: tests at a1b2c3d
purlin: record for a1b2c3d
sign(auth_login): RULE-3 RULE-4 RULE-7
sign(batch): auth_login RULE-9, checkout RULE-2
anchor(design_tokens): sync (abc1234)
chore(update): migrate to 0.10.0 (legacy-proof-file, legacy-marker)
chore: rename login to authentication
```

## The test results commit

`purlin:test` commits what it saw as:

```
purlin: tests at <commit7>
```

`<commit7>` is the first seven characters of the commit the tests ran against, not of the
results commit itself. The commit is yours, made under your own git identity, and it carries
`.purlin/tests/<feature>.json` and `.purlin/tests.md` and nothing else. It is never pushed for
you. A run that saw the same thing about the same code commits nothing.

## The record commit

**An audit makes the record commit, and so does CI.** `purlin:audit` runs the tagged tests,
then the breaks and the free checks at `strong` and above, and commits one record per feature
under your own identity. The CI job does the same under the build identity. Both use:

```
purlin: record for <commit7>
```

`<commit7>` is the first seven characters of the commit the tests ran against, not of the record
commit itself.

A record commit carries the record file and the briefs that run wrote, both under the folder
that names its source: `.purlin/records/local/` and `.purlin/briefs/local/` for yours,
`.purlin/records/ci/` and `.purlin/briefs/ci/` for CI's. It carries nothing else: never fold a
record into a `feat(...)` commit, because the record must be able to say which commit the tests
ran against. No run writes a signature file, so a record commit never carries one, and it
carries no test results either: those go in their own commit.

`purlin:audit` prints `Record committed.` or `Record unchanged.` and never pushes. CI's record
commit lands on the protected branch or on a run branch, and nowhere else. A pull request run
posts the comment and commits nothing: a record on a branch nobody merges from is evidence of a
branch that will not exist. At `passed` no run writes a record at all.

## The signature commit

```
sign(<feature>): RULE-N RULE-M ...
sign(batch): <feature> RULE-N, <feature> RULE-M ...
hold(<feature>): RULE-N ...
```

Signed, always. `purlin:sign` makes the commit with your git identity, and the gate counts the
signature only when the commit signature verifies, the author's email is on `signers` as of that
commit, that author is not the author of the commit that last touched the test, and, under the
`signed` gate, the commit is on the protected branch. One commit may carry a batch; the rule ids
are all listed in the subject, in order. A hold is committed the same way and carries the
missing case in the file, not in the subject.

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
| An audit finished | The record, alone | It names the commit the tests ran against |
| A walk of the review list ended | The signatures, signed, in one commit | The batch is one attestation |
| A pin advanced | The anchor spec and any designs it pulled in | Staleness is read from the committed pin |

Do not commit after each failed test iteration, do not batch two skills' output into one commit,
and do not commit without reading `sync_status` first.

## General rules

Keep the scope inside the parentheses equal to the feature name, one feature per commit where
you can, and commit at logical milestones rather than at the end of a session. A project that
requires trailers of its own adds them on top of these prefixes; nothing here replaces them.
