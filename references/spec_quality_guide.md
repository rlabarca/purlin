# Spec quality guide

How to write a spec worth proving. For spec syntax, section names, id format and
metadata fields, see [references/formats/spec_format.md](formats/spec_format.md). For
bad-to-good rewrites taken from real projects, see
[references/rule_examples.md](rule_examples.md). For what the brief checks, and
what a signer checks after it, see
[references/review_criteria.md](review_criteria.md).

## Writing rules

### One claim, observable

A rule is one line saying what the software has to do. It makes one claim, and that
claim is observable: someone or something outside the code can watch it hold or fail.

- Bad: "Use bcrypt.compare for password verification"
- Good: "Return 401 when the password does not match the stored hash"

The first names the library. The second names what a caller sees, so a test can observe
it and a refactor cannot break it.

### The rebuild test

Every rule must pass one question: **if an engineer rebuilt this feature from only this
spec, would they get this wrong without this rule?**

If the answer is "no, they would figure it out" or "QA would catch it immediately", it
is not a rule. Cut it. This question comes before everything else: coverage, tags
and proof text are all wasted on a rule that does not earn its line.

Two more questions for every candidate rule:

- **Behaviour:** does this say what the feature does, or how the code does it? If it
  names a library, a hook, a CSS value or a token, rewrite it as the observable
  behaviour, or cut it.
- **Overlap:** would this rule always pass or fail together with another rule? If so,
  merge them.

### What a missing rule costs

| What a rebuild gets wrong | What goes wrong | Spec priority |
|---|---|---|
| Wrong behaviour | The engineer builds the wrong thing: wrong data source, wrong conditional gate, wrong calculation | Must be a rule. The rebuild produces wrong numbers. |
| Broken functionality | The feature works, then degrades under real conditions: crashes on missing data, one failure cascades | Must be a rule. An engineer would likely miss it. |
| Wrong layout | The feature is correct but unusable: content overlaps, controls are hidden | Should be a rule, proved by a flow through the running app or `@manual`. |
| Visual polish | Spacing, exact pixel values, animation timing, icon sizing | Not a rule. QA catches it. |

### Too few rules, too many rules

Signs of too few: data source fields unnamed, so the engineer pulls the wrong API
field; conditional gates missing, so content reaches the wrong user; no graceful
degradation, so the rebuild crashes on missing data.

Signs of too many: rules that describe implementation ("uses a `forEach` loop"); rules
that fix a CSS value that is polish rather than behaviour; two rules that always pass
or fail together; rules for behaviour that exists only in tests.

### Coverage

After the rebuild test, check the feature's contract boundaries. Data crossing a
boundary is what an engineer gets wrong, and the rule count scales with the feature:
there is no target.

- **Inbound:** API response fields by exact name, config and environment values, props
  and parameters, file contents, CLI arguments, webhook payloads.
- **Outbound:** analytics events with their names and shapes, calls to other services,
  database writes, file outputs, log entries.
- **Transformations:** field mappings with the exact name on both sides, calculations,
  formatters, filters, sorts, aggregations.
- **State:** the valid states, what triggers each transition, what is forbidden, what
  expires and when.
- **Access:** role and permission gates, feature flag conditions, switches that change
  behaviour.

Then the supporting dimensions: each distinct error response, boundary conditions such
as maximum lengths and retry limits, performance constraints, and what happens when a
dependency fails.

### The rule tag

One tag goes at the end of a rule line: `[level: passed|strong|signed]`. It says what the rule
must have to meet the gate, in the gate's own words: tests; tests and the audit; tests, the
audit and a signature. It is read at the `strong` gate and above: under `passed` it is never
asked for and changes nothing. A rule with no tag takes the project's gate, and a tag above the
gate is read as the gate. Tag `[level: passed]` where a passing test is the whole of what the
rule needs, and leave the tag off where the rule needs everything the gate asks for.

Tag rules as you write them: retagging a spec later is a separate pass over every line. A
signature logs the rule's level and does not lock it, so a re-tag stales no signature.

## Writing proofs

A proof is one line saying how a rule will be shown to hold: what is done, what is observed,
and the value that settles it. It is the plan a test carries out, so it is written before the
test and in words that a person who cannot read code can judge. QA writes proofs and reads
them, often from a draft AI wrote; a developer, or `purlin:build`, then writes the test that
carries each one out. This section is the one home of what a good proof is. The AI audit reads
every proof against it, with the checks in
[references/review_criteria.md](review_criteria.md).

Proofs are optional at the gate `passed`, where a rule's passing tests are the whole of its
evidence. From `strong` up every rule needs at least one proof, and a rule without one does
not meet the gate.

Each point below carries a pair: a poor proof, and the one that replaces it.

### What is done, what is observed, the expected value

Every proof names three things:

1. **What is done.** The input, the action, and any state set up first. Without it the proof
   reads something that exists whether or not the software is right.
2. **What is observed.** Where the result shows: a message on the screen, a response, a line a
   command prints, a file it writes, an exit code.
3. **The expected value.** The exact message, number, status or text that settles it. Without
   it almost any result satisfies the proof.

- Poor: "Verify the account lockout works."
- Good: "A wrong password is entered five times; the sixth attempt is refused with the message
  `Account locked`, and a correct password is refused too."

Name the setup when the outcome depends on it: "With the customer's currency set to USD, an
invoice raised in EUR shows its total in both currencies."

### At least one failure case or boundary

A rule that refuses, limits, blocks or expires anything is proved in both directions: the case
that is allowed goes through, and the case that is not is refused. A rule proved in one
direction only is half proved. Name the exact input at the edge, not only the outcome.

- Poor: "Exports of up to 10,000 rows succeed."
- Good, as two proofs: "An export of exactly 10,000 rows downloads a file of 10,001 lines, the
  header and 10,000 rows." and "An export of 10,001 rows is refused with the message `Exports
  are limited to 10,000 rows`, and no file is downloaded."

### Written for a person who cannot read code

A proof names what a user, or a caller of the system, would see. It carries no source or test
file path, no function name, no class, no selector and no name of a test framework. A QA lead,
a product manager or an auditor reads it and can say whether it shows the rule.

- Poor: "Call `InvoiceService.total()` with the fixture in `tests/data/two_lines.json`; assert
  `result.amount == 11000`."
- Good: "An invoice with two lines of 50.00 each and 10 percent tax shows a total of 110.00."

Where the thing under test has no screen, such as a file format, an API or a command's output,
the proof names the observable output in words and values, not the source that produces it. A
status code, a response field, an exit code, a printed line and a file the software writes are
all things a caller sees, and so is the path of that file.

- Poor: "Check the header constant in the CSV writer."
- Good: "The first line of an exported file reads `date,amount,currency`."

When the file is itself the product, such as a configuration template a project copies,
checking its text is the honest proof; word it as what a reader of that file finds: "A new
project's settings file carries `gate` set to `passed`", not "search the template for `gate`".

### Written before the test, and not about the test

The proof comes first and the test implements it. The proof does not describe the test's
mechanics: no call, no assertion, no mock, no fixture, no spy.

- Poor: "Call `parse()` with `invoice 42` and assert the result raises."
- Good: "An invoice id with a space in it is refused, and the message names the id."

The first is a test. The second is a proof, and any test that shows it will do.

### One proof, one thing shown

Each proof shows one thing, so a failure says which thing broke. Several proofs may serve one
rule, as the allowed case and the refused case do; one test may carry out several proofs.

- Poor: "Change the password, sign out, sign back in with the new password and check the
  activity log."
- Good, as three proofs: "After the password is changed, the old password is refused with
  `Wrong email or password`.", "After the password is changed, the new password signs in and
  the home page greets the user by name." and "Changing the password adds one entry to the
  account's activity page reading `Password changed`."

### Drafted by AI, read by a person

AI may draft a proof. The person whose name goes on the commit has read it against this page,
and checks three things in particular:

- **It would fail if the rule were broken.** Picture the software doing the wrong thing; the
  proof must say that something different would be seen.
- **Its expected value is a real value.** A message, a number, a status, a line of text.
  "Works correctly", "is handled properly" and "succeeds" are not values.
- **It does not simply restate the rule.** It adds the input, the action and what is seen.

- Poor, as drafted for the rule "A locked account refuses sign-in": "A locked account refuses
  sign-in correctly."
- Good: "An account locked by five wrong passwords is refused when the right password is
  entered, and the page reads `Account locked. Try again in 15 minutes.`"

### Proofs about what a person sees

Describe what is on the screen, never the markup. The test picks the tool.

- Poor: "Count the elements with class `basket-row`; verify the count is 3."
- Good: "With three different items in the basket, the basket page lists 3 rows and the total
  reads `42.50`."

No selectors, no class names, no element ids. A proof that says what is on the screen survives
a rewrite of the page.

### Flow proofs

A proof that goes through the running app reads as arrange, act, observe.

- **Arrange:** the state a user would meet: an account, a basket, the page to open.
- **Act:** what a person does: click, type, submit.
- **Observe:** what shows at a boundary: text on the screen, the request that left the app,
  what is kept after the flow.

- Poor: "Assert `loginRedirect` uses the `access_as_user` scope."
- Good: "Open the app, enter an email and choose Sign in; the redirect to the identity provider
  asks for the scope `access_as_user`; after signing in with a test account and reopening the
  app, the email field shows the email entered."

A proof about a flow that could hold without the app running does not describe the flow;
rewrite it. Name the flow, never the tool that drives it.

### The operating system

Add `@env(windows)`, `@env(macos)` or `@env(linux)`, at most one per proof, when the behaviour
can only be observed on one operating system: a file lock the system holds, a console's default
encoding, a filesystem that ignores case. Those three are the whole vocabulary. A proof with no
`@env` is satisfied by a run on any operating system.

## Manual proofs

A proof carries no tag when a test settles it, whatever that test needs to run:
`purlin:test` runs every tagged test of the features it runs. Human judgment, such as
visual polish, wording or brand voice, is the one case for `@manual`: "Read the error
messages against the brand voice guide @manual".

Source files under `views/`, `pages/`, `templates/` or `layouts/`, components with
layout logic, and code producing HTML are a signal that the proofs go through the running app
or are `@manual`. Where no test could observe what the proof names, the proof is `@manual`.

`@manual` means there is no test, so nothing can run and there is no test body for the AI
audit to read. The rule's strong cell reads `manual test` with the reason `manual proof`.
A signature file carrying a one-line note clears it, written by a person:
`purlin:sign <feature> RULE-N --note "<what you saw>"`. CI never writes that file, at
any level and under any gate. Use `@manual` where judgment is the only instrument,
and keep the rule's `> Scope:` tight: when a scope file changes, the signature goes
stale and someone must look again.

## When a rule is stuck

Find the rule in the status table, read the cell that blocks it, then read the row. The
gate decides how many cells exist: under `passed` only the first, under `strong` the first
two, under `signed` all three. A rule's level decides which of them block it.

| Cell | Word | What it means | What moves it |
|---|---|---|---|
| passed | `no test`, with `no proof written` | No proof line names the rule. What a proof is worth is the audit's question. | Write the proof under `## Proof` so it names a trigger and an expected value a test can reach. `purlin:spec`. |
| passed | `no test` | A proof names the rule and no test carries its marker comment. | `purlin:build` writes the test, then `purlin:test`. |
| passed | `failed` | A test for the rule failed. The reason names the file and the test. | Fix the code, or the test. See the next section. |
| passed | `not run` | Nothing has run the rule's tests yet. | Run `purlin:test`, which counts at every gate. |
| passed | `not run`, with `<os>: no run yet` | A proof carries `@env` and no current section from that operating system has passed it. | Run `purlin:test --remote`, whose matrix covers it, or drop the `@env` tag if any host could prove it. |
| passed | `partial` | The rule's tests passed on one operating system and failed or did not run on another. `partial` is not met. | Fix the platform that failed, or let the CI matrix run the one that has not. |
| passed | `out of date` | A pass exists but the spec, the code or the tests moved since; the reason names which. | Run the tests again; the next run clears it. |
| strong | `weak`, `strength N% under M%` | The tests did not notice when the behaviour was broken. | Add the case that tells the correct behaviour from the broken one. `purlin:build`, then `purlin:audit`. |
| strong | `weak`, with a sentence the model wrote | The AI audit settled the question and observed that the test does not read what the proof names. | Write the assertion the sentence asks for. `purlin:build`, then `purlin:audit`. |
| strong | `manual test` | The proof is `@manual`, so no test can be written and a person runs it. | `purlin:sign <feature> RULE-N --note "<what you saw>"`. |
| strong | `not audited` | The rule's level is `strong` or `signed` and no audit has read this rule, proof and test, so the evidence holds no audit entry for the current hashes. | `purlin:audit`, which writes the entry into the evidence. |
| strong | `weak`, `the AI audit could not decide: ...` | The AI audit ran and could not tell whether the test observes what the proof names. | `purlin:build`: make the proof or the test say plainly what is observed; the next `purlin:audit` reads the rule again. |
| signed | `unsigned` | No signature file for the current hashes, and the rule's level is `signed`, so it needs one. | `purlin:sign <feature> RULE-N`, which writes it in a signed commit. |
| signed | `stale` | The rule text, the proof text, the test body or what the audit found changed after the signature. | Read what changed, then sign again or fix what broke. |

## When a test fails, fix the code

There are three diagnoses, and the default assumption is the first.

| Diagnosis | What is wrong | Action |
|---|---|---|
| Code bug | The test asserts the correct behaviour and the code does not implement it. | Fix the code. The test is right. |
| Test bug | The test asserts the wrong thing: wrong status code, wrong field name, bad setup. | Fix the test. The code is right. |
| Spec drift | The rule no longer matches the intended behaviour. | Update the rule first, then the proof, then the test and the code. |

Never weaken an assertion to make a test pass (`assert status == 200` becoming
`assert status in [200, 401]`), never remove an assertion that was testing the right
thing, never change an expected value to match the actual value without finding out why
they differ, and never delete a failing test.

If you change **what** a test asserts rather than how, the proof text may be wrong.
Re-read it. The rule, the proof text, the assertion and the code must all agree; when
one disagrees, find out which before you go on. Narrowing the proof text to match a
weaker test is not a fix: it lowers the claim instead of strengthening the evidence,
and on a rule pinned from an anchor it is never allowed, because the anchor is an
upstream-owned contract. Silently changing an assertion to match actual behaviour is
the most common way an agent introduces a correctness bug.
