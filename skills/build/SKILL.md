---
name: build
description: Load a spec's rules, write the code and the tagged tests, commit the changeset
---

# purlin:build

Load every rule a feature is bound by, write the code and the tests that prove it, run them,
and commit the result with a body that says which rule each change serves.

**Paths.** Every `references/` and `scripts/` path below is inside the plugin and is reached
through `${CLAUDE_PLUGIN_ROOT}`. A project carries none of them.

## Choosing what to build

```bash
purlin:build [<name>]
```

With no name, call `sync_status` and read the state:

| What the state says | What you do |
|---------------------|-------------|
| One spec has rules with no passing test | Build it. Say which and why, then start |
| Several do | List them with their unproved rule counts and ask which |
| None do | Say the specs are all proved and point at `purlin:spec` for the next requirement |
| There are no specs at all | Point at `purlin:spec`, or `purlin:spec-from-code` when the tree already has code |

## Loading the rules

Read the feature spec, then follow `> Requires:` through every anchor it names and every
anchor those name in turn. Add any anchor with `> Global: true`, which applies without being
named. The rules you must satisfy are the union of all of them, and a rule from an anchor
binds exactly as tightly as one written in the feature.

Read `> Scope:` and `> Stack:` before you write a line. `> Scope:` is where the code belongs;
a record carries the git tree hash of those files, so code that lands outside them is code no
record accounts for.

## Writing the code and the tests

Write the smallest change that satisfies the rules, then one test per proof. Every test
carries a marker naming the feature, the proof and the rule, which is what lets Purlin tell
which rule a passing test actually proves:

```python
@pytest.mark.proof("login", "PROOF-1", "RULE-1")
def test_valid_credentials_return_200():
    assert authenticate("user@test.com", "secret") == 200
```

The marker for every other framework is in `references/formats/proofs_format.md`. A test with
no marker proves nothing as far as Purlin is concerned, however good it is.

A test asserts the observable the proof names, against the real behaviour. A test that asserts
a stub returns what the stub was told to return is worse than no test: it reports a rule as
proved when nothing was proved. When a rule genuinely cannot be proved as written, do not
weaken the test. Stop and fix the rule.

## When a rule is wrong

A rule that contradicts another, or that no test could settle as written, is a spec problem
and not a build problem. Call `purlin:spec <name>`, fix the rule text in place, keep the id,
and come back. Changing rule text stales any signature bound to that rule, which is correct: a
person has to look again.

A rule tagged `[origin: pm]`, `[origin: design]` or `[origin: qa]` is not yours to change.
Leave it, build against it as written, and put the proposal in the pull request.

## Running them

```bash
purlin:test <name>
```

Never run the test framework directly. `purlin:test` runs the tagged tests, writes the proof
files into `.purlin/runtime/proofs/`, and prints the state of each rule. Iterate until every
rule the feature owns has a passing test. A proof tagged `@env` for an operating system that
is not this one is skipped and listed as `needs <os>`; that is expected locally and CI proves
it on the matching runner.

Never write a proof file, a record or a signature by hand. Tests write proof files,
`purlin:audit` writes records, `purlin:sign` writes signatures.

## Committing

One commit per build, with the `feat(<name>):` prefix and the changeset body described in
`references/commit_conventions.md`. The body has three sections: **Changeset**, a
`RULE-N → file:line` line for every rule the build addressed; **Decisions**, the judgment calls
you made between real alternatives; and **Review**, the places an engineer should look hardest.
Omit Decisions when every rule had one obvious implementation, and omit Review when nothing
needs a second pair of eyes. Changeset is never omitted. `references/commit_conventions.md`
carries the exact rendering; follow it rather than inventing one.

Commit the code and the tests together. `.purlin/runtime/` is ignored by git, so proof files
never enter a commit.

## When you are done

Print the state table from `sync_status` for the feature, then name the next step:

- Every rule has a passing test: `→ Next: purlin:audit`, which breaks the code on purpose,
  measures the test strength and writes the record.
- Some rules still have no test: name them and say what is missing.
- A rule has a `@manual` proof: say that its evidence is a signature with a one-line note, and
  point at `purlin:sign`.
- A proof needs another operating system: say which, and point at `purlin:audit --remote`.
