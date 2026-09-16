# Spec quality guide

How to write a spec worth proving. For spec syntax, section names, id format and
metadata fields, see [references/formats/spec_format.md](formats/spec_format.md). For
bad-to-good rewrites taken from real projects, see
[references/rule_examples.md](rule_examples.md). For what a reviewer or the review
brief checks once a rule has a test, see
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
is not a rule. Cut it. This question comes before everything else: coverage, tier tags
and proof text are all wasted on a rule that does not earn its line.

Two more questions for every candidate rule:

- **Behaviour:** does this say what the feature does, or how the code does it? If it
  names a library, a hook, a CSS value or a token, rewrite it as the observable
  behaviour, or cut it.
- **Overlap:** would this rule always pass or fail together with another rule? If so,
  merge them.

### What a missing rule costs

| Rebuild risk | What goes wrong | Spec priority |
|---|---|---|
| Wrong behaviour | The engineer builds the wrong thing: wrong data source, wrong conditional gate, wrong calculation | Must be a rule. The rebuild produces wrong numbers. |
| Broken functionality | The feature works, then degrades under real conditions: crashes on missing data, one failure cascades | Must be a rule. An engineer would likely miss it. |
| Wrong layout | The feature is correct but unusable: content overlaps, controls are hidden | Should be a rule, proved `@e2e` or `@manual`. |
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

### Rule tags

Three tags go at the end of a rule line: `[risk: high|medium|low]`,
`[origin: pm|design|qa|eng]` and `[criterion: <id>]`.

- **`risk`** says how much a wrong answer costs. It defaults to `low`, and it is read at
  the `strong` gate and above: under `passed` it is never asked for and changes nothing.
  It decides two things. `ai_review_at` says the risk at which the model review runs, and
  `sign_at` says the risk at which the signed cell needs a signature, so the tag decides
  who has to look at the rule.
- **`origin`** says who owns the rule. It defaults to `eng`. Drift routes a change by
  origin, so a PM sees their own rules move and an engineer sees theirs.
- **`criterion`** links the rule to an upstream acceptance criterion id. It has no
  default and nothing requires it; it exists so a PM can find the rule from the ticket.

Under the `signed` gate, `risk` and `origin` are required on every rule. Tag rules as
you write them: retagging a spec later is a separate pass over every line, and a risk
re-tag stales the rule's signature.

## Writing proofs

A proof description tells the agent exactly what to do and what to assert. It should
read straight into a test without interpretation. Five things make it one:

1. **A trigger.** Something runs before the assertion: a call, a request, a render, a
   grep. Without one the proof reads an artifact that exists whether or not the code is
   right.
2. **An expected value.** A literal, a number, a status code, a quoted string. Without
   one, almost any assertion satisfies the proof.
3. **A negative case.** When the rule says reject, block, limit or expire, one proof
   exercises the rejection. The accepted case alone proves the rule in one direction.
4. **A tier.** See "Tier assignment" below.
5. **An `@env` tag, when the operating system matters.** `@env(windows)`, `@env(macos)`
   or `@env(linux)`, at most one per proof. Those three are the whole vocabulary. Use
   it only when the behaviour genuinely cannot be observed elsewhere: a native file
   lock, a default console codec, a case-insensitive filesystem. A proof with no `@env`
   is satisfied by a record from any operating system.

Bad, because none of them names a value or a trigger:

```
- PROOF-1 (RULE-1): Test the login
- PROOF-1 (RULE-1): Verify authentication works
- PROOF-1 (RULE-1): Check error handling
```

Good:

```
- PROOF-1 (RULE-1): POST {"user": "alice", "pass": "wrong"} to /login; verify 401 with {error: "invalid_credentials"}
- PROOF-2 (RULE-2): Call resolve_config() with only config.json present; verify the returned dict matches config.json
- PROOF-3 (RULE-3): Grep src/ for eval(); verify zero matches
```

Include setup when the architecture matters:

```
- PROOF-4 (RULE-4): With PURLIN_PROJECT_ROOT set to /tmp/test, call find_project_root(); verify it returns /tmp/test without climbing directories
```

### Proofs about what a person sees

Describe what a person would see, never the DOM. The agent picks the tool.

Bad: "Count the table rows with class `fr`; verify the count is 8." Good: "Load the
dashboard with 3 features (3 of 3 strong, 2 of 6 passed, 0 of 4 untested); verify the
table shows 3 rows, the strength bars are filled proportionally, and the pills read
Strong, Passed and Untested; take a screenshot @e2e".

No selectors, no class names, no `querySelector`. The proof says what is on screen, so
it survives a refactor of the markup.

### `@e2e` proofs are flows

An `@e2e` proof reads as arrange, act, observe through the real running app.

- **Arrange:** seed the state a user would meet, navigate to a URL, stub an upstream
  response.
- **Act:** do what a person does: click, type, submit. Never "call function X".
- **Observe:** assert what is visible at a boundary: on-screen text, the outbound
  request that fired, the storage state after the flow. Never a source constant.

Bad: "Assert `loginRedirect` uses the `access_as_user` scope @e2e". That names an
internal function, so the test imports internals and asserts a declaration, which the
free checks report as `tier_mismatch`.

Good: "Open the app, enter an email, click Sign in; observe that the redirect to the
identity provider carries scope `access_as_user`; complete login with a test account;
verify `localStorage.loginEmail` equals the entered email. @e2e"

The tag and the description must agree in both directions. A proof tagged `@e2e` that
could pass without launching the app is mis-tagged; retag it. A proof that needs
rendering, routing or storage state after a flow and carries no tag is under-tagged;
tag it `@e2e`. Name the flow, never the runner: the description must be executable by
whatever end-to-end tooling the project has.

### Grep proofs

A grep-for-absence proof must be precise enough to miss comments, docstrings and
variable names that contain the keyword. Target the assignment pattern, not the keyword
on its own: `password\s*=\s*"[^"]*"` over `src/`, restricted to the source extensions
and with the test files excluded, rather than a bare search for `password`.

A grep proof of a structural rule is honest about what it checks. A spec where no proof
observes behaviour at all is the defect: when every proof of a spec is a grep or an
existence check, say so and offer behavioural rules for that same spec.

### Edge cases name their input

A boundary proof must name the exact input that triggers the edge case, not only the
expected output.

- Bad: "Verify the id parser rejects a malformed id"
- Good: "Call parse_id() with `RULE-`, the number missing; verify it raises ValueError
  naming the input"

## Tier assignment

Assign the tier by what the proof needs to execute. A proof with no tag is unit tier.

| What it needs | Tier | Example |
|---|---|---|
| Pure logic, memory only, or a grep over local files | none | Validate an input format, compute a hash, parse a config |
| A database, the network, the filesystem or an external service | `@integration` | An API roundtrip, a query, a file written and read back |
| A browser, the full stack or a rendered interface | `@e2e` | A login flow, a screenshot, a full page render |
| Human judgment: visual, wording, brand voice | `@manual` | Read the error messages against the brand voice guide |

When in doubt, tag `@integration`. A fast test carrying that tag is harmless; a slow
test with no tag blocks the unit tier. Tier tags are not optional: they decide which
tests run in which CI stage, so review them before you commit.

Source files under `views/`, `pages/`, `templates/` or `layouts/`, components with
layout logic, and code producing HTML are a signal that the proofs are `@e2e` or
`@manual`. Do not write an automated proof description for something that cannot be
automated.

### `@manual`

`@manual` means there is no test, so nothing can run and no free check on a test body
applies. The rule's strong cell reads `needs a person` with the reason `manual proof`.
A signature file carrying a one-line note clears it, written by a person:
`purlin:sign <feature> RULE-N --note "<what you saw>"`. CI never writes that file, at
any risk level and under any gate. Use `@manual` where judgment is the only instrument,
and keep the rule's `> Scope:` tight: when a scope file changes, the signature goes
stale and someone must look again.

## When a rule is stuck

Find the rule in the status table, read the cell that blocks it, then read the row. The
gate decides how many cells exist: under `passed` only the first two, under `strong` the
first three, under `signed` all four.

| Cell | Word | What it means | What moves it |
|---|---|---|---|
| spec | `drafted` | No proof line names the rule, or a blocking free check fires on the proof text: `no_expected_value`, `vague_verb`, `missing_trigger` or `tier_mismatch`. | Write or rewrite the proof under `## Proof` so it names a trigger and an expected value at a tier it can reach. `purlin:spec`. |
| passed | `no test` | The spec status is `ready` and no test carries the proof marker. | `purlin:build` writes the test, then `purlin:test`. |
| passed | `failed` | A test for the rule failed. The reason names the file and the test. | Fix the code, or the test. See the next section. |
| passed | `not run` | No record that counts under the gate exists, or the only record is a `developer` or `local` one and the gate is `strong` or above. The reason says which. | Push and let CI run, or `purlin:audit --remote`. |
| passed | `not run`, with `<os>: no record yet` | A proof carries `@env` and no record from that operating system has passed it. | Let the CI matrix run that job, or drop the `@env` tag if any host could prove it. |
| passed | `code changed` | A CI pass exists but the code moved since. | Nothing. CI clears it on the next run. |
| strong | `weak`, `strength N% under M%` | The tests did not notice when the behaviour was broken. | Add the case that tells the correct behaviour from the broken one. `purlin:build`, then `purlin:audit`. |
| strong | `weak`, with a finding name | A free check fired on the proof text or on the test body. `references/review_criteria.md` names each. | Rewrite the proof text, or the test body, whichever the finding concerns. |
| strong | `needs a person` | The proof is `@manual`, no brief exists for the current hashes, the model review could not settle, the model observed something, or a person holds the rule. The reason says which. | `purlin:sign` and answer the brief. A signature for the current hashes clears it. |
| signed | `unsigned` | No signature file for the current hashes, and the risk is at or above `sign_at`. | `purlin:sign <feature> RULE-N` as a signed commit from someone on the signer list. |
| signed | `stale` | The rule text, the proof text or the test body changed after the signature. | Read what changed, then sign again or fix what broke. |
| signed | `held` | A person committed a hold naming the missing case. | Add the case, then sign. A signature for the current hashes outranks the hold. |

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
