# Rule examples from real projects

Bad-to-good rule rewrites collected from spec reviews and from what the audit observed. Organized by the five coverage categories in the [spec quality guide](spec_quality_guide.md), "Coverage", then worked proofs about what an AI does. This file grows over time: when a bad rule is caught and rewritten, add the pair here.

---

## Inbound contracts

Rules about data entering the system: API responses, config, props, messages. What goes wrong first: wrong field names mean wrong data on screen or in storage.

### tca-frontend: Mortgage Report Data (2026-04)

```
Bad:  "MortgageReport type defines the raw API response shape including AnalysisContact and report metadata"
Good: "API field user.LogoFileName maps to header logo (via formatImageUrl); user.FirstName + ' ' + user.LastName maps to contact display name"
Why:  The API uses lowercase 'contact' not 'AnalysisContact', 'user' not 'User'. Without exact field names, a rebuild wires to wrong fields.

Bad:  "Fetches report data from the API"
Good: "GET /EdgeMobileService/EdgeService.svc/json/GetAnalysisGuidDisplay with params {contactId, isFirstTime, position, isDetails, historyId, updateDate} returns full report directly"
Why:  Missing the service path prefix and query params means a rebuild can't even call the API correctly.

Bad:  "Hero calls useProductQuery hook"
Good: "Hero displays product.address, product.loanAmount, and product.rate from GET /api/products/:id"
Why:  Hook name is implementation. Data fields are what a developer needs to wire correctly.
```

## Outbound contracts

Rules about data leaving the system: analytics events, API calls out, database writes, log entries.

### tca-frontend: Analytics Integration (2026-04)

```
Bad:  "Sends analytics events on key interactions"
Good: "Fires Firebase event 'report_viewed' with params {reportId, reportType, contactId} when report page loads"
Why:  Without event name and param shape, analytics dashboards break on rebuild.

Bad:  "Tracks user behavior with TrustEngine"
Good: "TrustEngine pixel fires on page load, polling at 100ms intervals for max 50 attempts until container element exists"
Why:  Polling strategy and retry limits are behavioral: affects whether analytics actually fires.

Bad:  "Logs errors"
Good: "API fetch failures log {endpoint, statusCode, errorMessage} at warn level; do not surface to user"
Why:  Log shape matters for monitoring dashboards. 'Do not surface' is a UX constraint.
```

## Transformations

Rules about logic that converts between inbound and outbound: field mappings, formulas, formatters.

### tca-frontend: Data Builders (2026-04)

```
Bad:  "Formats data for display"
Good: "formatImageUrl prepends CDN base URL to user.LogoFileName; returns empty string if null"
Why:  The null handling and URL construction are both behavioral: a rebuild without this shows broken images.

Bad:  "Builds mortgage data from API response"
Good: "Header logo comes from formatImageUrl(user.LogoFileName), not contact.CompanyLogo. Contact name from user.FirstName + user.LastName, not a single ContactName field."
Why:  Field source matters. The API has multiple name-like fields: picking the wrong one shows wrong data.

Bad:  "Loan details uses product.fields array"
Good: "Loan details renders product.fields filtered by excluded=false, sorted by field.order"
Why:  Without filter/sort spec, a rebuild shows all fields in wrong order.

Bad:  "Calculates monthly payment"
Good: "Monthly payment = principal * (rate/12) / (1 - (1 + rate/12)^-term); displayed as currency with 2 decimal places"
Why:  The formula is the behavior. Getting it wrong means wrong financial numbers shown to users.
```

## State

Rules about feature lifecycle: valid states, transitions, timeouts.

### tca-frontend: Recording Session (2026-04)

```
Bad:  "Has multiple recording states"
Good: "Recording lifecycle: idle → recording → paused → stopped. Cannot go from stopped back to recording without reinitializing."
Why:  Missing transitions mean a rebuild allows invalid state changes.

Bad:  "Polls for updates"
Good: "Analysis polling: starts on mount at 5s intervals, pauses when tab hidden, resumes on tab focus, stops on unmount or when analysis complete"
Why:  Tab visibility and cleanup behavior prevent resource leaks and stale data.
```

## Access

Rules about who can see or do what: permissions, flags, views.

### tca-frontend: Report Access (2026-04)

```
Bad:  "Checks user permissions"
Good: "Password-protected reports show password form; authenticated reports show content directly. Password validated against GET /ValidatePassword endpoint."
Why:  The kind of protection (password vs auth) and validation endpoint are both behavioral.

Bad:  "Has a loan officer view"
Good: "The loan officer view (activated by the lo=true URL hash param OR the lo cookie) shows editable benefit fields and a save button; it merges the loan officer overrides with the base report data"
Why:  Activation mechanism (hash + cookie) and data merging are both things a rebuild would get wrong.

Bad:  "Uses feature flags"
Good: "Feature flag 'ai_chat_enabled' controls AI chat widget visibility; evaluated at render time via Split SDK"
Why:  Flag name and evaluation timing matter: wrong flag name means wrong feature toggling.
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
needs judgment, so PROOF-6 is graded, and its sentence says all the grader needs: it is shown
the reply and the files the session wrote, not the request. The test makes one output, then
asserts `grade` exits 0.

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

## Implementation details are not rules

These describe *how* code works, not *what* it does. They fail the rebuild test: a developer using a different technique would still produce correct behavior.

```
"Uses useMediaQuery hook with 768px breakpoint"     -- names the hook, not the behavior
"Hero background uses var(--surface-primary)"        -- names the token, not the behavior
"SVG elbow connector uses rx={h/2} path formula"     -- names the technique
"Info bar has margin-top: -66px"                     -- CSS pixel value, visual polish
"Stats grid uses CSS Grid with 3 columns"            -- names the layout technique
"Each accordion is a separate component"             -- component structure, not behavior
"Has error boundary around chart"                    -- error handling technique, not outcome
```

When implementation causes a **behavioral** problem, the problem is a rule and the technique is not:

```
"Stat cards remain usable (no overlap, no hidden content) on viewports below 768px"  -- rule (behavioral)
"Section colors follow the active theme"                                              -- rule (behavioral)
"Missing chart data shows 'No data available' message instead of crashing"            -- rule (behavioral)
```

---

<!-- Add new project examples below. Format: ### project-name: Feature (YYYY-MM) under the relevant category -->
