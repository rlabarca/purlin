# Getting started

For a developer putting Purlin on a project, who wants it to stay out of the way.

## What Purlin touches

- **A settings file and the specs you write.** `purlin:init` writes `.purlin/config.json`,
  `.purlin/evidence/README.md`, an empty `specs/`, a block in `.gitignore`, and a copy of the
  dashboard, `purlin-report.html`, which that block keeps out of git. It prints every file it
  wrote and commits none of them.
- **One comment above a test.** `# purlin: cart RULE-1` in Python, `// purlin: cart RULE-1` in
  JavaScript, TypeScript or C#, `-- purlin: cart RULE-1` in SQL. The comment is how Purlin ties
  a test to a rule.
- **Your own test command, in your own framework.** Init writes it into the `tests` setting,
  with the flag that makes the framework write a report, and Purlin reads that report. For
  pytest that is `python3 -m pytest --ignore=mutants {files} --junitxml={report}`.
- **Nothing committed unless you ask.** A run writes its results and commits them only with
  `--commit`. `purlin:spec` and `purlin:build` commit the spec and the code you asked them for.
- **Nothing running unless you ran it.** No git hook, no background job, no CI workflow unless
  a rule needs another operating system or you say you do not trust this machine.
- **Nothing installed in your test suite.** No plugin, no import, no fixture. The one
  exception is the framework's own: Jest needs `jest-junit` to write its report.
- **If you leave, the markers are comments.** Delete `.purlin/`, `specs/`,
  `purlin-report.html` and the `.gitignore` block, and your tests run exactly as they did.

## Ten minutes

**1. Install.** Purlin needs git, Python 3.9 or later, and
[Claude Code](https://docs.anthropic.com/en/docs/claude-code).

```bash
cd my-project
claude plugin marketplace add https://github.com/rlabarca/purlin.git --scope project
```

Then, inside Claude Code, run `/plugin install purlin@purlin` and `/reload-plugins`, and:

```
purlin:init
```

Answer `passed` to the first question, `What must be true of every rule before a version is
proven?`, `y` to `Do you trust your own machine for the tests and the signing?`, and the
default to anything else it asks. Init reads your test framework from the tree and ends with
`→ Next: run purlin:spec to write the first spec.`

**2. Write three rules.** One file, `specs/shop/cart.md`:

```markdown
# Feature: cart

> Description: The cart's total.
> Scope: src/cart.py

## Rules

- RULE-1: An empty cart totals 0
- RULE-2: The total is the sum of price times quantity
- RULE-3: A negative quantity is refused
```

`> Scope:` names the code the rules are about. `purlin:spec` writes the same file from a
sentence, if you would rather describe the feature than type it.

**3. Add one comment above each of three tests.** Tests you already have, or new ones:

```python
# purlin: cart RULE-1
def test_empty():
    assert total([]) == 0

# purlin: cart RULE-2
def test_sum():
    assert total([(2, 3), (1, 1)]) == 7

# purlin: cart RULE-3
def test_negative():
    with pytest.raises(ValueError):
        total([(2, -1)])
```

**4. Run one command.**

```
purlin:test
```

It runs your test command and prints:

```
Selected 1 of 1 feature: cart (no run on macos yet).

Running the pytest suite.
Markers: 3 tied to a test, 0 not tied.
Ran pytest on 1 feature.

Evidence written to .purlin/evidence/local/cart.json.

Purlin status: my-project, plugin 0.10.0, gate passed

Spec  Rules  Tests
───────────────────
cart      3  3 of 3
───────────────────

3 of 3 rules meet the gate passed.
Untested 0 · Failing 0 · Partial 0 · Passing 3.
1 feature.

→ Next: nothing is outstanding at gate passed.

gate passed: 3 of 3
```

**5. Read it.** `3 of 3` rules passed. A rule whose test fails is counted under `Failing`, and
the run ends `gate not met: 2 of 3` and exits 1. Open `purlin-report.html` in a browser to see
each rule on its own line.

Now change `src/cart.py` and run `purlin:test` again. Every rule of `cart` is out of date until
its tests run over the new code, and the run says why it picked the feature:

```
Selected 1 of 1 feature: cart (code changed since bf3709e).
```

Run it once more with nothing changed and it runs nothing: `Nothing to run: every feature's
spec, code and tests match its evidence. purlin:test --all runs them anyway.`

That is the whole of it at the gate `passed`: a rule, a test, and whether the test passed over
the code as it is now.

## The day to day

```
purlin:drift eng
purlin:spec <name>
purlin:build <name>
purlin:test
```

`purlin:drift eng` says what your last pull, merge, rebase or checkout brought in: code changed
and the rules behind it, rules with no test, features out of date. `purlin:spec` turns a
requirement into rules; `purlin:build` writes the code and the tests, or marks a test you
already have; `purlin:test` runs what the change touched. `purlin:test <feature>` runs one
feature and `purlin:test --all` runs everything.

A run writes two files: `.purlin/evidence/local/<feature>.json`, what the run saw for each rule
on this operating system, and `.purlin/tests.md`, one table for the project. `purlin:test
--commit` commits both as `purlin: evidence at <sha7>`, under your own git identity, so a
teammate reads your run on the git host without running anything. It never pushes; the push is
yours.

Every command ends with one `→ Next:` line naming the step to take. Follow it rather than
remembering an order.

[running-and-evidence.md](running-and-evidence.md) covers a run in full, including the one
case at this gate that needs a remote runner: a test that can only pass on another operating
system.

## When a team wants more

The gate is how far a project asks every rule to go. There are three:

| Gate | What every rule must have | The command |
|------|---------------------------|-------------|
| `passed` | its tests pass over the current code | `purlin:test` |
| `strong` | that, and an audit that found the tests sound | `purlin:audit` |
| `signed` | that, and a person's signature | `purlin:sign` |

From `strong` up each rule also carries a **proof**: a plain sentence saying how the rule is
shown, which QA writes or reviews and the audit checks the test against. The marker then names
the proof, `# purlin: cart PROOF-2`. `purlin:audit` calls a model on each rule and a finding
blocks. At `signed` a person signs each rule, and `purlin:sign` writes the signed tag
`signed/<version>` once every rule meets the gate.

`purlin:init --gate strong` raises the gate and asks before each write; it changes no rule.
A single rule can stay lower, `[level: passed]` at the end of its line.

## Where to go next

- The model in one page: [how-purlin-works.md](how-purlin-works.md).
- The gate `strong`, for a team: [team-workflow.md](team-workflow.md).
- The gate `signed`, when the software is signed off in a regulated system:
  [regulated-workflow.md](regulated-workflow.md).
- An existing codebase with no specs yet: [spec-from-code.md](spec-from-code.md).
- Every command: [purlin_commands.md](../references/purlin_commands.md).
