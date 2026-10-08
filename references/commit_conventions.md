# Commit conventions

Every commit Purlin makes, or asks you to make, uses one of these. There is no other prefix.

## Prefixes

| Prefix | When | Who commits it |
|--------|------|----------------|
| `spec(<name>):` | Creating or editing a spec or an anchor's local rules; from `purlin:spec-from-code`, with the comments it adds above the project's existing tests | `purlin:spec` |
| `feat(<name>):` | Implementing a feature, with the changeset in the body | `purlin:build` |
| `fix(<name>):` | Fixing a bug | `purlin:build` |
| `test(<name>):` | Writing or changing tests without changing behaviour | `purlin:build` |
| `purlin: specs, tests and settings for <feature>[, <feature>...]`, or `for <n> features` over 5 | The specs of the features a run covered, the test files carrying their markers, and `.purlin/config.json`: the work the run's results describe. With no feature named, the settings file alone, which a first run commits once the test command is confirmed | `purlin:test --commit`, `purlin:audit --commit`, and the first test run |
| `purlin: evidence at <commit7>` | The evidence a run wrote, under `.purlin/evidence/` | `purlin:test --commit`, `purlin:audit --commit`, and a project's own run on another system |
| `sign(<version>): <signer email>` | One sign-off over a version's evidence package, signed; the first of a version carries the package too | `purlin:sign` |
| `anchor(<name>): create` | A new local anchor | `purlin:anchor create` |
| `anchor(<name>): sync (<sha>)` | Advancing a pin to that commit | You, after `purlin:anchor sync`, which changes the copy and commits nothing |
| `chore(update): migrate to <VERSION> (<ids>)` | Migrating a project to the installed plugin | `purlin:init --update` |
| `chore(update): restore <file>[, <file>...]` | The files setup writes, restored to a project that lacked them | `purlin:init --update` |
| `chore(init): set up Purlin` | The files setup wrote, once a person agrees or `--yes` is passed | `purlin:init` |
| `chore:` | Project setup, config changes, renames, cleanup | Anyone |
| `docs:` | Documentation | Anyone |

## Examples

```
spec(auth_login): rules for single sign-on and the lockout window
purlin: specs, tests and settings for auth_login, checkout
purlin: evidence at a1b2c3d
sign(1.2.0): quinn.qa@labconnect.example
anchor(security_baseline): sync (abc1234)
chore(update): migrate to 0.10.0 (markers, plugins)
```

## The two commits of a run

`purlin:test` and `purlin:audit` write the evidence and commit none of it. With `--commit` they
make two commits in one step, the work and then the results that describe it. Both are yours,
made under your own git identity, and neither is pushed for you.
`references/formats/evidence_format.md`, "The two commits", gives the lines the run prints.

**The first commit** holds whichever of these changed: each spec of the features the run
covered, the test files carrying their markers, and `.purlin/config.json`.

- With nothing to commit there is no first commit.
- Over 5 features the subject counts them, `purlin: specs, tests and settings for 54 features`,
  and the body lists them, one per line.
- A run that selected nothing to run still makes it. It holds every spec, every test file
  carrying a marker and `.purlin/config.json` that changed, and its subject names each feature
  whose spec or marked tests it holds. Where it holds only the settings, the subject is
  `purlin: specs, tests and settings`.
- A first run commits the settings file alone, once the test command is confirmed.

**The second commit** holds the evidence and nothing else:

- the files under `.purlin/evidence/local/`;
- each file under `.purlin/evidence/ci/` in which the run carried a section forward;
- any evidence file the run removed because its feature has no spec.

`<commit7>` is the first seven characters of the first commit, or of HEAD when there was nothing
to commit. It names the commit of the code the results describe, not the evidence commit itself.
Each section of the evidence records that same commit.

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

`sign(<version>): <signer email>` is signed, always: one commit per sign-off, made by
`purlin:sign` with your git identity. The first sign-off of a version carries the evidence
package, the outputs kept with it and the sign-off; a later one adds its own file and nothing
else. The first also writes the signed tag `signed/<version>` on its commit.
`references/evidence_and_signoff.md` says when a sign-off counts ("When a sign-off counts") and
gives the tag's message and meaning ("What `signed/<version>` means").

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

## General rules

- Keep the scope inside the parentheses equal to the feature name, one feature per commit where
  you can.
- Commit at a milestone: the spec once it is agreed, the build once it is stable, a pin once it
  advanced. Do not commit after each failed test iteration.
- Do not batch two skills' output into one commit, and do not commit without reading
  `sync_status` first.
- A project that requires trailers of its own adds them on top of these prefixes; nothing here
  replaces them.
