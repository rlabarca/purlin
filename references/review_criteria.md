# Review criteria

What the brief checks on one rule before a person reads it, and what a person checks after.
The brief runs these layers cheapest first and stops when it has enough for the rule's risk:
the free checks on the proof text, the free checks on the test body, the test strength from
the latest record, then a model review when the rule needs one. The brief builds that model
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

## The three risk levels

Risk is read at `strong` and above. Under `passed` it is never asked for, never shown and
never required, and a rule's risk tag changes nothing.

**`low`.** The free checks and a passing CI record are enough for the strong cell. Nobody has
to look unless a finding fires. Under `signed` with the default `sign_at: medium` a low-risk
rule's signed cell reads `not required`, so the rule meets the gate at strong.

**`medium`.** The model review runs when `ai_review_at` is `medium`, which is the derived
default under `signed`. Every blocking finding on the proof text must be clear and the test
body must carry no finding. Under `signed` with the default `sign_at: medium` the rule needs
a current signature from someone on the signer list.

**`high`.** The model review always runs, at every gate above `passed`. On top of the medium
requirements, the rule needs at least one proof that names a rejection, an error or a
boundary, so `happy_path_only` is blocking rather than advisory here.

Risk defaults to `low` when the rule carries no `[risk: ...]` tag. `ai_review_at` says the
risk at which the model review runs; `sign_at` says the risk at which a signature is required.

## Design rules

A rule tagged `[origin: design]` is read as a pair: the pinned mock from `designs/<feature>/`
beside the screenshot the test wrote to
`.purlin/runtime/attachments/<feature>/<PROOF-N>.png`. The brief shows both and runs a model
pre-compare that names what differs. Judge what a person would see: the text, the order, the
states present. A proof for a design rule that names a selector, a class or a pixel value is
`implementation_coupling`, and a new export of the mock stales the signatures of that anchor's
rules.

## What the brief reports

The brief reports. It recommends nothing, and it never names a next action. Four things:

- **The strength, beside the minimum.** `71% against a minimum of 80%`, or `n/a` when no break
  engine ran.
- **The findings**, by the names above: the ones on the proof text, then the ones on the test
  body, each in one sentence naming the proofs it concerns.
- **The observations.** What the model review saw the test observe, against what the proof
  names, one sentence each. The model is asked to state what it saw and to say when it cannot
  tell. It is never asked what to do.
- **Whether it settled.** `settled` is true when the model could tell, false when it could
  not, and absent when no model review ran. An unsettled review makes the strong cell read
  `needs a person`.

A `@manual` proof has no test, so no free check on a test body runs and no model review is
asked for. Its strong cell reads `needs a person` and its brief says so.

What a person does with the brief is one of four things, and `purlin:sign` takes each:

- **Sign it.** The test proves the proof. `purlin:sign <feature> RULE-N`.
- **Add a case.** The test is right as far as it goes and a case is missing, usually the
  rejection behind `happy_path_only`. Write the proof line; the next `purlin:build` writes the
  test for it.
- **Hold it.** No test written against this proof text could prove the rule, or this one does
  not. `purlin:sign <feature> RULE-N --hold "<the missing case>"` names what is missing.
- **Skip it.** Come back to it later. Nothing is written.
