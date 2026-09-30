# Getting started

For a developer putting Purlin on a project, who wants it to stay out of the way.

## What Purlin touches

- **A settings file, the specs and the evidence.** `purlin:init` writes `.purlin/config.json`,
  `.purlin/evidence/README.md`, an empty `specs/`, a block in `.gitignore`, and a copy of the
  dashboard, `purlin-report.html`, which that block keeps out of git. It prints every file it
  wrote, then asks whether it may commit them. On a yes it commits them in one commit,
  `chore(init): set up Purlin at the gate <gate>`.
- **One comment above a test.** `# purlin: cart PROOF-1` in Python, `// purlin: cart PROOF-1`
  in JavaScript, TypeScript or C#, `-- purlin: cart PROOF-1` in SQL. The comment ties the test
  to a proof, and the proof names its rule. Where a rule has no proof, the comment names the
  rule: `# purlin: cart RULE-1`.
- **Your own test command, in your own framework.** Setup leaves the `tests` setting empty. The
  first `purlin:test` suggests an entry for each test tool it recognises, with the flag that
  makes the tool write a report Purlin reads, and the entries are written once you confirm
  them. For pytest the command is `python3 -m pytest --ignore=mutants {files} --junitxml={report}`,
  starting `py -3` on Windows.
- **A commit when you ask for one.** A test run writes its results and commits them only with
  `--commit`. `purlin:spec` and `purlin:build` commit the spec and the code you asked them for.
- **Nothing running unless you ran it.** No git hook, and no Purlin process left running after
  a command ends. A runner file for the git host is written for one reason: a proof tagged
  `@env` for an operating system this machine is not.
- **Nothing added to your test suite.** No plugin, no import, no fixture. The one exception is
  the test tool's own: jest needs `jest-junit` to write its report, and the first test run
  prints the command that installs it.

## Ten minutes

The path below starts in a Python project whose `pyproject.toml` configures pytest and that
holds no code yet. Each step shows what you type and the lines the step ends on. The rules and
tests the model writes are your own and differ from run to run, so this page shows none of
them.

**1. Install.** Purlin needs git, Python 3.9 or later, and
[Claude Code](https://docs.anthropic.com/en/docs/claude-code).

```bash
cd my-project
claude plugin marketplace add https://github.com/rlabarca/purlin.git --scope project
```

Then, inside Claude Code, run `/plugin install purlin@purlin` and `/reload-plugins`.

**2. Set up.** Type `purlin:init`. It asks up to three things:

- the gate, `What must be true of every rule before a version is finished?`, with the choices
  `passed` and `signed`. Answer `passed`.
- at `signed` only, and only where a tool that can do it exists for your test framework,
  whether to break the code on purpose to measure test strength.
- whether it may commit the files it wrote. Answer yes.

It names each file it wrote, copied or skipped:

<!-- sample: setup -->
```text
wrote .purlin/
wrote specs/
wrote .purlin/config.json
wrote .gitignore
wrote .purlin/evidence/
wrote .purlin/evidence/README.md
copied scripts/report/purlin-report.html to purlin-report.html
skipped the runner file (every test runs on this operating system, so nothing has to run remotely)
```

Then it commits them, names the commit and each file in it, and ends on the next step:

<!-- sample: setup -->
```text
  .purlin/config.json
  .gitignore
  .purlin/evidence/README.md

No specs found under specs/.
→ Run: purlin:spec <name> to write the first spec.
```

In a project that already holds code, the last line names `purlin:spec-from-code`, which writes
the specs that code already implies: [spec-from-code.md](spec-from-code.md).

**3. Write the rules.** Type `purlin:spec cart` and say what the cart must do: a sentence, a
ticket or a list of criteria. A **rule** is one line saying what the software must do, and a
**proof** says how that is shown, in words a person who cannot read code can judge. It prints
the rules and proofs it drafted for you to read, writes them to `specs/<category>/cart.md` with
a `> Scope:` line naming the files the code lives in, commits the spec once you agree, and
ends on:

`Spec saved: cart. Next: purlin:build cart`

**4. Build.** Type `purlin:build cart`. It writes the code into the files `> Scope:` names and a
test for each proof, with one comment above each test naming the proof, where no existing test
already shows it. It commits them, with a body saying which rule each change serves, and runs
`purlin:test cart`.

The first test run in a project has no test command to run. It runs nothing, suggests an entry
for each test tool it recognises, then prints the whole setting on one line,
`Suggested tests setting: [...]`:

<!-- sample: first-run -->
```text
No test command is set in .purlin/config.json, so nothing ran.
Suggested for pytest: python3 -m pytest --ignore=mutants {files} --junitxml={report}
```

Where your project runs its tests in another way, with another interpreter or other options,
the agent shows you the difference. Say yes to the entry you want: the agent writes it into
`.purlin/config.json` and runs the tests again. The run prints:

<!-- sample: confirmed-run -->
```text
Running the pytest suite.

Markers: 3 tied to a test, 0 not tied.
Ran pytest on 1 feature.

Evidence written to .purlin/evidence/local/cart.json.
```

and then the status of every rule, which is what it ends on:

<!-- sample: confirmed-run -->
```text
Spec  Rules  Proofs  Tests
───────────────────────────
cart  3      3       3 of 3
───────────────────────────

3 rules. 3 pass their tests.
Nothing left to do. To release a version: purlin:test --release
```

Where the first run recognises no test tool, which for pytest means no `conftest.py`, no
`pytest.ini`, no `[tool.pytest` section in `pyproject.toml` and no file named `test_*.py` under
`tests/`, it prints:

<!-- sample: no-tool -->
```text
No test command is set and no test tool Purlin knows was found, so nothing ran. The agent reads the project and proposes a command for you to confirm.
```

[supported_frameworks.md](../references/supported_frameworks.md) lists the test tools it
recognises and the entry it suggests for each.

**5. Read it.** `3 rules. 3 pass their tests.` is the summary: how many rules there are and how
many passed their tests. `Nothing left to do.` means no rule has anything left, and the rest of
the line names how a version is released. Open `purlin-report.html` in a browser to see each rule on its own line; it reads the
results of the last run.

Where a test fails, here the test of `RULE-2`, the run names the rule and the test:

<!-- sample: failing-run -->
```text
cart RULE-2 fails: tests/test_cart.py::test_sum. Run purlin:build cart.
```

It ends on what is left to do, and exits 1:

<!-- sample: failing-run -->
```text
3 rules. 2 pass their tests.
Left to do:
  1 rule to fix: purlin:build
```

Change `src/cart.py` and run `purlin:test` again. Every rule of `cart` is out of date until its
tests run over the new code, and the run's first line says why it picked the feature,
`Selected 1 of 1 feature: cart (code changed since <sha7>).`, naming the commit the last run
saw. Run it once more with nothing changed and it runs nothing:

<!-- sample: commit-run -->
```text
Nothing to run: every feature's spec, code and tests match its evidence. purlin:test --all runs them anyway.
```

That is the whole of it at the gate `passed`: a rule, a test, and whether the test passed over
the code as it is now.

## The day to day

- `purlin:drift eng` says what your last pull, merge, rebase or checkout brought in: code that
  changed and the rules behind it, rules with no test, features out of date.
- `purlin:spec <name>` turns a requirement into rules and proofs.
- `purlin:build <name>` writes the code and the tests, or marks a test you already have.
- `purlin:test` runs the features the change touched: those whose spec, code or tests changed
  since their last run, and those with no run on this operating system. `purlin:test <feature>`
  runs one feature and `purlin:test --all` runs every feature.

A run writes two files: `.purlin/evidence/local/<feature>.json`, what the run saw for each rule
on this operating system, and `.purlin/tests.md`, one table for the project. `purlin:test
--commit` makes two commits under your own git identity: first the specs, the marked tests and
the settings the results describe, as `purlin: specs, tests and settings for <feature>`, then
the evidence, as `purlin: evidence at <sha7>`, naming the first. A teammate reads your run on
the git host without running anything. It never pushes; the push is yours.

Every run ends on the summary and `Left to do`. The first line of `Left to do` is the next step
and names its command; a project with nothing left ends on the release step,
`purlin:test --release`.

[running-and-evidence.md](running-and-evidence.md) covers a run in full, including the one
reason a project has a remote runner: a proof tagged for an operating system this machine is
not.

## When a team wants more

The gate says what a release asks. There are two:

| Gate | What a release must have | The commands |
|------|--------------------------|--------------|
| `passed` | every rule's tests pass at the release commit | `purlin:test --release` |
| `signed` | that, and a person's signature over the evidence package | `purlin:test --release`, then `purlin:sign` |

`purlin:test --release`, on a release branch, runs every test, commits the evidence and the
evidence package, and at `passed` tags the release `passed/<version>`. At `signed` a person walks
the package with `purlin:sign`, and the first sign-off writes the signed tag `signed/<version>`.

`purlin:audit` is a tool you run at either gate: a model reads each rule, its proofs and its
tests. A finding makes the rule `weak`, and it is left to do as `to strengthen`; nothing waits on
it, and the summary adds what the audit found only where it ran.

`purlin:init --gate signed` changes the gate. The specs, the tests and the evidence stay as they
are.

## Where to go next

- The model in one page: [how-purlin-works.md](how-purlin-works.md).
- A team of product, developers and QA: [team-workflow.md](team-workflow.md).
- The gate `signed`, when the software is signed off in a regulated system:
  [regulated-workflow.md](regulated-workflow.md).
- An existing codebase with no specs yet: [spec-from-code.md](spec-from-code.md).
- Every command: [purlin_commands.md](../references/purlin_commands.md).
