---
name: build
description: Load a spec's rules, write the code and the marked tests, commit the changeset
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
the evidence carries a fingerprint of those files, so code that lands outside them is code no
evidence accounts for, and a change to it selects nothing on the next `purlin:test`.

## Writing the code and the tests

Build from the proofs that exist. Write the smallest change that satisfies the rules, then, for
each proof with no test marked for it:

1. **Look first for a test that already shows it.** Search the project's existing tests for one
   that does what the proof says: the same input, the same observable, the same expected
   value. Where one does, offer to add the marker above it and write nothing new. A test that
   shows part of it is not that test.
2. **Otherwise write an ordinary test** in the project's own framework, in the folder and the
   style its other tests use, with the marker above it.

The marker is one comment, in the language's own comment syntax, on the line above the test:

```python
# purlin: login PROOF-1
def test_valid_credentials_return_200():
    assert authenticate("user@test.com", "secret") == 200
```

It names the feature and the proof; the spec already says which rule the proof serves. Where a
rule has no proof, which the gate `passed` allows, it names the rule: `purlin: login RULE-2`. A
test may carry several markers, one line each, and decorators may sit between marker and test.
`references/formats/marker_format.md` is the contract. A test Purlin wrote and a test a
developer wrote differ in nothing but who typed them; a test with no marker is not evidence.

A test must sit where a suite of the `tests` setting in `.purlin/config.json` reaches it, under
one of its `files` globs; a marker in a file no suite names is never read. `purlin:test` writes
that setting at the first run, and `references/supported_frameworks.md` shows each framework's.

A test asserts the observable the proof names, against the real behaviour. A test that asserts
a stub returns what the stub was told to return is worse than no test: it reports a rule as
proved when nothing was proved. When a rule genuinely cannot be proved as written, do not
weaken the test. Stop and fix the rule.

## When a rule is wrong

A rule that contradicts another, or that no test could settle as written, is a spec problem
and not a build problem. Call `purlin:spec <name>`, fix the rule text in place, keep the id,
and come back. Any signature on the rule then ends, which is correct: a person has to look again.

## Repairing a comment that is nearly a marker

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/mcp/purlin/markers.py" --near-misses --project-root .
```

It prints one JSON list of the comments that are nearly markers, each with its `file`, `line`,
`text`, `fix` and `why`. Show each `fix` beside its `why`, ask, and make the edits accepted.

## Running them

```bash
purlin:test <name>
```

Never run the test framework directly. `purlin:test` runs the project's own test command, ties
each result to the marker above its test, writes the evidence and prints the state of each
rule; where no test command is set it suggests one and writes it once the person confirms, so
write no entry yourself. It names every marker it could not tie to exactly one test, by file and
line; fix each before going on. Iterate until every rule the feature owns has a passing test.
A proof tagged `@env` for another operating system is not run here, and the run says it
`needs <os>`; `purlin:test --remote` runs it on a runner of that system.

Never write evidence or a signature by hand. `purlin:test` and `purlin:audit` write the
evidence, `purlin:sign` writes signatures and the tag.

## Committing

One commit per build, with the `feat(<name>):` prefix and the changeset body described in
`references/commit_conventions.md`. The body has three sections: **Changeset**, a
`RULE-N → file:line` line for every rule the build addressed; **Decisions**, the judgment calls
you made between real alternatives; and **Review**, the places a developer should look hardest.
Omit Decisions when every rule had one obvious implementation, and omit Review when nothing
needs a second pair of eyes. Changeset is never omitted. `references/commit_conventions.md`
carries the exact rendering; follow it rather than inventing one.

Before you commit, compare the files you created, changed or deleted for the feature with its
`> Scope:`: add each new file no entry covers, remove each entry whose file you deleted, and
rewrite the line in the same commit as the code. Commit the code and the tests together.

## When you are done

`purlin:test` ended on the summary and `Left to do`. Name the next step from them:

- Every rule has a passing test, gate `passed`: `→ Run: git push`
- Every rule has a passing test, gate `strong` or `signed`: `→ Next: purlin:audit`, which has a
  model read each rule, proof and test, and breaks the code where mutation testing is on.
- Some rules still have no test: name them and what is missing, `→ Run: purlin:build <feature>`
- A `@manual` proof: a person checks it and signs, `→ Run: purlin:sign <feature> RULE-<n>`
- A proof needs another operating system: name it, `→ Run: purlin:test --remote`
