# Review criteria

What the audit reads on one rule, and what a person reads after. `purlin:audit` runs when a
person asks, and nothing waits on it. For each rule it reads it takes three steps: the heuristic
spot tests, then one model call for the rule's planted bugs and its reading, then each bug
planted and its proof's test run. The spot tests and the planted bugs set the rule's verdict; the
model's reading explains the tests and decides nothing. The model's request opens with this file
verbatim, so every sentence here is written to be read by a person and by a model.

## Which rules the audit reads

The audit reads a rule when all of these hold:

- the rule is its feature's own;
- at least one of its proofs has a test;
- its tests pass;
- it has no audit entry, or its entry is out of date because the rule, its proofs, its tests or
  its feature's code changed since, or a proof it plants a bug for has no result recorded.

An anchor's rules are read once, as the anchor's. `purlin:audit --all` reads every rule that
passes its tests again. A rule whose every proof is `@manual` has no test to read, so it is not
read.

## The verdict

A rule reads `weak` when a spot test fires on one of its tests or a planted bug survived. It
reads `strong` when none did and a planted bug was caught by its proof's test. It reads
`spot-checked` when none did and no bug was planted and caught; the entry then says why. Nothing
else sets it: the model's reading never changes it.

When the model cannot be reached for a rule, the spot tests still report what they find as
`weak`, and a rule that passed them is written `spot-checked` and read again by the next audit.

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
does, bug included. Model-written tests tend to capture what the code actually does rather than
what it should do
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
and model-written tests drift to the code's actual behaviour
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

The audit runs each proof's own test against a small change to the code. For a proof whose test
or whose feature's code changed since its last planted bug, the model is asked for the smallest
change to one file the feature covers that would break what the proof says. Its one reply for
the rule holds a part for each such proof, under a line naming the proof: the file, the exact
lines to change and what they become,

```
=== PROOF-1 ===
file: src/age.py
before:
<the exact lines>
after:
<the lines>
```

or, under the same line, `no break: <why>` when no change to those files can break what the
proof says. The change is made in a copy of the project, never in the project itself. Only the
proof's own tests run there, once before the change and once with it in place, and the copy is
deleted after.

- **Caught.** A test of the proof ran and failed with the change in place. The test noticed.
- **Survived.** Every one of the proof's own tests still passes with the change in place. The
  rule reads `weak`, with the finding
  `PROOF-1: the test still passes when src/age.py:12 reads "return 0"`.
- **Not run.** The test was skipped, could not be collected, ran past its limit or ended in an
  error its tool does not report as a failure, with the change in place. That decides nothing:
  the bug was neither caught nor missed.
- **Not made.** The reply held no part for the proof, or the part named no change, or a change
  that does not match its file exactly once, or a file the feature does not cover, or a file that
  holds one of the proof's tests, or the proof's test does not pass in the copy before any
  change. The test is not run against a bug, the audit prints `No bug was planted: <why>.`, and it
  is not a finding. Where the model could not be reached, nothing is recorded for the proof and
  its bug is asked for at the next audit.

A proof keeps its last result while its tests and its feature's code are unchanged, and no bug is
planted for it again. No bug is planted for an anchor's proof, a `@manual` proof or a proof tagged
for a system this machine is not. When a file of the project changes while the audit runs, the
audit stops and writes nothing.

## What the model is sent, and what it decides

The model is asked once for each rule: this file, then the rule's text, its proofs, the source of
each test, and under `Findings:` each finding of the spot tests, or `none`; then the proofs to
plant a bug for and the text of each file the feature covers. It answers with one part for each of
those proofs and then its reading. The model decides nothing; its reading explains.

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

**The call.** One call per rule, four at once, 300 seconds each, the request on its standard
input:

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
A rule on which a spot test fired is still written `weak`; any other is written `spot-checked`.

## Anchors and rules with no proof

An anchor's rule covers the whole project. Its test is strong only when it checks every file of
the project the rule speaks of, not a sample of them and not one feature's files. No bug is
planted for an anchor, so its rule reads `spot-checked` where the spot tests find nothing.

A rule no proof line names has no proof to read its test against, and the audit does not read
it. Whether a proof line is there is all the status reads; what a proof is worth is the audit's
question.

## What the audit reports

The audit reports. It recommends nothing.

- **Each rule it read**, its verdict, then each finding: the spot tests' sentences and each
  planted bug that survived. Then one sentence for each proof no bug was caught for, which is not
  a finding. Under a `spot-checked` rule those sentences follow `The spot tests found nothing.`
- **The share of rules found strong**, the last line:
  `The audit found 34 of 40 rules strong (85%): 34 strong, 4 weak, 2 spot-checked.`, counted over
  the rules that pass their tests, a rule with a hand check counted where it also has a tested
  proof. A team can set its own target, such as 80 percent, and check it here.

Each rule read gets one entry in its feature's evidence, under `audit.rules`: the hashes of its
rule, proofs, tests and code, the `verdict`, the `findings`, under `no_bug` one sentence for each
proof no bug was caught for, each planted bug under `breaks` with its file, line, the lines
before and after, and its result, the model's `explanation` and `notes`, the `model`, the sha256
of these `criteria`, the time and the commit. A person reads it beside the rule, each proof and
the source of each test, which is what the audit read.

A rule the audit found weak shows under `Left to do` as a rule to strengthen, and `purlin:build`
works on it. A case the test is missing is fixed by writing its proof line; the next
`purlin:build` writes the test for it.

## What the audit holds back

Nothing. The audit is a tool a person runs by hand. Neither the tests being met nor a sign-off
waits on it. Where it ran, what it found is written into the evidence and the evidence package,
and the signer of `purlin:sign` can read its findings as a list.
