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

## The test of an AI proof

A proof tagged `@ai(...)` is an AI proof: it says what an AI does with a prompt or a skill.
Its test is an ordinary marked test. It starts the helper, at the path the run sets in
`PURLIN_AI`, and asserts on the folder the helper prints. `references/purlin_commands.md`,
"The helper", is the one home of the helper's commands, and `references/rule_examples.md`,
"AI proofs", has a worked test for each.

- Write the test, and the sample it runs on, under the project's own tests folder: the input
  file, and for a skill or a plugin the sample project.
- Start `run` for a prompt, a skill or a plugin, or `record` where the project makes the
  output its own way. One test makes one output.
- Assert what the proof names on the output: the exact value, line or absence, in `reply.md`
  or a file under `files/`.
- A graded proof's test then starts `grade` and asserts it exits 0.
- The test passes or skips when `PURLIN_AI` is not set: a suite that cannot leave one test out
  starts it with the others, and a developer running the suite by hand gets a skip, not a
  call to a model.
- Name no model in the test. The proof's tag names it, and the run hands it to the helper.

`purlin:test` leaves the test out, as it does any slow proof's. `purlin:test --all` starts it
on each model the tag names, several times on each. Run `purlin:test --all` once the test is
written, and say first that it reaches a real model and takes minutes. `skills/test/SKILL.md`, Step 4 says how each line of that run reads. A model that was not
reached is no failure: change nothing for it.

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
count, `<n> test comments to correct.` or `No test comment to correct.` A line names the proof
and its rule, the words that changed, and the test's file, line and last commit:

```
login PROOF-4 (RULE-2): test comment to correct. "sixteen" became "seventeen" after tests/test_login.py:1 last changed (3c9d2e1). Run purlin:build login.
```

The line shows the words that changed, not the proof: read the proof in the spec. For each,
read the test against the proof as it reads now. Where the test does not show it, fix
the test: the starting situation, the action and each value the proof names are what the test
sets up, does and asserts. Where it already does, change the test so it states it, in its name
or an assertion. The line clears once the test's own lines change; never reword the proof to
fit the test. A line ending `Move the comment to PROOF-6, which holds the old wording.` is a
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

## Strengthening a weak rule

A rule the audit found `weak` is left to do as a rule to strengthen. The status carries each
finding as a reason of the rule's `strong` cell.

A line `<file>::<test>: ...` is a spot test's finding: fix the test as the finding says, then
run `purlin:audit <feature> RULE-N --settle`. The settle runs the spot tests over the rule's
tests again and asks no model, so a finding they no longer make is gone at once, and the
settle prints `<file>::<test>: the spot tests now find nothing.`

A line `PROOF-N: the test still passes when <file>:<line> reads "<line>"` is a planted bug that
survived. Auditing again does not clear it: while its test is as it was, `purlin:audit` plants
the same bug again (`references/review_criteria.md`, "The planted bug"). For each:

1. Read the proof, its test, the finding and the case line under it,
   `PROOF-N: the AI says this breaks: <case>`.
2. Write the assertion the proof names, for the proof's own case: the exact value, line or
   absence the proof gives. Write it in the test's own body: a change to a helper, a fixture
   or another test alone is not a change to the test, and the settle is refused for it. Never
   change the code under test for a finding. Never narrow or reword a rule or a proof to make
   a finding go away. Never change a test that already asserts what its proof names: where
   you have read the test against the proof, line by line, and it already asserts the exact
   value, line or absence the proof gives for the proof's own case, leave it as it is and
   settle that proof with `--sound PROOF-N`, as step 4 says. Say which line of the test
   asserts which words of the proof before you do.
3. Where the proof names too little to write that assertion, stop for that proof: say so,
   propose a sharper proof sentence, and send the person to `purlin:spec`.
4. Run `purlin:test <feature>`, then `purlin:audit <feature> RULE-N --settle`. For each proof
   whose test you left alone under step 2, and for no other, add `--sound PROOF-N`:
   `purlin:audit <feature> RULE-N --settle --sound PROOF-N`. A settle is refused for a proof
   whose test is as it was when the bug got past it; `--sound` is the recorded judgment that
   the test was sound already, and the evidence then says the test was not changed. Never
   pass it for a test you did not read against its proof, and never to get past a refusal.
   The settle starts the test of a slow proof of the rule it names, so a rule with a proof
   tagged `@slow` needs no `purlin:test --all` first.
5. Report what the settle printed for each proof, and the word the rule then reads:
   - The test now catches the bug: the finding was right, and the bug reads `caught`.
   - The bug did not break what the proof says, and a new bug was planted: the finding was
     wrong. Where the new bug survives too, two bugs left the proof's check passing, and the
     proof gets no further bug until its test or code changes.
   - The same line ending at `did not break what the proof says.`: no new bug could be planted,
     and the rule's block says why.
   - The test did not run with the bug in place: the bug reads `not run`.
   - `PROOF-N: its test is as it was when the bug got past it. Strengthen it with purlin:build,
     then settle.`: nothing was planted, and the bug still reads `survived`. Go back to
     step 2 for that proof.
   - `PROOF-N was settled with its test unchanged: it was judged to assert what the proof
     names.`: the settle went on under `--sound`, and the evidence records it.

The rule then reads what the verdict gives: `weak` where a spot test fires or a bug still
survives, else `strong` where any of its proofs has a caught bug, else `spot-checked`. A rule
can read `strong` through another proof.

A rule that still reads `weak` has a finding left: start again at step 1 with it.

An AI proof is strengthened the same way. Its planted bug is a wrong output, so the finding
names a file of the output, as in `PROOF-4: the test still passes when reply.md:12 reads
"Refund approved."`: write the assertion the proof names, then settle. The settle starts the
AI proof's test on each model again, so say first that it reaches a real model and takes
minutes. For a graded proof the finding says the grader accepted a wrong output. Where the
proof names an exact value the test does not assert, assert it; otherwise stop for that proof
as step 3 says.

`skills/audit/SKILL.md`, Step 2 says how each line the settle prints reads.
`references/review_criteria.md`, "Settling a finding", is the one home of what it does.

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
- A rule to strengthen: do as "Strengthening a weak rule" says, `→ Run: purlin:build <feature>`
- A proof needs another operating system: name it, then do as `skills/test/SKILL.md`, Step 5 says
