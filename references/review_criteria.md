# Review criteria

What the brief checks on one rule before a person reads it, and what a person checks after.
The brief runs these layers cheapest first and stops when it has enough for the rule's bar:
the free checks on the proof text, the free checks on the test body, the test strength from
the latest record, then the AI audit on every rule whose bar is `strong`. The brief builds that model
prompt from this file verbatim, so every sentence here is written to be read by a person and
by a model.

The names below are the only names a finding ever carries. The brief prints them, the strong
cell carries them as its reasons, and this file explains them. Nothing else is a finding.

## Free checks on the proof text

Six findings, decided from the proof description and its tier tag alone. No test code
is read and nothing runs, so they apply to a spec written before any code exists.
`no_expected_value`, `vague_verb`, `missing_trigger` and `tier_mismatch` keep a rule's
spec status at `drafted`. `implementation_coupling` and `happy_path_only` are advisory: a
rule can be legitimately positive-only, and a grep proof legitimately names a path.

**`no_expected_value`.** The description names no literal, number, quoted string,
backticked token or named constant, so almost any assertion satisfies it. "Verify the
parser handles the id" passes against a test that asserts nothing in particular. Name
the value: the status code, the string, the count.

**`vague_verb`.** The description says "works", "correctly", "properly", "as expected"
or "successfully" with no value beside it. A proof should read straight into a test
without interpretation. Replace the verb with the observation.

**`missing_trigger`.** Nothing runs before the assertion, so the proof reads an
artifact that exists whether or not the code is right. Name the call, the request, the
render or the grep that produces what you then assert on.

**`tier_mismatch`.** An `@e2e` proof is described as a function call. An `@e2e` proof
must read as an observable flow: arrange, act, observe, through the real running app.
Either rewrite it as that flow or retag it to the tier it actually exercises.

**`implementation_coupling`.** The description names a private symbol, a CSS selector
or a source path instead of an observable outcome, so a refactor breaks the proof
without changing behaviour. Say what a person or a caller would see. A name that opens
with an underscore after a `/`, such as `specs/_anchors/` or `/_git/`, is a path or URL
segment and does not raise it.

**`happy_path_only`.** No proof of this rule names a rejection, an error or a
boundary. A rule that says reject, block, limit or expire has been proved in one
direction only. Add the case that trips the constraint.

## Free checks on the test body

Six findings, decided from the marked test body alone by `scripts/review/static_checks.py`.
They read the proof markers, locate each marked test, and report defects a reader can
see without running anything. A finding here is structural: no model judgment overrides
it, and no edit to the spec clears it. Only editing the test does.

**`no_assertion`.** The marked test body contains no assertion at all: no `assert`, no
`self.assert*`, no `pytest.raises`, no `expect()`, no `Assert.`. The test runs code and
checks nothing, so it passes whatever the code does.

**`tautology`.** The assertion cannot fail: `assert result is not None`,
`assert len(x) >= 0`, `expect(true).toBe(true)`, a `SELECT 'PASS'` nothing decides. The
test is true regardless of behaviour.

**`assert_true_literal`.** The narrower case of the same defect: the assertion is a
literal true, such as `assert True`, `self.assertTrue(True)` or `Assert.True(true)`.

**`bare_except`.** A bare `except:` or `except Exception:` followed by `pass` wraps the
code under test, so a failure is swallowed and the test passes through the bug.

**`logic_mirroring`.** The expected value is computed by the same function the test is
proving, so a bug in that function is confirmed rather than caught. Expected values
must be literal constants or come from an independent source.

**`mock_of_target`.** A patch target names the very behaviour the rule describes, so
the test replaces what it claims to prove. Mock the network, the clock and the
filesystem; never the code under test.

## What test strength says

Test strength is the share of deliberate breaks made to the code that the tests
caught, as an integer percent. It reads `test_strength` from the latest record, is
compared against `min_strength` from `.purlin/config.json`, and shows as `n/a` when no
engine ran.

It says one thing: the tests noticed when the behaviour changed. It does not say the
tests prove the right rule, that the proof text matches the test, or that the rule is
worth having. A rule can reach 90 percent strength on a proof that observes the wrong
thing, and a correct proof of a small rule can sit at 0 percent because nothing broke.
Read it beside the findings above, never instead of them.

## The two bars

A rule's **bar** is the evidence it must have before it can be signed: `passed` or `strong`.
A rule tagged `[bar: ...]` carries what it names; a rule with no tag takes the project's
gate, so `passed` at the gate `passed` and `strong` at `strong` and at `signed`. The bar is
read at `strong` and above; under `passed` it is never shown and it changes nothing.

**`passed`.** The tests are the evidence. The free checks and a passing run from either
source clear the bar, and the AI audit does not run on the rule at all. Under `signed` with
the default `sign_at: strong` the rule needs no signature: its signed cell carries `required`
false and the rule meets the gate on its tests.

**`strong`.** The strong cell is the evidence. Every blocking finding on the proof text must
be clear, the test body must carry no finding, the strength must reach `min_strength`, and
the AI audit must have run on the current rule, proof and test and settled. Until it has run
the strong cell reads `not audited`; where it ran and could not tell it reads `unsettled`.
Where no model could be reached the audit did not run at all, and the free checks and the
strength answer level 2 on their own.
The rule needs at least one proof that names a rejection, an error or a boundary, so
`happy_path_only` is blocking rather than advisory here. Under `signed` the rule needs a
current signature from someone on the signer list, whatever `sign_at` says.

`sign_at` widens that last requirement: `strong`, the default, asks for a signature on the
rules whose bar is `strong`, and `all` asks for one on every rule.

## Design rules

A rule tagged `[origin: design]` is read as a pair: the pinned mock from `designs/<feature>/`
beside the screenshot the test wrote to
`.purlin/runtime/attachments/<feature>/<PROOF-N>.png`. The brief shows both and runs a model
pre-compare that names what differs. Judge what a person would see: the text, the order, the
states present. A proof for a design rule that names a selector, a class or a pixel value is
`implementation_coupling`, and a new export of the mock stales the signatures of that anchor's
rules.

## Who is on Review, and who is on Sign

Two lists hold the rules whose next step is a person, and nothing else holds any.

**Review** exists at `strong` and above and holds the rules whose strong cell reads one of
three words: `manual test`, because the proofs are `@manual` and no test can be written;
`unsettled`, because the AI audit ran and could not tell; or `held`, because a person wrote
the case the test misses.

**Sign** exists at the gate `signed` and holds the **signable** rules: the ones that have
cleared their bar, need a signature, and do not have a counting one. Its rows read
`unsigned`, `stale` or `held`.

A rule blocked at its spec status or at its passed cell is on neither: it is build work and
it stays on the board. A weak rule is build work too, and so is a rule reading `not audited`,
whose next step is `purlin:audit` rather than a reader. Both lists read the rules whose bar
is `strong` first, then by feature and rule number.

## What the brief reports

The brief reports. It recommends nothing, and it never names a next action. Four things:

- **The strength, beside the minimum.** `Test strength: 71 percent (minimum 80)`, or
  `Test strength: n/a (minimum 80)` when no break engine ran.
- **The findings**, by the names above: the ones on the proof text, then the ones on the test
  body, each in one sentence naming the proofs it concerns.
- **The observations.** What the model review saw the test observe, against what the proof
  names, one sentence each. The model is asked to state what it saw and to say when it cannot
  tell. It is never asked what to do.
- **Whether it settled.** `Settled: yes` when the model could tell, `no` when it could not,
  and `not answered` when no AI audit ran. Anything but `yes` on a rule whose bar is `strong`
  makes the strong cell read `unsettled`. A review that settled and still observed something
  is a different answer: the model could tell, and what it saw is build work, so the cell
  reads `weak` with each observation sentence among its reasons.

A `@manual` proof has no test, so no free check on a test body runs and no AI audit is
asked for. Its strong cell reads `manual test` and its brief says so.

What a person does with the brief is one of four things, and `purlin:sign` takes each:

- **Sign it.** The test proves the proof. `purlin:sign <feature> RULE-N`.
- **Add a case.** The test is right as far as it goes and a case is missing, usually the
  rejection behind `happy_path_only`. Write the proof line; the next `purlin:build` writes the
  test for it.
- **Hold it.** No test written against this proof text could prove the rule, or this one does
  not. `purlin:sign <feature> RULE-N --hold "<the missing case>"` names what is missing.
- **Skip it.** Come back to it later. Nothing is written.
