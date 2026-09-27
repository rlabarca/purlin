# Review criteria

What the audit reads on one rule before a person does, and what a person reads after.
The brief gathers it in layers, cheapest first, and stops when it has enough for the rule's
bar: the hints free scans read off the proof text, the hints they read off the test body,
the test strength from the latest record, then the AI audit on every rule whose bar is
`strong`. The brief builds that model prompt from this file verbatim, so every sentence
here is written to be read by a person and by a model.

## The hints the audit reads

A hint is a sentence a scan wrote, and it is not a finding. Nothing a scan reads decides a
cell, keeps a rule at `drafted` or appears on the board: the hints go into the audit's
prompt beside the rule, the proof and the test body, marked `hint:`, and the audit says
what it observed. A settled audit that observed a gap leaves the strong cell reading
`weak` with its own sentence as the reason, so the audit's judgment is what carries the
hint. A scan cannot read a test, and a rule it flagged may be perfectly proved; that is
why the judgment is the audit's.

**Read off the proof description and its tier tag**, with no test code and nothing run, so
they apply to a spec written before any code exists:

- The description names no literal, number, quoted string, backticked token or named
  constant, so almost any assertion would satisfy it. "Verify the parser handles the id"
  passes against a test that asserts nothing in particular.
- The description says "works", "correctly", "properly", "as expected" or "successfully"
  with no value beside it. A proof should read straight into a test without interpretation.
- Nothing runs before the assertion, so the proof reads an artifact that exists whether or
  not the code is right. Name the call, the request, the render or the grep that produces
  what you then assert on.
- An `@e2e` proof is described as a function call. An `@e2e` proof must read as an
  observable flow: arrange, act, observe, through the real running app.
- The description names a private symbol, a CSS selector or a source path instead of an
  observable outcome, so a refactor would break the proof without changing behaviour. A
  name that opens with an underscore after a `/`, such as `specs/_anchors/` or `/_git/`,
  is a path segment and does not raise it.
- No proof of the rule names a failure or an edge case. A rule that says reject, block,
  limit or expire has been proved in one direction only.

**Read off the marked test body** by `scripts/review/static_checks.py`, which locates each
marked test and reports what a reader could see without running anything:

- The marked test body holds no assertion at all: no `assert`, no `self.assert*`, no
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
  claims to prove. Mock the network, the clock and the filesystem; never the code under test.

A rule's spec status reads `ready` when a proof line names it and `drafted` when none does.
Nothing else is read there: what a proof is worth is the audit's question, answered by a
model that read the test beside it.

## What test strength says

Test strength is the share of deliberate breaks made to the code that the tests
caught, as an integer percent. It reads `test_strength` from the latest record, is
compared against `min_strength` from `.purlin/config.json`, and shows as `n/a` when no
engine ran.

It says one thing: the tests noticed when the behaviour changed. It does not say the
tests prove the right rule, that the proof text matches the test, or that the rule is
worth having. A rule can reach 90 percent strength on a proof that observes the wrong
thing, and a correct proof of a small rule can sit at 0 percent because nothing broke.
Read it beside what the audit observed, never instead of it.

## The two bars

A rule's **bar** is the evidence it must have before it can be signed: `passed` or `strong`.
A rule tagged `[bar: ...]` carries what it names; a rule with no tag takes the project's
gate, so `passed` at the gate `passed` and `strong` at `strong` and at `signed`. The bar is
read at `strong` and above; under `passed` it is never shown and it changes nothing.

**`passed`.** The tests are the evidence. A passing run from either source clears the
bar, and the AI audit does not run on the rule at all. Under `signed` with the default
`sign_at: strong` the rule needs no signature: its signed cell carries `required` false and
the rule meets the gate on its tests.

**`strong`.** The strong cell is the evidence. The strength must reach `min_strength`, and
the AI audit must have run on the current rule, proof and test, observed nothing and
settled. Until it has run the strong cell reads `not audited`; where it ran and could not
tell it reads `unsettled`; where it settled and still observed something the cell reads
`weak` with that sentence as the reason. Where no model could be reached the audit did not
run at all, and the strength answers level 2 on its own. Under `signed` the rule needs a
current signature from someone on the signer list, whatever `sign_at` says.

`sign_at` widens that last requirement: `strong`, the default, asks for a signature on the
rules whose bar is `strong`, and `all` asks for one on every rule.

## Design rules

A rule tagged `[origin: design]` is read as a pair: the pinned mock from `designs/<feature>/`
beside the screenshot the test wrote to
`.purlin/runtime/attachments/<feature>/<PROOF-N>.png`. The brief shows both and runs a model
pre-compare that names what differs. Judge what a person would see: the text, the order, the
states present. A proof for a design rule that names a selector, a class or a pixel value
draws a hint saying so, and a new export of the mock stales the signatures of that anchor's
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

The brief reports. It recommends nothing, and it never names a next action. Three things:

- **The strength, beside the minimum.** `Test strength: 71 percent (minimum 80)`, or
  `Test strength: n/a (minimum 80)` when no break engine ran.
- **The observations.** What the AI audit saw the test observe, against what the proof
  names, one sentence each. The audit is asked to state what it saw and to say when it
  cannot tell. It is never asked what to do.
- **Whether it settled.** `Settled: yes` when the audit could tell, `no` when it could not,
  and `not answered` when no AI audit ran. `no` on a rule whose bar is `strong` makes the
  strong cell read `unsettled`; `not answered` does not, because nothing asked the question
  and the strength answers level 2 on its own. An audit that settled and still observed something
  is a different answer: it could tell, and what it saw is build work, so the cell reads
  `weak` with each observation sentence among its reasons.

The hints are printed beside the proof and the test they were read off, marked `hint:`, so
a person reading the brief sees what the audit was handed.

A `@manual` proof has no test, so nothing is scanned off a test body and no AI audit is
asked for. Its strong cell reads `manual test` and its brief says so.

What a person does with the brief is one of four things, and `purlin:sign` takes each:

- **Sign it.** The test proves the proof. `purlin:sign <feature> RULE-N`.
- **Add a case.** The test is right as far as it goes and a case is missing, usually the
  failure the rule's proofs never name. Write the proof line; the next `purlin:build` writes
  the test for it.
- **Hold it.** No test written against this proof text could prove the rule, or this one does
  not. `purlin:sign <feature> RULE-N --hold "<the missing case>"` names what is missing.
- **Skip it.** Come back to it later. Nothing is written.
