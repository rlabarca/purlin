# Lane `prose`, decision 120

Wording only, in ten files. No spec, no code and no test changed. No `> Format-Version:` moved:
every format edit rewords or moves sentences, and no field or structure changed.

## What changed

1. **Duplication.**
   - The two commits of a committing run were described in full in three places. Now:
     `references/formats/evidence_format.md`, "The two commits", holds what the run prints;
     `references/commit_conventions.md`, "The two commits of a run", holds what each commit
     carries and how its subject reads; `skills/test/SKILL.md`, Step 3, says two commits are
     made and points at both. Each of the two references points at the other.
   - Facts that stood only in the format moved to the conventions with the shapes: the run on
     another system makes one commit, `<commit7>` there names HEAD when the run started, it
     holds nothing else, and the run pushes nothing.
   - `skills/audit/SKILL.md`, Step 1, lists the three step names and points at
     `references/review_criteria.md`. The six spot tests, the planted bug's mechanics and the
     `claude -p` call are no longer restated; each is in the criteria.
   - `skills/status/SKILL.md` and the two facts in `agents/purlin.md` stay, as the item says.
     `skills/status/SKILL.md` is unchanged.
2. **Nine dense paragraphs** rewritten as short sentences and lists. Two neighbours were split
   in the same pass, marked 2b and 7b below: the last paragraph of Step 4, and the paragraph
   after the `proofs` table that the reading names at `:143`.
3. **`references/review_criteria.md`, the release sentence**, now an instruction.

## Calls made, for the owner to check

- **Item 3 sits inside "Heuristic spot tests"**, the section this lane was told to leave as the
  owner's official text. The item names the line, so that one list item was changed and nothing
  else in the section.
- **`evidence_format.md`, an untied proof.** The old sentence said its entry reads "the same
  way". The new one says what the code writes (`scripts/run/evidence.py`): `missing`, or
  `not run` where the proof is tagged `@env` for another operating system.
- **`evidence_format.md`, `<sha7>`.** The format now defines it only for the printed line
  `Committed <sha7>, ...`. The subject `purlin: evidence at <commit7>` and its HEAD case are in
  the conventions.
- **`references/review_criteria.md` is sent to the model**, and its sha256 is the `criteria`
  field of each audit entry. Two paragraphs of it changed, so the next audit records a new
  `criteria`. An entry still answers its rule, since only the three hashes are compared.

## Tests

- The five files of this lane (`dev/test_skill_test.py`, `dev/test_skill_spec.py`,
  `dev/test_skill_audit.py`, `dev/test_skill_status.py`, `dev/test_purlin_agent.py`): 10 passed
  before, 10 passed after. No test asserted a sentence that changed, so no test file changed.
- The 22 test files under `dev/` that read a skill, the agent definition or a reference: 278
  passed and 4 skipped before, the same after.
- `dev/test_purlin_docs.py` and `dev/test_plain_checks.py`: 24 passed after.
- No rule or proof is new or reworded.

## Edits needed in files this lane does not own

None. `docs/running-and-evidence.md:143` quotes `Evidence unchanged.`, which still prints.

Integration should expect the features whose `> Scope:` reaches these ten files to read
`out of date` until the next committed run.

## Item 1, before and after

**`references/formats/evidence_format.md`, "The two commits": the printed lines stay, the shapes go to the conventions**

Before:

````
## The two commits

`purlin:test` and `purlin:audit` write the files and do not commit them. With `--commit` they make two commits in one step, under the
person's own identity. The first carries the work the results describe: the
spec of each feature run, the test files carrying their markers and
`.purlin/config.json`, where any of them changed:

```
purlin: specs, tests and settings for <feature>[, <feature>...]
```

The run prints `Committed <sha7>, the work these results describe:` and then
each file that commit changed, one per line, indented two spaces. Where none
changed it makes no such commit and prints nothing.

A run that selected nothing to run still makes the first commit, of every
spec, every test file carrying a marker and `.purlin/config.json` that
changed. Its subject names each feature whose spec or marked tests it holds;
where it holds only the settings, the subject is:

```
purlin: specs, tests and settings
```

The second carries the files under `local/` and any file the run removed:

```
purlin: evidence at <sha7>
```

where `<sha7>` is the first seven characters of the first commit, or of
`HEAD` when there was nothing to commit first. The run prints `Evidence
committed.`, or `Evidence unchanged.` when no file changed and there was
nothing to commit. Neither command ever pushes.

A `--ci` run writes its `ci/` files and does not commit them. With
`--commit` it makes one commit, of the files under `ci/` and any evidence
file the run removed and nothing else, under the git identity set in that
checkout, with the same subject, where `<sha7>` names `HEAD` when the run
started. It prints `Evidence committed.` or `Evidence unchanged.` the same
way, and it never pushes.
````

After:

````
## The two commits

`purlin:test` and `purlin:audit` write the files and do not commit them. With
`--commit` a run makes two commits, the work and then the evidence.
`references/commit_conventions.md`, "The two commits of a run", says what each
commit holds and how its subject reads. This section gives what the run
prints:

| When | The run prints |
|---|---|
| It made the first commit | `Committed <sha7>, the work these results describe:`, then each file that commit changed, one per line, indented two spaces |
| No spec, test file or setting changed, so it made no first commit | nothing |
| It made the evidence commit | `Evidence committed.` |
| No evidence file changed, so there was nothing to commit | `Evidence unchanged.` |

`<sha7>` is the first seven characters of the first commit.

A `--ci` run writes its `ci/` files and does not commit them. With `--commit`
it makes the evidence commit alone, and prints `Evidence committed.` or
`Evidence unchanged.` the same way.

No run ever pushes.
````

**`references/commit_conventions.md`, "The two commits of a run", from its third paragraph to the end of the section (this is also the dense paragraph of item 2, the second commit)**

Before:

````
The first carries each spec of the features the run covered, the test files carrying their
markers and `.purlin/config.json`, where any of them changed. The run prints
`Committed <sha7>, the work these results describe:` and then each path on a line of its own,
indented two spaces. With nothing to commit there is no first commit.

A run that selected nothing to run still commits, in the first commit, every spec, every test
file carrying a marker and `.purlin/config.json` that changed. Its subject names each feature
whose spec or marked tests it holds, and reads `purlin: specs, tests and settings` where it
holds only the settings.

The second carries the files under `.purlin/evidence/local/` and any
evidence file the run removed because its feature has no spec, and nothing else. `<commit7>`
is the first seven characters of the first commit, or of HEAD when there was nothing to commit:
the commit of the code the results describe, not the evidence commit itself. Each section records
that same commit, and a sign-off counts a result only when nothing but Purlin's own records under
`.purlin/` changed after it. Never fold it into a
`feat(...)` commit, because the evidence must be able to say which commit the tests ran
against. The run prints `Evidence committed.`, or `Evidence unchanged.` when nothing new was
seen. Both commits are yours, made under your own git identity, and neither is pushed for you.

A run on another system commits its own files under `.purlin/evidence/ci/` with the same subject,
under the git identity its checkout sets. No run writes a sign-off, so an evidence commit never carries one.

````

After:

````
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
nothing but Purlin's own records under `.purlin/` changed after it.

Never fold the evidence into a `feat(...)` commit. The evidence must be able to say which commit
the tests ran against.

A run on another system with `--commit` makes the second commit alone:

- It holds that run's files under `.purlin/evidence/ci/` and any evidence file the run removed,
  and nothing else.
- Its subject is the same, and `<commit7>` names HEAD when the run started.
- It is made under the git identity its checkout sets.
- The run itself pushes nothing.

No run writes a sign-off, so an evidence commit never carries one.

````

**`skills/audit/SKILL.md`, Step 1: the three step names and the pointer**

Before:

````
would select. It runs the tests, then reads each rule whose tests pass, that has a proof with a
test, and whose text, proofs, tests or covered code changed since its last audit:

1. **The heuristic spot tests**, with no model: a test that checks nothing, a check that cannot
   fail, a swallowed error, a test that checks the code against itself, a test that replaces what
   it is testing, and a test that never checks the result the proof expects.
2. **One planted bug per proof** whose test or covered code changed since its last one. The model
   names the smallest change to the code that would break the proof; the change is made in a copy
   of the project, never in the project itself; the proof's own tests run there; the copy is
   removed. A test that still passes is weak, with the change as the evidence. No bug is planted
   for an anchor's proof or a `@manual` proof.
3. **The model's reading**, one `claude -p` call per rule, which explains what the first two found
   and decides nothing.

A rule reads `weak` when a spot test fires on one of its tests or a planted bug survived, else
`strong`. `references/review_criteria.md` is the one home of each check, the research behind it
and what the model is sent.
````

After:

````
would select. It runs the tests, then reads each rule whose tests pass, that has a proof with a
test, and whose text, proofs, tests or covered code changed since its last audit. It takes three
steps for each rule:

1. The heuristic spot tests.
2. One planted bug per proof.
3. The model's reading.

A rule reads `weak` when a spot test fires on one of its tests or a planted bug survived, else
`strong`. `references/review_criteria.md` is the one home of each step: its checks, the research
behind them and what the model is sent.
````

The third place, `skills/test/SKILL.md` Step 3, is the first paragraph of item 2 below.

## Item 2, the nine paragraphs, before and after

**1. `skills/test/SKILL.md`, Step 3**

Before:

````
The run writes this operating system's section of `.purlin/evidence/local/<feature>.json`: the
commit of the code it describes, the time, who ran it and on which machine, the fingerprint of the
spec, code and tests it saw, each rule's word, each proof's result and test. It prints `Evidence
written to .purlin/evidence/local/<feature>.json.`, or the folder and a count for several
features, and commits nothing. With `--commit` it makes two commits under your own git identity.
The first, `purlin: specs, tests and settings for <feature>`, holds the specs of the features run,
the test files carrying their markers and `.purlin/config.json`, and the run prints `Committed
<sha7>, the work these results describe:` and each path. The second, `purlin: evidence at <sha7>`,
holds the evidence and names the first; the run prints `Evidence committed.`, or `Evidence
unchanged.` when nothing new was seen. It never pushes. `references/formats/evidence_format.md` is
the contract.

The tests read `met` only on committed evidence, and a sign-off counts only results taken on this
version of the code. So before a person signs, run `purlin:test --all --commit`: every feature,
on the code as committed, and the results committed after it.
````

After:

````
The run writes this operating system's section of `.purlin/evidence/local/<feature>.json`. The
section holds:

- the commit of the code it describes, and the time;
- who ran it, and on which machine;
- the fingerprint of the spec, code and tests it saw;
- each rule's word, and each proof's result and test.

It prints `Evidence written to .purlin/evidence/local/<feature>.json.`, or the folder and a count
for several features. It commits nothing.

With `--commit` it makes two commits under your own git identity: the work, then the evidence
that names it. It never pushes. `references/commit_conventions.md`, "The two commits of a run",
says what each commit holds. `references/formats/evidence_format.md` is the contract for the file
and for the lines the run prints.

The tests read `met` only on committed evidence. A sign-off counts only results taken on this
version of the code. So before a person signs, run `purlin:test --all --commit`. It runs every
feature on the code as committed, then commits the results.
````

**2. `skills/test/SKILL.md`, Step 4, first paragraph**

Before:

````
The run prints `Markers: <n> tied to a test, <k> not tied.`, then each test comment to correct,
then `Ran <suite> on <n> features.`, then one line per rule that fails or has no test,
`<feature> RULE-<n> fails: <file>::<test>. Run purlin:build <feature>.`, `<feature> RULE-<n> has
no test. Run purlin:build <feature>.` or `<feature> <RULE-N> has no test for <PROOF-N>[,
<PROOF-M>...]. Run purlin:build <feature>.`, then the status `purlin:status` builds. For a
failed test the run also prints the last 60 lines of the suite's own output.
````

After:

````
The run prints, in this order:

1. `Markers: <n> tied to a test, <k> not tied.`
2. Each test comment to correct.
3. `Ran <suite> on <n> features.`
4. One line per rule that fails or has no test. It is one of:
   - `<feature> RULE-<n> fails: <file>::<test>. Run purlin:build <feature>.`
   - `<feature> RULE-<n> has no test. Run purlin:build <feature>.`
   - `<feature> <RULE-N> has no test for <PROOF-N>[, <PROOF-M>...]. Run purlin:build <feature>.`
5. The status `purlin:status` builds.

For a failed test the run also prints the last 60 lines of the suite's own output.
````

**2b. `skills/test/SKILL.md`, Step 4, last paragraph (the same step; split while there)**

Before:

````
A test comment to correct reads `<file>:<line> names <feature> <PROOF-N>, whose wording changed
after the test was last changed in <sha7>: ...`, and clears once the test itself changes: run
`purlin:build <feature>`. Loud failures come first: `Evidence is missing: <what>.` means a suite
left no readable report, or a marker has no pass or fail: its test was skipped, the report lacks
it, or no test follows it. A marker naming nothing a spec has reads `<file>:<line> names
<feature> <ID>, which no spec has.`
````

After:

````
A test comment to correct reads `<file>:<line> names <feature> <PROOF-N>, whose wording changed
after the test was last changed in <sha7>: ...`. It clears once the test itself changes: run
`purlin:build <feature>`.

Loud failures come first. `Evidence is missing: <what>.` means one of two things:

- a suite left no readable report;
- a marker has no pass or fail: its test was skipped, the report lacks it, or no test follows it.

A marker naming nothing a spec has reads `<file>:<line> names <feature> <ID>, which no spec has.`
````

**3. `skills/spec/SKILL.md`, "Ids"**

Before:

````
A new rule takes one more than the highest of `> Highest-Rule:` and every rule number in either
copy of the spec, the working copy and `origin/main`'s, read with `git show origin/main:<spec>`.
Write that number into `> Highest-Rule:`, adding the line after the spec's other `>` lines where
it is missing, so a deleted number is never used again. A new proof takes one more than the
highest of `> Highest-Proof:` and every proof number in either copy; write that number into
`> Highest-Proof:`, adding the line after `> Highest-Rule:` where it is missing.
````

After:

````
A new rule takes one more than the highest of these:

- `> Highest-Rule:`;
- every rule number in the working copy of the spec;
- every rule number in `origin/main`'s copy, read with `git show origin/main:<spec>`.

Write that number into `> Highest-Rule:`, so a deleted number is never used again. Where the line
is missing, add it after the spec's other `>` lines.

A new proof takes one more than the highest of `> Highest-Proof:` and every proof number in
either copy. Write that number into `> Highest-Proof:`. Where the line is missing, add it after
`> Highest-Rule:`.
````

**4. `references/formats/spec_format.md`, taking the next number**

Before:

````
Renumbering by hand would silently repoint every test comment that already
names the old id.
A new rule takes one more than the highest of `> Highest-Rule:` and every rule number the spec holds, and `> Highest-Rule:` is raised to it, so a number is never used again.
When two branches take the same number, the number already on the default branch keeps it, and the rule or proof from the branch not yet merged moves to the next free number. A moved rule's audit is read again; `purlin:spec` renumbers it and its test comments when you say yes.
Unnumbered lines under `## Rules` are reported. A rule id written twice is
````

After:

````
Renumbering by hand would silently repoint every test comment that already
names the old id.

A new rule takes one more than the highest of `> Highest-Rule:` and every
rule number the spec holds. `> Highest-Rule:` is raised to that number, so a
number is never used again.

Two branches can take the same number. The rule or proof already on the
default branch keeps it. The one from the branch not yet merged moves to the
next free number, and a moved rule's audit is read again. `purlin:spec`
renumbers it and its test comments when you say yes.

Unnumbered lines under `## Rules` are reported. A rule id written twice is
````

**5. `references/formats/anchor_format.md`, the file at the path**

Before:

````
The file at the path is a spec in this format that holds at least one rule. `purlin:anchor add` refuses any other source, a file on disk, a description in words or a file with no rule, and writes nothing. A copy whose `> Source:` names no repository reads `error` in `purlin:drift` and in `purlin:anchor sync --check`. A local anchor carries no `> Source:` and is never checked.
````

After:

````
The file at the path is a spec in this format that holds at least one rule.
`purlin:anchor add` refuses any other source and writes nothing:

- a file on disk;
- a description in words;
- a file with no rule.

A copy whose `> Source:` names no repository reads `error` in `purlin:drift`
and in `purlin:anchor sync --check`. A local anchor carries no `> Source:` and
is never checked.
````

6. `references/commit_conventions.md`, the second commit: shown under item 1 above.

**7. `references/formats/evidence_format.md`, the rule words**

Before:

````
Each `rules` value:

| Word | What it means |
|---|---|
| `failed` | a tied test of a proof that could run here failed, or a test marked with the rule's id failed |
| `no test` | else, a proof of the rule that is not `@manual`, tagged `@env` or not, has no test tied to it; or no proof names the rule and no test is marked with its id |
| `not run` | else, a tied test did not run, a proof of the rule is tagged `@env` for another operating system, so this machine could not answer, or the run left out the test of a proof tagged `@slow` |
| `passed` | else: every test tied to every proof of the rule that could run here ran and passed; for a rule with no proof, every test marked with the rule's own id passed |

The words are read in that order. A rule whose proofs are all `@manual`
reads `passed`, since no run was ever going to observe one. A proof that
reads `nothing to check` counts as passed in an anchor's section and as not
run in any other.
````

After:

````
Each `rules` value is one word. The rows are read from the top, and the
first that holds gives the word:

| Word | When it holds |
|---|---|
| `failed` | a tied test of a proof that could run here failed; or a test marked with the rule's id failed |
| `no test` | a proof of the rule that is not `@manual` has no test tied to it, whether it is tagged `@env` or not; or no proof names the rule and no test is marked with its id |
| `not run` | a tied test did not run; or a proof of the rule is tagged `@env` for another operating system, so this machine could not answer; or the run left out the test of a proof tagged `@slow` |
| `passed` | none of the rows above holds: every test tied to every proof of the rule that could run here ran and passed. For a rule with no proof, every test marked with the rule's own id passed |

A rule whose proofs are all `@manual` reads `passed`, since no run was ever
going to observe one. A proof that reads `nothing to check` counts as passed
in an anchor's section and as not run in any other.
````

**7b. `references/formats/evidence_format.md`, the paragraph after the `proofs` table**

Before:

````
A test is tied to its proof by the marker comment above it, as
`references/formats/marker_format.md` says. A proof whose test was skipped, or
that no case in the report is, reads `missing` with the test named. A proof
whose every tied test skipped with a reason starting exactly `nothing to
check:` reads `nothing to check` instead, each entry carrying its `reason`;
in an anchor's section its rule reads `passed`, and in any other spec's
section `not run`. A proof
tagged `@env` for another operating system than the section's reads `not run`
whatever its tied test did there: a test carrying a Mac proof's marker and a
Windows proof's marker runs on the Mac and proves only the Mac proof. A proof
no test is tied to has one entry with an empty `test`, reading the same way.
A proof tagged `@slow` whose test the run left out reads `not run` with the
test named, unless the section the run replaces was taken over the same
fingerprint and holds a result for that test: then the entry keeps that
result.
````

After:

````
A test is tied to its proof by the marker comment above it, as
`references/formats/marker_format.md` says. Besides `pass` and `fail`, an
entry reads:

- **`missing`**, with the test named, where the test was skipped or the
  report holds no case for it.
- **`nothing to check`** instead, where every test tied to the proof skipped
  with a reason starting exactly `nothing to check:`. Each entry carries its
  `reason`. The proof's rule reads `passed` in an anchor's section and
  `not run` in any other spec's section.
- **`not run`** where the proof is tagged `@env` for another operating system
  than the section's, whatever its tied test did there. A test carrying a Mac
  proof's marker and a Windows proof's marker runs on the Mac and proves only
  the Mac proof.
- **`not run`**, with the test named, where the proof is tagged `@slow` and
  the run left its test out. One case differs: the section the run replaces
  was taken over the same fingerprint and holds a result for that test. The
  entry then keeps that result.

A proof no test is tied to has one entry with an empty `test`. It reads
`missing`, or `not run` where the proof is tagged `@env` for another
operating system.
````

**8. `references/review_criteria.md`, "Which rules the audit reads"**

Before:

````
A rule is read when it is its feature's own, at least one of its proofs has a test, its tests
pass, and it has no audit entry for its current rule, proofs and tests, or its feature's code
changed since that entry. An anchor's rules are read once, as the anchor's. `purlin:audit --all`
reads every rule that passes its tests again. A rule whose every proof is `@manual` has no test
to read and is not read.
````

After:

````
The audit reads a rule when all of these hold:

- the rule is its feature's own;
- at least one of its proofs has a test;
- its tests pass;
- it has no audit entry for its current rule, proofs and tests, or its feature's code changed
  since that entry.

An anchor's rules are read once, as the anchor's. `purlin:audit --all` reads every rule that
passes its tests again. A rule whose every proof is `@manual` has no test to read, so it is not
read.
````

**9. `agents/purlin.md`, "The words"**

Before:

````
A **rule** is one line saying what the software must do. A **proof** says in plain language how
that is shown, written to `references/spec_quality_guide.md`, "Writing proofs"; QA writes and
reads proofs, and you may draft them. A **test** is any test in the project's own suite with one
marker comment above it naming the proof, `purlin: login PROOF-4`, or the rule where the rule has
no proof. The **evidence** is what a run saw, one file per feature per source: `purlin:test`
writes each proof's result, `purlin:audit` adds what the audit found, and `--commit` commits it.
Its **source** is the folder it sits in, `.purlin/evidence/ci/` or `.purlin/evidence/local/`, and
both count. The **evidence package** is one data file describing one version of the code, built
by `purlin:sign` from the committed evidence. A **sign-off** is one person's signature over that
package, a file in a signed commit.

Purlin shows **two facts**, defined in `references/evidence_and_signoff.md`. The tests: `met`
when every rule passes its tests on the committed evidence, else `not met`. The sign-off:
`signed 0.1.0 at a1b2c3d`, `signed 0.1.0, 4 commits since`, or `not signed`. Every rule has two
**cells**: `passed` says every test tied to the rule ran and passed, on every **platform** a
counting run covered; `strong` says what the audit found, and nothing waits on it. A passed cell
whose platforms disagree reads `partial`, which is not met. A **hand check**, a proof marked
`@manual`, reads `checked at sign-off`: a person looks at it in the sign-off walk.
`references/glossary.md` defines the rest of the words.
````

After:

````
- A **rule** is one line saying what the software must do.
- A **proof** says in plain language how that is shown. It is written to
  `references/spec_quality_guide.md`, "Writing proofs". QA writes and reads proofs, and you may
  draft them.
- A **test** is any test in the project's own suite with one marker comment above it. The marker
  names the proof, `purlin: login PROOF-4`, or the rule where the rule has no proof.
- The **evidence** is what a run saw, one file per feature per source. `purlin:test` writes each
  proof's result, `purlin:audit` adds what the audit found, and `--commit` commits it.
- Its **source** is the folder it sits in, `.purlin/evidence/ci/` or `.purlin/evidence/local/`.
  Both count.
- The **evidence package** is one data file describing one version of the code. `purlin:sign`
  builds it from the committed evidence.
- A **sign-off** is one person's signature over that package, a file in a signed commit.

Purlin shows **two facts**, defined in `references/evidence_and_signoff.md`:

- The tests: `met` when every rule passes its tests on the committed evidence, else `not met`.
- The sign-off: `signed 0.1.0 at a1b2c3d`, `signed 0.1.0, 4 commits since`, or `not signed`.

Every rule has two **cells**:

- `passed` says every test tied to the rule ran and passed, on every **platform** a counting run
  covered. A passed cell whose platforms disagree reads `partial`, which is not met.
- `strong` says what the audit found. Nothing waits on it.

A **hand check** is a proof marked `@manual`. It reads `checked at sign-off`: a person looks at
it in the sign-off walk.

`references/glossary.md` defines the rest of the words.
````

## Item 3, before and after

**`references/review_criteria.md`, "How the checks are held to account", second item**

Before:

````
- Before a release, the checks run over Purlin's own tests. Every finding is read by a person
  and either fixed in the test or, if the check was wrong, the check is narrowed.
````

After:

````
- Before a release of Purlin, run the checks over Purlin's own tests. A person reads every
  finding. Fix the test or, where the check was wrong, narrow the check.
````

## Left open

Nothing. `skills/sign/SKILL.md` about line 74 is another lane's and was not touched.
