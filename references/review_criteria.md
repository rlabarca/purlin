# Review criteria

What the audit reads on one rule, and what a person reads after. `purlin:audit` runs when a
person asks, and nothing waits on it. For each rule it reads it takes three steps: the heuristic
spot tests; then the model is asked for a small bug for each proof, aimed past that proof's test,
and for its reading; then each bug is planted and its proof's test run. The spot tests and the
planted bugs set the rule's verdict; the model's reading explains the tests and decides nothing. The model's request opens with this file
verbatim, so every sentence here is written to be read by a person and by a model.

## Which rules the audit reads

The audit reads a rule when all of these hold:

- the rule is its feature's own;
- at least one of its proofs has a test;
- its tests pass;
- it has no audit entry, or its entry is out of date because the rule, its proofs, its tests or
  its feature's code changed since, or a proof it plants a bug for has no result recorded.

A test is compared by its own lines, from its declaration to the end of its body. A test
changed through a helper it calls, with its own lines as they were, keeps its audit result.
Change the test's own lines to have a new bug planted, or run `purlin:audit --all`, which reads
the rule again with the spot tests and the model's reading and keeps each planted bug's
result.

An anchor's rules are read once, as the anchor's. `purlin:audit --all` reads every rule that
passes its tests again. A rule whose every proof is `@manual` has no test to read, so it is not
read.

## The verdict

A rule reads `weak` when a spot test fires on one of its tests or a planted bug survived. It
reads `strong` when none did and a planted bug was caught by its proof's test. It reads
`spot-checked` when none did and no bug was planted and caught; the entry then says why. Nothing
else sets it: the model's reading never changes it.

When the model cannot be reached for a rule, the spot tests and the bugs kept from earlier
audits still set its verdict: a finding of the spot tests or a kept bug that survived reads
`weak`, and a kept bug that was caught, with neither, reads `strong`. Any other rule is written
`spot-checked` and read again by the next audit.

## Heuristic spot tests

The audit's first step reads each marked test as text, without running it, and flags a test that cannot fail. It catches the mistakes model-written tests are known to make. Each check below names what it flags, what it deliberately does not flag, the finding it reports, and the research it rests on.

### How the checks are designed

- **Each check flags only what it can be sure of.** Test-smell detectors are known to raise many
  false alarms, and most classic smells say little about whether a test can catch a bug
  ([Panichella et al., EMSE 2022](https://pure.tudelft.nl/ws/portalfiles/portal/137994226/s10664_022_10207_5.pdf)).
  So every check below is narrow: it fires on a pattern that is wrong in every case, and stays
  silent where a reasonable test could look similar. A missed case is left to the planted bug,
  the audit's third step, which runs the test for real.
- **A finding never blocks anything.** It is reported, with the test's file and name and one
  sentence on why, and the rule reads `weak` until the test changes.
- **Each check is about whether the test can fail, not about style.** Smells about readability
  or maintenance, such as many assertions in one test or magic numbers, are left out (see
  "Considered and left out").

### The six checks

#### 1. The test checks nothing

**Flags** a test whose body, and the helpers it calls in the same file, hold no assertion of its
test framework: no `assert`, `self.assert…`, `pytest.raises`, `expect(`, `assert.` (Node),
`Assert.` (.NET), or a shell test's comparison.

**Does not flag** a test that calls a helper defined in another file, which may assert; a test
that only expects an error (`pytest.raises`, `toThrow`, `Assert.Throws`) counts as asserting.

**Finding:** `tests/test_age.py::test_age: the test checks nothing.`

**Why:** a test that runs code and checks nothing passes whatever the code does. It is the
"Empty Test" and "Unknown Test" smells of
[tsDetect (Peruma et al., FSE 2020)](https://2020.esec-fse.org/details/esecfse-2020-tool-demos/4/tsDetect-An-Open-Source-Test-Smells-Detection-Tool),
and it is common in model-written tests
([Siddiq et al., EASE 2024](https://arxiv.org/pdf/2305.00418)). Code a test runs but never checks
cannot be said to be tested
([Schuler and Zeller, ICST 2011](https://www.st.cs.uni-saarland.de/publications/files/schuler-icst-2011.pdf)).

#### 2. The check cannot fail

**Flags** an assertion that is true whatever the code does: a literal true (`assert True`,
`self.assertTrue(True)`, `expect(true).toBe(true)`, `Assert.True(true)`); a value compared with
itself (`assert x == x`); a size compared as at least zero (`assert len(x) >= 0`).

**Does not flag** a weak but failable check, such as `assert result is not None`; that is the
planted bug's to judge.

**Finding:** `tests/test_age.py::test_age: the check cannot fail: assert len(ages) >= 0.`

**Why:** the "Redundant Assertion" smell of
[tsDetect](https://2020.esec-fse.org/details/esecfse-2020-tool-demos/4/tsDetect-An-Open-Source-Test-Smells-Detection-Tool):
an assertion that is always true checks nothing.

#### 3. The test swallows the error

**Flags** a `try` around the code under test whose `except` or `catch` does nothing (`pass`, an
empty block) and does not assert or re-raise, so a failure inside is hidden and the test passes.

**Does not flag** a `try` whose handler asserts something about the error, or one used only for
cleanup.

**Finding:** `tests/test_age.py::test_bad_zone: the test swallows the error the code raises.`

**Why:** a narrow form of tsDetect's "Exception Handling" smell
([Peruma et al., FSE 2020](https://2020.esec-fse.org/details/esecfse-2020-tool-demos/4/tsDetect-An-Open-Source-Test-Smells-Detection-Tool)):
an error that is caught and dropped cannot fail the test.

#### 4. The test checks the code against itself

**Flags** an assertion whose expected value is computed by the same function or method whose
result it checks, as in `assert age(s) == age(s)` or `expected = age(s)` then
`assert age(s) == expected`.

**Does not flag** an expected value computed by a different function, a library, or a literal.

**Finding:** `tests/test_age.py::test_age: the expected value comes from age(), the code under test.`

**Why:** a test whose expected answer comes from the code under test confirms whatever the code
does, bug included. Shown buggy code, a model more often rejects the right expected answer
([Konstantinou, Degiovanni and Papadakis, 2024](https://arxiv.org/pdf/2410.21136)); the expected
value should come from somewhere the code cannot influence, the problem at the heart of
[the test oracle survey (Barr et al., TSE 2015)](https://discovery-pp.ucl.ac.uk/id/eprint/1471263/1/06963470.pdf).

#### 5. The test replaces what it is testing

**Flags** a mock, patch, stub or fake whose target is the same function or method whose result
the test asserts on.

**Does not flag** a mock of something the code depends on, such as the network, the clock, a
database or another service.

**Finding:** `tests/test_age.py::test_age: the test mocks age(), the function it checks.`

**Why:** developers mock the dependencies that make testing hard, not the code that holds the
rules ([Spadini et al., MSR 2017](https://repository.tudelft.nl/file/File_dcb7ec41-615b-457c-9b5f-e6c6de2dea7e?preview=1));
a test that mocks the thing it checks only checks the mock. Coding agents add more mocks than
people do ([an empirical study of coding agents, 2026](https://arxiv.org/pdf/2602.00409)).

#### 6. The test never checks the result the proof expects

**Flags** a test whose file holds none of the values its proof names. A proof marks its expected
values in backticks, as in "has an age of `90` minutes"; if `90` appears nowhere in the test's
file, the test cannot be checking it.

**Does not flag** a proof that names no value in backticks; an empty pair of backticks, which
marks an empty value and names nothing to look for; the same number written another way (`90` and
`90.0`); a value the test reads from a data file its own file names.

**Finding:** `tests/test_age.py::test_age: the proof expects 90 and the test never checks it.`

**Why:** this check needs a specification, so no general tool can make it, and it is Purlin's
own. It follows from the oracle problem: the expected value should come from the requirement,
not the code ([Barr et al., TSE 2015](https://discovery-pp.ucl.ac.uk/id/eprint/1471263/1/06963470.pdf)),
and a model shown buggy code more often rejects the right expected answer
([Konstantinou et al., 2024](https://arxiv.org/pdf/2410.21136)). The proof is the requirement's
expected value, written by a person; a test that never mentions it is checking something else.

### Considered and left out

- **Many assertions in one test, magic numbers, eager tests, a shared fixture, a sleep, a print.**
  These are maintenance smells. They make a test harder to read, not unable to fail, and their tie
  to real flaws is weak ([Panichella et al., EMSE 2022](https://pure.tudelft.nl/ws/portalfiles/portal/137994226/s10664_022_10207_5.pdf)).
- **Code coverage.** Running a line says little about whether a bug in it would be caught
  ([Inozemtseva and Holmes, ICSE 2014](https://cs.ubc.ca/~rtholmes/papers/icse_2014_inozemtseva.pdf)).
- **A weak but failable check, such as "is not None".** Flagging it would raise many false alarms;
  the planted bug shows whether it is too weak.

### How the checks are held to account

- Each check has a rule and proofs, with tests that show it firing on a wrong test and staying
  silent on a right one, in Python, JavaScript or TypeScript, and C#.
- Before a release of Purlin, run the checks over Purlin's own tests. A person reads every
  finding. Fix the test or, where the check was wrong, narrow the check.

## The planted bug

The audit runs each proof's own test against one small change to the code, aimed past that test.
For a proof whose test or whose feature's code changed since its last planted bug, the model is
shown the proof, its test and each file the feature covers. It is asked for the smallest change
to one of those files after which what the proof says no longer holds: the case the proof names
gives a different result from the one it names.

**The aim.** Of the changes that break the proof's case, the model chooses the one the proof's
test, as it is written, is most likely to miss: a value the test never compares, a case other
than the proof's, an expected value the test takes from the code. Where the test checks the
proof's case and its result, no change gets past it, and the model makes the plainest change
that breaks the case. A change that leaves the proof's case as it was is never the bug, and the
change carries no comment about the bug.

**The part.** The model's reply holds a part for each such proof, under a line naming the proof:
the aim, the case, the file, the exact lines to change and what they become,

```
=== PROOF-1 ===
aim: past the test
case: a sample collected 90 minutes ago; the proof says 90; the changed code gives 150
file: src/age.py
before:
<the exact lines>
after:
<the lines>
```

or, under the same line, `no bug: <why>` when no change to those files can break what the
proof says. The reason is that one line; an `aim:` line may stand above it.

- `aim:` reads `past the test`, or `plain` where the test leaves no way past it. Any other
  word, or no `aim:` line, is recorded `plain`.
- `case:` is one line: the proof's case, the result the proof names and the result the changed
  code gives. It is the model's claim, and the audit does not check it. It is kept as written,
  up to 300 characters, without control characters and terminal escape sequences.

The change is made in a copy of the project, never in the project itself. Only the proof's own
tests run there, once before the change and once with it in place, and the copy is deleted
after.

- **Caught.** A test of the proof ran and failed with the change in place. The test noticed, and
  nothing is added to the rule's findings.
- **Survived.** Every one of the proof's own tests still passes with the change in place. The
  rule reads `weak`, with two findings, the change and then the case the model says it breaks:
  `PROOF-1: the test still passes when src/age.py:12 reads "return minutes + 60"`
  `PROOF-1: the AI says this breaks: a sample collected 90 minutes ago; the proof says 90; the changed code gives 150`
  A test run settles the first, as "Settling a finding" says.
- **Not run.** The test was skipped, could not be collected, ran past its limit or ended in an
  error its tool does not report as a failure, with the change in place. That decides nothing:
  the bug was neither caught nor missed.
- **Not made.** The reply held no part for the proof, or the part named no change, or a change
  and no case of the proof, or a change that touches only a comment, or a change that leaves
  the file as it was, or a change that does not match its file exactly once, or a path outside
  the copy of the project, or a file that is not in the project, or a file the feature does not
  cover, or a file that holds one of the proof's tests, or the proof's test does not pass in the
  copy before any change. The test is not run against a bug, the audit prints
  `No bug was planted: <why>.`, and it is not a finding. Where the model could not be reached,
  nothing is recorded for the proof and its bug is asked for at the next audit.

Two of those reasons are refusals of a change the model did name:

- `No bug was planted: the model's answer for PROOF-1 could not be used: the answer named no case of the proof.`
  The part holds no `case:` line, or an empty one.
- `No bug was planted: the model's answer for PROOF-1 could not be used: the change touches only a comment.`
  The lines after the change differ from the lines before it only in blank lines, comment
  lines and a comment at the end of a code line. A comment line starts, after its indent, with
  `//` in any file, or with `#` in a file ending `.py`, `.sh`, `.bash`, `.rb`, `.yml`, `.yaml`
  or `.toml`. A comment at the end of a code line starts, after a space, with `#` in a file
  with one of those endings and with `//` in any other file; a line that holds a quotation mark
  before it is read as code. A line opening `#!`, `//go:` or `// @ts-`, after any indent, is
  read as code. The check is narrow: a `/* */` comment, a docstring, a `--` comment and a
  comment in any other kind of file are read as code, and such a change is planted.

A proof keeps its last result while its tests and its feature's code are unchanged, and no bug is
planted for it again; a kept bug that survived adds its two findings again. No bug is planted for
an anchor's proof, a `@manual` proof or a proof tagged for a system this machine is not. When a
file of the project changes while the audit runs, the audit stops and writes nothing.

**A bug that survived is planted again first.** Where the feature's code changed and the proof's
test is as it was when the bug got past it, the audit makes the recorded change again in a copy,
with every refusal above, and runs the proof's own tests. The model is asked for no bug for that
proof.

- **The test still passes.** The bug still reads `survived`, its two findings stay, at the line
  the change now stands at, and the rule reads `weak`. The audit prints, under the rule,
  `  PROOF-1: its test is as it was and still passes with the bug it missed. Strengthen it with purlin:build.`
- **The test fails.** The code changed and the test did not, and the test now catches the bug.
  The entry reads `caught`, its two findings leave the rule, and the audit prints
  `  PROOF-1: the test now catches the bug it missed at src/age.py:12.`
- **The test does not run** with the bug in place: the entry reads `not run`.
- **The recorded change can no longer be planted**, because its `before` lines are not in the
  file exactly once or another refusal above holds: a new bug is asked for.

The two printed lines are not stored. A bug that survived whose proof's test changed is not
planted again by this audit: a new bug is asked for. "Settling a finding" says what is compared,
and how a finding that still holds is cleared.

## Settling a finding

A planted bug that survived is settled by a test run, and a finding of the spot tests by
reading the test again. `purlin:build` strengthens the test, then
runs `purlin:audit <feature> RULE-N --settle`, which is
`scripts/run/purlin_run.py --audit --feature <feature> --settle RULE-N`. `--settle` is given once
per rule, beside `--audit` and exactly one `--feature`, and `--commit` works as on any audit.
The script takes `--sound PROOF-N` the same way, once per proof.

- Without `--audit`, without `--feature` or with two features, the run is refused before
  anything runs and exits 2.
- A rule the feature's spec does not have is named before anything runs, and the run exits 1:
  `<feature> RULE-N is not a rule any spec has. Run purlin:status <feature> to see its rules.`
- The feature's tests run first, as on any audit. A rule whose tests do not pass is not
  settled, and the run names it as failing.
- The test of a proof tagged `@slow` is started with them where its rule is named, so one
  command settles a rule with a slow proof. The slow tests of every other rule are left out,
  and the run names them.
- Only the rules named are read.

**A test that has not changed.** While the recorded bug still gets past the test, a finding is
cleared by a stronger test or by a recorded judgment that the test was sound already, and by
nothing else. So a settle plants nothing for a proof whose test is as it was when the bug got
past it. The audit prints, under the rule,
`  PROOF-2: its test is as it was when the bug got past it. Strengthen it with purlin:build, then settle.`
The bug still reads `survived`, its two findings stay, and the rule reads `weak`.

- **What is compared.** The proof's own tests as the audit reads them: each test's own lines,
  from its declaration to the end of its body, or the whole file for a shell or SQL test. A
  change elsewhere in the file, to a helper, a fixture or another test, is not a change to
  the test. A bug recorded as `survived` holds the sha256 of those tests as `test_key`.
- **A test whose source is not found** is read as changed.
- **`--sound PROOF-N`** says the test of that proof was read against the proof and judged to
  assert what the proof names already. It is given once per proof, beside `--settle`:
  `purlin:audit <feature> RULE-N --settle --sound PROOF-N`. The settle then goes on for that
  proof as the steps below say. The entry it writes for the proof holds `test_unchanged`:
  `true`, and `no_bug` gains
  `PROOF-2 was settled with its test unchanged: it was judged to assert what the proof names.`
  The audit prints that sentence under the rule, last, and every later audit that keeps the
  entry prints it again. A new bug that reads `survived` is a new finding and carries
  neither.
- `--sound` without `--settle` is refused before anything runs and exits 2. A proof that is
  no proof of a rule named with `--settle`, or that keeps no bug as `survived`, is named
  before anything runs, and the run exits 1:
  `<feature> PROOF-N is not a proof of a rule named with --settle. Run purlin:status <feature> to see its rules.`
  `<feature> PROOF-N has no planted bug that survived: nothing to settle.`
- `--sound` for a proof whose test did change records nothing: the settle goes on as any
  settle does.

**Settling one rule.** For each proof of the rule whose entry under `bugs` reads `survived`,
and whose test changed since or which `--sound` names:

1. **The bug is planted again.** The recorded change, its `file`, `before` and `after`, is made
   in a copy of the project, with every refusal of "The planted bug", and the proof's own tests
   run, once before the change and once with it in place. No model is asked.
2. **The test fails.** The finding was right, and the test now catches the bug. The entry reads
   `caught`, with the same `file`, `line`, `before`, `after`, `aim` and `case`, and the
   `bug_key` of the test and code as they stand. Its two findings leave the rule. The audit
   prints, under the rule,
   `  PROOF-2: the test now catches the bug it missed at src/auth.py:12.`
3. **The test still passes.** The bug did not break what the proof says, so it is dropped. The
   model is asked for one new bug for that proof, in the usual request, and it is planted as
   any bug is. The audit prints
   `  PROOF-2: the bug at src/auth.py:12 did not break what the proof says. A new bug was planted.`
   - The new bug is caught: the entry reads `caught`, as any caught bug.
   - The new bug survives too: no bug is kept. The entry reads `not made`, with the `why`
     `two planted bugs left the proof's check passing` and the `bug_key` of the test and code
     as they stand, and `no_bug` gains
     `No bug was caught for PROOF-2: two planted bugs left the proof's check passing.`
   - No new bug is planted, because the model answers `no bug`, its part cannot be used or
     the model cannot be reached: `no_bug` holds the sentence that case has in any audit, and
     the printed line ends at `did not break what the proof says.`
4. **The test does not run** with the recorded bug in place, because it is skipped, ends in an
   error or runs past its limit: the entry reads `not run`.
5. **The recorded change can no longer be planted**, because its `before` lines are not in the
   file exactly once or another refusal of "The planted bug" holds: the proof is read as any
   audit reads it, with a new bug, and one that survives reads `survived`.

A proof of the rule with no `survived` entry keeps what it has where its test and code are
unchanged since that result. A result taken on another test or code is left out of the entry,
and the next audit without `--settle` plants a bug for that proof. The audit prints, under the
rule,
`  PROOF-2: no bug is on record for its test as it stands. Run purlin:audit <feature> to plant one.`

The spot tests run again over the rule's tests, and "The verdict" sets the rule's word as in
any audit, from the results the entry holds: `weak` where a spot test fires or a bug survived,
else `strong` where a bug was caught, else `spot-checked`. A proof whose two bugs both survived
holds no caught bug, and the rule still reads `strong` where another of its proofs does. A
rule with two bugs that survived, one proof's test changed and the other's not, has the first
settled and the second refused, and reads `weak` while the second survives.

**A finding of the spot tests.** A rule named with `--settle` whose entry holds a finding of
the spot tests is read, whether or not it keeps a bug as `survived`. The spot tests run over
its tests as they stand, and no model is asked for a rule that needs no new bug, so a fixed
test clears its finding at once. For each test they no longer find anything in, the audit
prints, under the rule and before any other line,
`  tests/test_age.py::test_age: the spot tests now find nothing.`
A finding that still holds is printed again, and the rule reads `weak`.

A rule named with `--settle` that keeps no bug as `survived`, and whose entry holds no finding
of the spot tests, prints
`<feature> RULE-N has no planted bug that survived: nothing to settle.` and is left as it is.
A rule whose every surviving bug is refused is read and asks no model.

A dropped bug is kept nowhere: not under `bugs`, not among the `findings`, not in the evidence
package. The `not made` entry of step 3 holds the state, so no audit plants a bug for that proof
until its test or code changes. The lines of steps 2 and 3, the line that refuses a settle,
the line for a test the spot tests now find nothing in and the line for a proof with no bug on
record are printed and not stored. One run
drops a bug, plants one more and ends: nothing counts the bugs between runs.

Where a settled rule needs no new bug, no model is asked. Its entry keeps the `model` and the
`criteria` of the entry it replaces and holds no `explanation`, since that reading was of the
test as it was.

An audit without `--settle` plants a recorded bug again only where the code changed and the
test is as it was, as "The planted bug" says, and the bug stays while the test still passes
with it. For a proof whose test changed, that audit asks for a new bug, and a survivor reads
`weak`.

The audit checks that the test changed, not that the changed test asserts what its proof
names; and under `--sound` it records the judgment and does not check it. A rule made `strong`
by settling caught the bug it once missed, with a test written after that bug was seen.

## What the model is sent, and what it decides

The model is asked for a small bug for each proof and for its reading. The request holds this
file, then the rule's text, its proofs, the source of each test, and under `Findings:` each
finding of the spot tests, or `none`; then the proofs to plant a bug for, the aim of "The planted
bug" and the text of each file the feature covers. It answers with one part for each of those
proofs and then its reading. The model decides nothing: the test run says whether a bug was
caught, the case it names is shown as its claim, and its reading explains.

**The reading.** Under a line `=== reading ===`, one sentence per line, each opening `- `: what
each test observes against what its proof names, and why each finding holds or what it misses. Then, where there is one, a line
`notes:` and one sentence per note, each opening `- ` and naming the proof. Nothing else: no
recommendation, no grade, no score, no verdict. A person reads what the model wrote beside the
findings and decides.

```
=== reading ===
- PROOF-2: the test calls login and reads no status, so a wrong status still passes.
notes:
- PROOF-2 holds two cases.
```

**What the explanation may point at in a proof.** A good proof is defined in
`references/spec_quality_guide.md`, "Writing proofs", and the reasoning lives there. Each of these
is read against the test the proof names, never on the proof text alone:

- The proof does not say what is done, what is observed and the expected value. It names no
  literal, number, quoted string, status or exact message, so almost any result would
  satisfy it.
- The expected value is not a real value: the proof says "works", "correctly", "properly",
  "as expected" or "successfully" with nothing beside it.
- Nothing is done before the observation, so the proof reads something that exists whether
  or not the software is right.
- No proof of the rule names a failure case or a boundary. A rule that refuses, limits,
  blocks or expires anything has been proved in one direction only.
- A person who cannot read code could not judge the proof: it names a source or test file
  path, a function, a class, a selector or a test framework, where it should name what a
  user or a caller of the system would see, as `references/spec_quality_guide.md`, "Written
  for a person who cannot read code", says. A path the software itself writes, reads or
  prints is output a caller sees, and naming it is not a problem.
- The proof describes the test's mechanics, a call, an assertion, a mock, a fixture or a spy,
  instead of what is shown.
- The proof would read the same if the rule were broken, or it restates the rule and adds no
  input, action or value.
- A proof about a flow through the running app is described as a function call. Such a
  proof must read as arrange, act, observe, through the running app.

**Notes.** A proof holds one case: one starting situation, one action and the results seen from
it, in at most 60 words, as `references/spec_quality_guide.md`, "One proof, one case", says. A
proof longer than 60 words, or one holding a second case, such as a refusal beside the case that
is allowed, is written under `notes:`, one sentence naming the proof.

**The call.** Each request is written to the command's standard input and given 300 seconds:

```
claude -p --output-format json --max-turns 1 --tools "" --strict-mcp-config --safe-mode \
  --setting-sources "" --disable-slash-commands --no-session-persistence \
  --system-prompt "<the audit's own>"
```

The model is given no tools and is started in an empty folder, so it can read and change nothing.
It is started with `DISABLE_PROMPT_CACHING=1`, with no MCP server, no plugin, no skill, no
project instructions and none of the person's settings. Each answer names the model that gave it
and the sha256 of this file as it was sent. When `claude` is not on the path, exits with an error,
runs past its 300 seconds or gives no answer, no explanation is recorded and the audit prints one
line naming the reason, `claude is not on PATH`, `claude exited with an error`,
`claude timed out after 300 s` or `claude gave no answer`:
`The model could not be reached: claude is not on PATH. 2 rules are spot-checked alone. Run purlin:audit again.`
Bugs kept from earlier audits still count. A rule on which a spot test fired, or with a kept
bug that survived, is still written `weak`; one with neither and a kept bug that was caught is
written `strong`; any other is written `spot-checked`.

## Anchors and rules with no proof

An anchor's rule covers the whole project. Its test is strong only when it checks every file of
the project the rule speaks of, not a sample of them and not one feature's files. No bug is
planted for an anchor, so its rule reads `spot-checked` where the spot tests find nothing.

Any change to the project ends an anchor's audit result. `purlin:test --all` and
`purlin:test --clean` keep it current: once the anchors' tests have run, the spot tests read
again each rule of an anchor that passes its tests and holds an audit entry. No model is asked.
The entry is written as the audit writes it, `spot-checked` with its reason or `weak` with the
spot tests' findings, and the run prints
`Anchors: the spot tests read 2 audited rules again. 2 spot-checked, 0 weak.`
An anchor's rule with no audit entry is left as it is: the audit is a person's to start.

A rule no proof line names has no proof to read its test against, and the audit does not read
it. Whether a proof line is there is all the status reads; what a proof is worth is the audit's
question.

## What the audit reports

The audit reports. It recommends nothing.

- **Each rule it read**, its verdict, then each finding: the spot tests' sentences and, for each
  planted bug that survived, the change and then the case the model says it breaks. Then one
  sentence for each proof no bug was caught for and one for each proof settled with its test
  unchanged, neither of which is a finding. Under a `spot-checked`
  rule those sentences follow `The spot tests found nothing.`
- **The share of rules found strong**, the last line:
  `The audit found 34 of 40 rules strong (85%): 34 strong, 4 weak, 2 spot-checked.`, with the
  numbers the status gives. Each rule that passes its tests is counted under the word its strong
  cell reads, and the share counts no rule of an anchor; a rule with a hand check whose strong cell reads `checked at sign-off` is in no
  count. A team can set its own target, such as 80 percent, and check it here.

Each rule read gets one entry in its feature's evidence, under `audit.rules`: the hashes of its
rule, proofs, tests and code, the `verdict`, the `findings`, under `no_bug` one sentence for each
proof no bug was caught for, each planted bug under `bugs` with its `aim`, its `case`, its
file, line, the lines before and after, and its result, the model's `explanation` and `notes`, the `model`, the sha256
of these `criteria`, the time and the commit. A person reads it beside the rule, each proof and
the source of each test, which is what the audit read.

A rule the audit found weak shows under `Left to do` as a rule to strengthen, and `purlin:build`
works on it: it strengthens the test, then settles the rule as "Settling a finding" says. A case
the test is missing is fixed by writing its proof line; the next `purlin:build` writes the test
for it.

## What the audit holds back

Nothing. The audit is a tool a person runs by hand. Neither the tests being met nor a sign-off
waits on it. Where it ran, what it found is written into the evidence and the evidence package,
and the signer of `purlin:sign` can read its findings as a list.
