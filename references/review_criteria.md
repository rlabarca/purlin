# Review criteria

What the AI audit reads on one rule, and what a person reads after. `purlin:audit` sets the
rule, its proofs and the source of each test that backs them beside the test strength from the
evidence, and sends that to a model, one call per rule. The prompt opens with this file
verbatim, so every sentence here is written to be read by a person and by a model.

## What the audit looks for

The AI audit reads each proof beside the source of the test that backs it and says what it
observed, one sentence at a time. A settled audit that observed a gap leaves the strong cell
reading `weak` with its own sentence as the reason. The checks below are what it looks for;
a rule that trips one may still be proved, so each is read against the test, never on the
proof text alone.

**In the proof description.** A good proof is defined in
`references/spec_quality_guide.md`, "Writing proofs", and the reasoning lives there. The audit
checks each of these against the test the proof names:

- The proof does not say what is done, what is observed and the expected value. It names no
  literal, number, quoted string, status or exact message, so almost any result would
  satisfy it. "Verify the parser handles the id" holds against a test that asserts nothing
  in particular.
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
  prints is output a caller sees, and naming it is not a finding.
- The proof describes the test's mechanics, a call, an assertion, a mock, a fixture or a spy,
  instead of what is shown.
- The proof would read the same if the rule were broken, or it restates the rule and adds no
  input, action or value.
- A proof about a flow through the running app is described as a function call. Such a
  proof must read as arrange, act, observe, through the running app.

**Notes, not findings.** A proof holds one case: one starting situation, one action and the
results seen from it, in at most 60 words, as `references/spec_quality_guide.md`, "One proof,
one case", says. A proof longer than 60 words, or one holding a second case, such as a refusal
beside the case that is allowed, is written under `notes:`, one sentence naming the proof. A
note never makes the rule `weak`: the rule is read against its test as it stands.

## Heuristic spot tests

The audit's first step reads each marked test as text, without running it, and flags a test that cannot fail. It catches the mistakes model-written tests are known to make. Each check below names what it flags, what it deliberately does not flag, the finding it reports, and the research it rests on.

### How the checks are designed

- **Each check flags only what it can be sure of.** Test-smell detectors are known to raise many
  false alarms, and most classic smells say little about whether a test can catch a bug
  ([Panichella et al., EMSE 2022](https://pure.tudelft.nl/ws/portalfiles/portal/137994226/s10664_022_10207_5.pdf)).
  So every check below is narrow: it fires on a pattern that is wrong in every case, and stays
  silent where a reasonable test could look similar. A missed case is left to the planted bug,
  the audit's second step, which runs the test for real.
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

**Does not flag** a proof that names no value in backticks; the same number written another way
(`90` and `90.0`); a value the test reads from a data file its own file names.

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
  silent on a right one, in Python, JavaScript or TypeScript, and C#, which Purlin's runner
  supports.
- Before release, the checks run over Purlin's own roughly 2,300 tests. Every finding is read by a
  person and either fixed in the test or, if the check was wrong, the check is narrowed. The count
  of findings and of false alarms is reported in the release notes.

## Anchors and rules with no proof

An anchor's rule covers the whole project. Its test is strong only when it checks every file of
the project the rule speaks of, not a sample of them and not one feature's files. No code is
broken on purpose for an anchor, so the audit alone judges its tests.

A rule no proof line names, and no test marked with the rule's own id answers, reads
`no test` with the reason `no proof written`. A rule whose test passes and that has no proof
reads `no proof` in its strong cell, because there is no proof to read the test against.
Whether a proof line is there is all that is read there: what a proof is worth is the audit's
question, answered by a model that read the test beside it.

## What test strength says

The model is shown the test strength of the feature the rule belongs to: of the deliberate
breaks made to that feature's code, the share its tests caught, as an integer percent, as
`Test strength 71%.` Where nothing was measured, or the engine cannot run on this system, the
model is shown `Test strength: not measured`. No strength is measured for an anchor. The
breaks run wherever `mutation_engine` in `.purlin/config.json` is not `none`, at either gate,
and the strength is a reason beside the strong cell's word, never the word itself.

It says one thing: the feature's tests noticed when its behaviour changed. It does not say
the tests prove the right rule, that the proof text matches the test, or that the rule is
worth having. A feature can reach 90 percent while one of its proofs observes the wrong thing,
and a rule proved correctly can belong to a feature at 0 percent because nothing broke. Read
it beside what the audit observed, never instead of it.

## What the audit holds back

Nothing. The AI audit and the breaks are tools at either gate: `purlin:audit` runs them when a
person asks, and neither a gate nor a release waits on them. Where the audit ran, what it found
is written into the evidence and the evidence package. Until it has run the strong cell reads
`not audited`; where it ran and could not tell it reads `weak` with the reason
`the AI audit could not decide: <its sentence>`; where it settled and still observed something
the cell reads `weak` with that sentence as the reason. Where no model could be reached nothing
is written, and the cell reads `not audited` until an audit reaches the rule.

## What the audit reports

The audit reports. It recommends nothing, and it never names a next action. Four things:

- **The feature's test strength, where it was measured.** `Test strength 71%.` Where
  nothing was measured the report says nothing of strength, and the model reading the rule is
  shown `Test strength: not measured`.
- **The observations.** What the AI audit saw the test observe, against what the proof
  names, one sentence each. The audit is asked to state what it saw and to say when it
  cannot tell. It is never asked what to do.
- **Whether it settled.** `settled: yes` when the audit could tell and `settled: no` when it
  could not. `no` makes the strong cell read `weak`, with the audit's own sentence as the
  reason: an audit that cannot decide is build work. Where no model could be reached nothing
  is written, and the rule reads `not audited`. An audit that settled and still observed
  something is a different answer: it could tell, and what it saw is build work, so the cell
  reads `weak` with each observation sentence among its reasons.
- **The notes.** A proof longer than the standard, or holding two cases, one sentence each
  under `notes:`. They are written beside what the audit found, printed after the findings,
  each on a line of its own starting `Note:`, and change no cell.

What the audit found is written into the evidence with the name of the model that found it,
and a person reads it beside the rule, each proof and the source of each test, which is what
the audit read.

A `@manual` proof has no test, so there is no test body to read and no AI audit is asked
for. Its strong cell reads `manual test`.

A rule the audit found weak is build work: it shows under `Left to do` as a rule to strengthen,
and `purlin:build` works on it. A weak finding does not stop a release. At the gate `signed`
the sign-off walk of `purlin:sign` stops at each weak rule and each rule no audit has read,
shows its proofs, its tests and what the audit found, and the signer continues, adds a note,
or stops to fix it. A case the test is missing is fixed by writing its proof line; the next
`purlin:build` writes the test for it.
