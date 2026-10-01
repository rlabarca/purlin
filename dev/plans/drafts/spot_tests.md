# Heuristic spot tests

> Draft of the reference for the audit's first step (decision 110), written before it is built.
> The build places it in `references/review_criteria.md`, the one home of what the audit looks
> for, implements it in code, and gives each check a rule, its proofs and their tests.

The audit's first step reads each marked test as text, with no model and without running it, and
flags a test that cannot fail. It is cheap, it gives the same answer every time, and it catches the
mistakes AI-written tests are known to make.

## How the checks are designed

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

## The six checks

### 1. The test checks nothing

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

### 2. The check cannot fail

**Flags** an assertion that is true whatever the code does: a literal true (`assert True`,
`self.assertTrue(True)`, `expect(true).toBe(true)`, `Assert.True(true)`); a value compared with
itself (`assert x == x`); a size compared as at least zero (`assert len(x) >= 0`).

**Does not flag** a weak but failable check, such as `assert result is not None`; that is the
planted bug's to judge.

**Finding:** `tests/test_age.py::test_age: the check cannot fail: assert len(ages) >= 0.`

**Why:** the "Redundant Assertion" smell of
[tsDetect](https://2020.esec-fse.org/details/esecfse-2020-tool-demos/4/tsDetect-An-Open-Source-Test-Smells-Detection-Tool):
an assertion that is always true checks nothing.

### 3. The test swallows the error

**Flags** a `try` around the code under test whose `except` or `catch` does nothing (`pass`, an
empty block) and does not assert or re-raise, so a failure inside is hidden and the test passes.

**Does not flag** a `try` whose handler asserts something about the error, or one used only for
cleanup.

**Finding:** `tests/test_age.py::test_bad_zone: the test swallows the error the code raises.`

**Why:** a narrow form of tsDetect's "Exception Handling" smell
([Peruma et al., FSE 2020](https://2020.esec-fse.org/details/esecfse-2020-tool-demos/4/tsDetect-An-Open-Source-Test-Smells-Detection-Tool)):
an error that is caught and dropped cannot fail the test.

### 4. The test checks the code against itself

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

### 5. The test replaces what it is testing

**Flags** a mock, patch, stub or fake whose target is the same function or method whose result
the test asserts on.

**Does not flag** a mock of something the code depends on, such as the network, the clock, a
database or another service.

**Finding:** `tests/test_age.py::test_age: the test mocks age(), the function it checks.`

**Why:** developers mock the dependencies that make testing hard, not the code that holds the
rules ([Spadini et al., MSR 2017](https://repository.tudelft.nl/file/File_dcb7ec41-615b-457c-9b5f-e6c6de2dea7e?preview=1));
a test that mocks the thing it checks only checks the mock. Coding agents add more mocks than
people do ([an empirical study of coding agents, 2026](https://arxiv.org/pdf/2602.00409)).

### 6. The test never checks the result the proof expects

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

## Considered and left out

- **Many assertions in one test, magic numbers, eager tests, a shared fixture, a sleep, a print.**
  These are maintenance smells. They make a test harder to read, not unable to fail, and their tie
  to real flaws is weak ([Panichella et al., EMSE 2022](https://pure.tudelft.nl/ws/portalfiles/portal/137994226/s10664_022_10207_5.pdf)).
- **Code coverage.** Running a line says little about whether a bug in it would be caught
  ([Inozemtseva and Holmes, ICSE 2014](https://cs.ubc.ca/~rtholmes/papers/icse_2014_inozemtseva.pdf)).
- **A weak but failable check, such as "is not None".** Flagging it would raise many false alarms;
  the planted bug shows whether it is too weak.

## How the checks are held to account

- Each check has a rule and proofs, with tests that show it firing on a wrong test and staying
  silent on a right one, in Python, JavaScript or TypeScript, and C#, which Purlin's runner
  supports.
- Before release, the checks run over Purlin's own roughly 2,300 tests. Every finding is read by a
  person and either fixed in the test or, if the check was wrong, the check is narrowed. The count
  of findings and of false alarms is reported in the release notes.
