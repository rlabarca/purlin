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
  user or a caller of the system would see. A path the software itself writes, reads or
  prints is output a caller sees, and naming it is not a finding.
- The proof describes the test's mechanics, a call, an assertion, a mock, a fixture or a spy,
  instead of what is shown.
- The proof shows more than one thing, so a failure could not say which one broke.
- The proof would read the same if the rule were broken, or it restates the rule and adds no
  input, action or value.
- A proof about a flow through the running app is described as a function call. Such a
  proof must read as arrange, act, observe, through the running app.

**In the marked test body.** The audit reads the source of each marked test and checks:

- The test body holds no assertion at all: no `assert`, no `self.assert*`, no
  `pytest.raises`, no `expect()`, no `Assert.`. It runs code and checks nothing.
- The assertion cannot fail: `assert result is not None`, `assert len(x) >= 0`,
  `expect(true).toBe(true)`, a `SELECT 'PASS'` nothing decides.
- The assertion is a literal true, such as `assert True`, `self.assertTrue(True)` or
  `Assert.True(true)`.
- A bare `except:` or `except Exception:` followed by `pass` wraps the code under test, so
  a failure is swallowed and the test passes through the bug.
- The expected value is computed by the same function the test is proving, so a bug in that
  function is confirmed rather than caught.
- A patch target names the very behaviour the rule describes, so the test replaces what it
  claims to prove. A test mocks the network, the clock and the filesystem, never the code
  under test.

A rule no proof line names, and no test marked with the rule's own id answers, reads
`no test` with the reason `no proof written`. A rule whose test passes and that has no proof
reads `no proof` in its strong cell, because there is no proof to read the test against.
Whether a proof line is there is all that is read there: what a proof is worth is the audit's
question, answered by a model that read the test beside it.

## What test strength says

Test strength is the share of deliberate breaks made to the code that the tests
caught, as an integer percent. It reads `test_strength` from the evidence, is
compared against `min_strength` from `.purlin/config.json`, and shows as `n/a` when no
engine ran.

It says one thing: the tests noticed when the behaviour changed. It does not say the
tests prove the right rule, that the proof text matches the test, or that the rule is
worth having. A rule can reach 90 percent strength on a proof that observes the wrong
thing, and a correct proof of a small rule can sit at 0 percent because nothing broke.
Read it beside what the audit observed, never instead of it.

## The three levels

A rule's **level** is what it must have to meet the gate, in the gate's own words: `passed`,
`strong` or `signed`. A rule marked `[level: ...]` asks for what it names; a rule with no mark
takes the project's gate, and a mark above the gate is read as the gate. The level is read at
`strong` and above; under `passed` it is never shown and it changes nothing.

**`passed`.** The tests are the evidence. A passing run from either source meets the level.
Under a gate above `passed` the AI audit does not read the rule; under the gate `passed` it
reads every rule and what it finds blocks nothing. The rule needs no signature, and it meets
the gate on its tests.

**`strong`** and **`signed`.** The strong cell is the evidence. The AI audit must have run on
the current rule, proof and test, observed nothing and settled, and where mutation testing is
on the strength must reach `min_strength`. Until it has run the strong cell reads
`not audited`; where it ran and could not tell it reads `weak` with the reason
`the AI audit could not decide: <its sentence>`; where it settled and still observed something
the cell reads `weak` with that sentence as the reason. Where no model could be reached nothing
is written, and the cell reads `not audited` until an audit reaches the rule. A rule whose
level is `signed` also needs a current signature in a signed commit.

## Who is in the queue

One list holds the rules whose next step is a person, the queue, and nothing else holds any.
Each row says what it needs.

A **hand check** exists at `strong` and above: a rule whose level is `strong` or `signed` and
whose strong cell reads `manual test`, because the proofs are `@manual` and no test can be
written.

A **signature** exists at the gate `signed`: a rule whose level is `signed`, whose passed and
strong cells are met, and that does not have a counting signature. Its row reads `unsigned` or
`stale`. A rule that needs both is one hand check.

A rule blocked at its passed cell is not in the queue, a rule with no proof written included:
it is build work and it stays on the board. A weak rule is build work too, and so is a rule
reading `not audited`, whose next step is `purlin:audit` rather than a reader. A rule whose
level is `passed` is never in it. The queue reads by feature, then by rule number.

## What the audit reports

The audit reports. It recommends nothing, and it never names a next action. Three things:

- **The strength, beside the minimum.** `Test strength: 71 percent (minimum 80)`, or
  `Test strength: n/a (minimum 80)` when no break engine ran.
- **The observations.** What the AI audit saw the test observe, against what the proof
  names, one sentence each. The audit is asked to state what it saw and to say when it
  cannot tell. It is never asked what to do.
- **Whether it settled.** `settled: yes` when the audit could tell and `settled: no` when it
  could not. `no` makes the strong cell read `weak`, with the audit's own sentence as the
  reason: an audit that cannot decide is build work. Where no model could be reached nothing
  is written, and the rule reads `not audited`. An audit that settled and still observed
  something is a different answer: it could tell, and what it saw is build work, so the cell
  reads `weak` with each observation sentence among its reasons.

What the audit found is written into the evidence with the name of the model that found it,
and a person reads it beside the rule, each proof and the source of each test, which is what
the audit read.

A `@manual` proof has no test, so there is no test body to read and no AI audit is asked
for. Its strong cell reads `manual test`.

What a person does with what the audit found is one of three things, and `purlin:sign` takes
each:

- **Sign it.** The test proves the proof. `purlin:sign <feature> RULE-N`.
- **Add a case.** The test is right as far as it goes and a case is missing, usually the
  failure the rule's proofs never name. Write the proof line; the next `purlin:build` writes
  the test for it.
- **Skip it.** Come back to it later. Nothing is written.
