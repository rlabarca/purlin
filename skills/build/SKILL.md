---
name: build
description: Write the code and the marked tests for a spec's rules, fix a failing rule, strengthen a weak test, and commit the changeset
---

# purlin:build

Load every rule a feature is bound by, write the code and the tests that prove it, run them,
and commit the result with a body that says which rule each change serves.

**Paths.** Every `references/` and `scripts/` path below is inside the plugin and is reached
through `${CLAUDE_PLUGIN_ROOT}`. A project carries none of them.

A line marked **Stop and ask** is a question for the person: print it, end your turn, and act
only on their answer. Never answer it yourself.

## Choosing what to build

```bash
purlin:build [<name>]
```

With no name, read the state from the status.

Get the status from the tool `mcp__plugin_purlin_purlin__sync_status`, passing `project_root`:
the top folder of the git checkout you are working in. Where the session lists it as a
deferred tool, load it with ToolSearch first. Where the session does not have it, run the
script, which prints the same status:

```bash
sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_status.py" --project-root .
```

Never read `.purlin/report-data.js` or `purlin-report.html` as the status: they hold what the
last command saw.

| What the state says | What you do |
|---------------------|-------------|
| One spec has rules with no passing test | Build it. Say which and why, then start |
| Several do | List them with their unproved rule counts and ask which |
| None do | Say the specs are all proved and point at `purlin:spec` for the next requirement |
| There are no specs at all | Point at `purlin:spec`, or `purlin:spec-from-code` when the tree already has code |

## Loading the rules

Read the feature spec. Every anchor's rules hold across the whole project, so code you write
keeps them too; their tests are the anchors' own and `purlin:test` runs them after any change.

Read `> Scope:` and `> Stack:` before you write a line. `> Scope:` is where the code belongs;
the evidence carries a fingerprint of those files, so code that lands outside them is code no
evidence accounts for, and a change to it selects nothing on the next `purlin:test`.

## Writing the code and the tests

Build from the proofs that exist. Write the smallest change that satisfies the rules, then, for
each proof with no test marked for it:

1. **Look first for a test that already shows it.** Search the project's existing tests for one
   that does what the proof says: the same input, the same observable, the same expected
   value. Where one does, offer to add the marker above it and write nothing new. A test that
   shows part of it is not that test. Before you add a marker above any test, read the test
   against the proof as it is worded now and check it still shows it.
2. **Otherwise write an ordinary test** in the project's own framework, in the folder and the
   style its other tests use, with the marker above it.

The marker is one comment, in the language's own comment syntax, on the line above the test:

```python
# purlin: login PROOF-1
def test_valid_credentials_return_200():
    assert authenticate("user@test.com", "secret") == 200
```

It names the feature and the proof; the spec already says which rule the proof serves. Where a
rule has no proof, it names the rule: `purlin: login RULE-2`. A
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
and come back. A number written twice in a spec, or a test comment whose proof's wording
changed, moves as `purlin:spec`'s "Renumbering" says, after the person answers `Do it? [y/N]`.

## A test comment to correct

A test comment names a proof. When the proof's wording changed after the test was last changed,
the status and every run name the comment under `Left to do` as a test comment to correct, and
the tests read `not met` until the test changes. List them:

```bash
sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/mcp/purlin/wording.py" --project-root .
```

Add `--file <path>` for each test file to narrow it. It prints one line per comment, then the
count, `<n> test comments to correct.` or `No test comment to correct.`:

```
tests/test_login.py:1 names login PROOF-4, whose wording changed after the test was last changed in 3c9d2e1: it read "A" and now reads "B". Run purlin:build login to make the test show it; the line clears once the test changes.
```

For each, read the test against the proof as it reads now. Where the test does not show it, fix
the test: the starting situation, the action and each value the proof names are what the test
sets up, does and asserts. Where it already does, change the test so it states it, in its name
or an assertion. The line clears once the test's own lines change; never reword the proof to
fit the test. A line ending `Its old wording is now PROOF-6: move the comment there.` is a
comment to move, as `purlin:spec`'s "Renumbering" says.

## Repairing a comment that is nearly a marker

```bash
sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/mcp/purlin/markers.py" --near-misses --project-root .
```

It prints one JSON list of the comments that are nearly markers, each with its `file`, `line`,
`text`, `fix` and `why`. Show each `fix` beside its `why`, ask, and make the edits accepted.

## Running them

```bash
purlin:test <name>
```

Never run the test framework directly. `purlin:test` runs the project's own test command, ties
each result to the marker above its test, writes the evidence and prints the state of each rule;
where no test command is set it prints a suggestion and asks before it writes one, so write no
entry yourself and never edit `.purlin/config.json` by hand. It names every marker it could not tie to
exactly one test, by file and line; fix each before going on. Iterate until every rule the
feature owns has a passing test. A proof tagged `@env` for another operating system is not run
here: the run counts such proofs in one line per system; `skills/test/SKILL.md`, Step 5 says what
to do then. A
proof tagged `@slow` gets its test and its comment like any other, with nothing added to the
test; `purlin:test` leaves it out and names it, and `purlin:test --all` runs it
(`references/purlin_commands.md`). Never
write evidence or a sign-off by hand. `purlin:test` and `purlin:audit` write the evidence,
and `purlin:sign` the evidence package and a sign-off.

## Committing

One commit per build, with the `feat(<name>):` prefix and the changeset body described in
`references/commit_conventions.md`. The body has three sections, which open with `Changeset:`,
`Decisions:` and `Review:`: a `RULE-N → file:line` line for every rule the build addressed; the
judgment calls you made between real alternatives; and the places a developer should look hardest.
Omit Decisions when every rule had one obvious implementation, and omit Review when nothing
needs a second pair of eyes. Changeset is never omitted. `references/commit_conventions.md`
carries the exact rendering; follow it rather than inventing one.

Before you commit, compare the files you created, changed or deleted for the feature with its
`> Scope:`: add each new file no entry covers, remove each entry whose file you deleted, and
rewrite the line in the same commit as the code. Commit the code and the tests together.

## When you are done

`purlin:test` ended on the summary and `Left to do`. Name the next step from them:

- Every rule passes and the work is committed: the hand-off is
  `→ Run: purlin:test --all --commit`, after which a person may sign with `purlin:sign`
- A test comment to correct: fix the test as above, `→ Run: purlin:build <feature>`
- Some rules still have no test: name them and what is missing, `→ Run: purlin:build <feature>`
- A rule to strengthen: add the case the audit's finding names, `→ Run: purlin:build <feature>`
- A proof needs another operating system: name it, then do as `skills/test/SKILL.md`, Step 5 says
