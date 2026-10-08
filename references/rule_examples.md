# Rule examples from real projects

Worked rules and proofs. One bad-to-good rewrite of a rule for each of the five coverage
categories in the [spec quality guide](spec_quality_guide.md), "Coverage", then worked proofs
about what an AI does. A good rule names what a caller or a user sees: a field, an endpoint, an
event, a value. It names no hook, library, SDK or function from inside the code.

## Inbound contracts

Data entering the system: API responses, config, props, messages.

```
Bad:  "Hero calls useProductQuery hook"
Good: "Hero displays product.address, product.loanAmount, and product.rate from GET /api/products/:id"
Why:  The hook's name is implementation. The endpoint and the exact field names are what a rebuild wires wrongly.
```

## Outbound contracts

Data leaving the system: analytics events, API calls out, database writes, log entries.

```
Bad:  "Sends analytics events on key interactions"
Good: "Sends the analytics event 'report_viewed' with params {reportId, reportType, contactId} when the report page loads"
Why:  Without the event name and the shape of its params, analytics dashboards break on a rebuild.
```

## Transformations

Logic that converts between inbound and outbound: field mappings, formulas, formatters.

```
Bad:  "Calculates monthly payment"
Good: "Monthly payment = principal * (rate/12) / (1 - (1 + rate/12)^-term); displayed as currency with 2 decimal places"
Why:  The formula is the behaviour. Getting it wrong shows users wrong financial numbers.
```

## State

Feature lifecycle: valid states, transitions, timeouts.

```
Bad:  "Has multiple recording states"
Good: "Recording lifecycle: idle → recording → paused → stopped. Cannot go from stopped back to recording without reinitializing."
Why:  Missing transitions mean a rebuild allows invalid state changes.
```

## Access

Who can see or do what: permissions, flags, views.

```
Bad:  "Has a loan officer view"
Good: "The loan officer view (activated by the lo=true URL hash param OR the lo cookie) shows editable benefit fields and a save button; it merges the loan officer overrides with the base report data"
Why:  How the view is activated and how its data is merged are both things a rebuild would get wrong.
```

## Implementation details are not rules

A rule that names a technique fails the rebuild test: a developer using another technique
would still produce correct behaviour. Where the technique prevents a problem a user would
see, the problem is the rule.

```
Bad:  "Stats grid uses CSS Grid with 3 columns"
Good: "Stat cards remain usable (no overlap, no hidden content) on viewports below 768px"
Why:  The layout technique is not a rule. What stays usable, and where, is.
```

## AI proofs

Worked proofs about what an AI does, each with the outline of its test. The three kinds of
check are in the [spec quality guide](spec_quality_guide.md), "A proof about what an AI does",
and the helper's commands are in [purlin_commands.md](purlin_commands.md), "The helper". The
tests are pytest; a test in any language starts the helper the same way.

Every test below shares one opening. It skips where `PURLIN_AI` is not set, so the suite's own
pass and a developer's own run reach no model:

```python
import os
import re
import subprocess
import sys

import pytest

HELPER = os.environ.get('PURLIN_AI')
HERE = os.path.dirname(os.path.abspath(__file__))
needs_the_helper = pytest.mark.skipif(
    not HELPER, reason='an AI proof: purlin:test --all starts it')


def helper(*arguments):
    return subprocess.run([sys.executable, HELPER] + list(arguments),
                          capture_output=True, text=True, encoding='utf-8')


def output(*arguments):
    """The folder `run` or `record` printed."""
    ran = helper(*arguments)
    assert ran.returncode == 0, ran.stderr
    return ran.stdout.strip()


def reply(folder):
    with open(os.path.join(folder, 'reply.md'), encoding='utf-8') as handle:
        return handle.read()
```

### An exact check of a prompt

```
- RULE-2: The triage prompt's reply names every finding of the report by its id
- PROOF-4 (RULE-2): With the sample report of three findings, the reply names `F-101`, `F-102` and `F-103` and no other id @ai(claude-opus-5-5)
```

```python
# purlin: triage_prompt PROOF-4
@needs_the_helper
def test_the_reply_names_the_three_findings_and_no_other():
    folder = output('run',
                    '--instructions', os.path.join(HERE, '..', 'prompts', 'triage.md'),
                    '--input', os.path.join(HERE, 'samples', 'report.md'))
    assert sorted(set(re.findall(r'F-\d+', reply(folder)))) == [
        'F-101', 'F-102', 'F-103']
```

Why: the proof names the sample and the three ids, so the test holds the whole set. A test
that looked for one id would pass on a reply that dropped two.

### A graded check of a skill

```
- RULE-3: The refund skill refuses a refund over the limit without blaming the customer
- PROOF-5 (RULE-3): Asked for a refund of 900.00 with the limit at 500.00, the reply refuses and names `500.00` @ai(claude-opus-5-5)
- PROOF-6 (RULE-3): Asked for a refund over the limit, the reply refuses, gives the limit as the reason and blames nobody @ai(claude-opus-5-5) @graded(claude-haiku-4-5-20251001)
```

```python
# purlin: refund_skill PROOF-6
@needs_the_helper
def test_the_refusal_blames_nobody():
    output('run',
           '--skill', os.path.join(HERE, '..', 'skills', 'refund'),
           '--project', os.path.join(HERE, 'samples', 'shop'),
           '--say', 'Refund order 1042 in full: 900.00.')
    graded = helper('grade', '--feature', 'refund_skill', '--proof', 'PROOF-6')
    assert graded.returncode == 0, graded.stdout + graded.stderr
```

Why: the amount is a value, so PROOF-5 checks it exactly, in a test of its own. Who is blamed
needs judgment, so PROOF-6 is graded, and its sentence is the whole criterion. The test makes
one output, then asserts `grade` exits 0.

### A graded check against the input

```
- RULE-2: The summary skill states nothing the report does not hold
- PROOF-3 (RULE-2): The summary states no fact the sample report does not hold @ai(claude-opus-5-5) @graded(claude-haiku-4-5-20251001)
```

```python
# purlin: summary_skill PROOF-3
@needs_the_helper
def test_the_summary_states_no_fact_the_report_does_not_hold():
    output('run',
           '--skill', os.path.join(HERE, '..', 'skills', 'summary'),
           '--project', os.path.join(HERE, 'samples', 'lab'),
           '--say', 'Summarise report.md.')
    graded = helper('grade', '--feature', 'summary_skill', '--proof', 'PROOF-3')
    assert graded.returncode == 0, graded.stdout + graded.stderr
```

Why: no test can list every fact a summary might invent, so the proof is graded. The grader is
shown what the AI was given, the message and the sample holding `report.md`, beside what it
produced, so the sentence can compare the two. The sentence is still the whole criterion: the
input is what the output is checked against, never a second set of rules.

### An output the project makes its own way

```
- RULE-4: The summary the service returns is at most three sentences
- PROOF-7 (RULE-4): With the sample ticket, the summary the service returns holds at most 3 sentences @ai(claude-sonnet-5-5)
```

```python
# purlin: summary_service PROOF-7
@needs_the_helper
def test_the_summary_is_at_most_three_sentences(tmp_path):
    summary = summarise(ticket('samples/ticket.md'),
                        model=os.environ['PURLIN_AI_MODEL'])
    (tmp_path / 'reply.md').write_text(summary, encoding='utf-8')
    folder = output('record', '--from', str(tmp_path))
    assert len(re.findall(r'[.!?](?:\s|$)', reply(folder))) <= 3
```

Why: the project builds its prompt in code and calls the model with its own key, so the test
makes the output and hands it over with `record`. It reads `PURLIN_AI_MODEL` to ask the model
the proof names, and asserts on the folder `record` printed, never on its own copy, so the
audit can hand it a wrong output.
