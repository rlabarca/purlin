# Getting started

For a developer putting Purlin on a project, who wants it to stay out of the way.

## What Purlin touches

- **A settings file, the specs and the evidence.** `purlin:init` writes `.purlin/config.json`,
  `.purlin/evidence/README.md`, an empty `specs/` and a few lines in `.gitignore`. It also
  copies the dashboard page, `purlin-report.html`, into the project, where git ignores it. It
  names every file it wrote, then asks whether it may commit them. On a yes it makes one
  commit, `chore(init): set up Purlin`.
- **One comment above a test.** `# purlin: cart PROOF-1` in Python, `// purlin: cart PROOF-1`
  in JavaScript, TypeScript or C#, `-- purlin: cart PROOF-1` in SQL. The comment ties the test
  to a proof, and the proof names its rule. The test itself does not change. Where a rule has
  no proof, the comment names the rule: `# purlin: cart RULE-1`.
- **Your own test command, in your own framework.** Setup leaves the `tests` setting empty. The
  first `purlin:test` suggests an entry for each test tool it recognises, with the flag that
  makes the tool write a report. The entries are written once you confirm them.
- **A commit when you ask for one.** A test run commits its results only with `--commit`.
  `purlin:spec` and `purlin:build` commit the spec and the code you asked them for.
- **Nothing running unless you ran it.** No git hook, no background job and no pipeline, and
  no Purlin process left running after a command ends.
- **Nothing added to your test suite.** No plugin, no import, no fixture. The one exception is
  the test tool's own: jest needs `jest-junit` to write its report. The first test run prints
  the command that installs it.

## Ten minutes

The path below starts in a Python project that holds no code yet. Its `pyproject.toml`
configures pytest. Each step shows what you type and the lines the step ends on. The rules and
tests the model writes are your own and differ from run to run, so this page shows none of
them.

**1. Install.** Purlin needs git, Python 3.9 or later, and
[Claude Code](https://docs.anthropic.com/en/docs/claude-code).

```bash
cd my-project
claude plugin marketplace add https://github.com/rlabarca/purlin.git --scope project
claude plugin install purlin@purlin --scope project
```

The two `claude` lines name the marketplace in the project's `.claude/settings.json` and turn
the plugin on for this project. Start Claude Code in the project, or run `/reload-plugins` in
a session that is already open. The `purlin:` commands are there.

**2. Set up.** Type `purlin:init`. It names each file it wrote, kept or copied, one per line,
then asks one question:

```text
wrote .purlin/
wrote specs/
wrote .purlin/config.json
wrote .gitignore
wrote .purlin/evidence/
wrote .purlin/evidence/README.md
copied scripts/report/purlin-report.html to purlin-report.html
Commit the files setup wrote? [y/N] 
```

Answer yes. It commits them and names the commit and each file in it:

```text
Committed e1a0b21, the files setup wrote:
  .purlin/config.json
  .gitignore
  .purlin/evidence/README.md
```

`purlin:init --yes` commits setup's files whenever they are not committed yet.

The settings file holds two things. `version` is the Purlin that set the project up. `tests`
is your test commands, empty until the first test run.

In a project that already holds code, `purlin:spec-from-code` reads it once and writes the
specs that code already implies.

**3. Write the rules.** Type `purlin:spec cart` and say what the cart must do: a sentence, a
ticket or a list of criteria.

A **rule** is one line saying what the software must do. A **proof** says how that is shown, in
words a person who cannot read code can judge.

`purlin:spec` prints the rules and proofs it drafted for you to read. It writes them to
`specs/<category>/cart.md`, with a `> Scope:` line naming the files the code lives in. Once you
agree, it commits the spec and ends on:

`Spec saved: cart. Next: purlin:build cart`

**4. Build.** Type `purlin:build cart`. It writes the code into the files `> Scope:` names. It
writes a test for each proof, with one comment above each test naming the proof. Where a test
you already have shows the proof, it adds the comment there and writes no new test. It commits
them, with a body saying which rule each change serves, and runs `purlin:test cart`.

The first test run in a project has no test command to run. It runs nothing and suggests an
entry for each test tool it recognises. Then it prints the whole setting on one line,
`Suggested tests setting: [...]`:

```text
No test command is set in .purlin/config.json, so nothing ran.
Suggested for pytest: python3 -m pytest {files} --junitxml={report}
```

Your project may run its tests another way, with another interpreter or other options. The
agent shows you the difference, then asks
`Write this tests setting to .purlin/config.json and commit that file? [y/N]`. On your yes the run writes the setting,
commits the settings file alone, and runs the tests. The results then name a commit that holds
the command they were taken with. It prints:

```text
Wrote the tests setting to .purlin/config.json.
Committed a1b2c3d, the work these results describe:
  .purlin/config.json
Running pytest: python3 -m pytest tests/test_cart.py --junitxml=.purlin/runtime/reports/pytest.xml

Markers: 3 tied to a test, 0 not tied.
Ran pytest on 1 feature.

Evidence written to .purlin/evidence/local/cart.json.
```

and then the status of every rule, which is what it ends on:

```text
Purlin status: shop, plugin 0.10.0
Tests: not met
Sign-off: not signed

Spec  Rules  Proofs  Tests
───────────────────────────
cart  3      3       3 of 3
───────────────────────────

3 rules. 3 pass their tests.
Left to do:
  1 feature whose results are not committed: purlin:test --commit
```

Every rule passes. The tests read `not met` for one reason: the results are on disk and not in
git. `purlin:test --commit` commits the work and its evidence:

```text
Evidence committed.

Purlin status: shop, plugin 0.10.0
Tests: met
Sign-off: not signed

Spec  Rules  Proofs  Tests
───────────────────────────
cart  3      3       3 of 3
───────────────────────────

3 rules. 3 pass their tests.
Every rule passes its tests on the committed evidence. Optional: sign this version with purlin:sign
```

Where the first run recognises no test tool, it prints:

```text
No test command is set and no test tool Purlin knows was found, so nothing ran. The agent reads the project and proposes a command for you to confirm.
```

[supported_frameworks.md](../references/supported_frameworks.md) lists the test tools it
recognises and the entry it suggests for each.

**5. Read it.** The three opening lines name the project and state the two facts. The project's
name is read from `pyproject.toml`, `package.json` or a `.csproj` file, then from the remote's
name, then from the folder's.

- `Tests: met` means every rule's tests pass on the committed evidence.
- `Sign-off: not signed` means nobody has signed this code. Signing is optional. The last
  line names the command that does it.
- `3 rules. 3 pass their tests.` says how many rules there are and how many passed their
  tests.

Open `purlin-report.html` in a browser to see each rule on its own line. It reads the results
of the last command.

When a test fails, the run names the rule and the test. Here it is the test of `RULE-2`:

```text
cart RULE-2 fails: tests/test_cart.py::test_sum. Run purlin:build cart.
```

It ends on what is left to do, and exits 1:

```text
3 rules. 2 pass their tests.
Left to do:
  1 rule to fix: purlin:build
```

Change `src/cart.py` and run `purlin:test` again. Every rule of `cart` is out of date until its
tests run over the new code. The run's first line says why it picked the feature, and names the
commit the last run saw: `Selected 1 of 1 feature: cart (code changed since <sha7>).` Run it
once more with nothing changed and it runs nothing. The status follows, as after every run:

```text
Nothing to run: every feature's spec, code and tests match its evidence. purlin:test --clean runs them anyway.

Purlin status: shop, plugin 0.10.0
Tests: not met
Sign-off: not signed

Spec  Rules  Proofs  Tests
───────────────────────────
cart  3      3       3 of 3
───────────────────────────

3 rules. 3 pass their tests.
Left to do:
  1 feature whose results are not committed: purlin:test --commit
```

That is the whole loop: a rule, a test, and whether the test passed over the code as it is now.

## The day to day

- `purlin:drift` says what your last pull, merge, rebase or checkout brought in: rules and
  proofs added and changed, numbers written twice, test comments to correct, anchors behind
  their source.
- `purlin:spec <name>` turns a requirement into rules and proofs.
- `purlin:build <name>` writes the code and the tests, or marks a test you already have.
- `purlin:test` runs what changed: the features whose spec, code or tests changed since their
  last run, and those with no run on this operating system. `purlin:test <feature>` runs one
  feature. `purlin:test --all` covers every feature: it runs what changed, slow tests
  included, and carries the rest forward.
- `purlin:audit` asks whether the tests would catch a bug, when you want to know.

A run writes `.purlin/evidence/local/<feature>.json`: what the run saw for each rule on this
operating system. `purlin:test --commit` makes two commits under your own git identity:

1. The specs, the marked tests and the settings the results describe, as
   `purlin: specs, tests and settings for <feature>`.
2. The evidence, as `purlin: evidence at <sha7>`, naming the first.

It never pushes. The push is yours.

Every run ends on the status. The first line of `Left to do` is the next step and names its
command.

[running-and-evidence.md](running-and-evidence.md) covers a run in full, including how a
project tests on another operating system.

## When the tests are met

**Signing is optional.** `purlin:sign` is there for any project, whenever it chooses. It reads
the committed evidence, builds the evidence package for the version, and stops at each hand
check. Then it takes one signature in a signed commit. The first sign-off writes the signed tag
`signed/<version>`. A project that never signs keeps its evidence all the same.
[sign-off.md](sign-off.md) is the walk in full.

**The audit is a tool you run when you want it.** `purlin:audit` runs heuristic spot tests over
your tests. Then, for each proof, an AI writes the one small bug that proof's test is most
likely to miss. The bug goes into a copy of the project, and the proof's own test runs. A
surviving bug is shown with the case the AI says it breaks. A caught bug and no finding make
the rule `strong`. A finding makes it `weak`, left to do as `to strengthen`. `purlin:build`
strengthens the test and settles the finding with a test run.
Nothing waits on it. [audit.md](audit.md) says what it checks and why.

## Where to go next

- The model in one page: [how-purlin-works.md](how-purlin-works.md).
- A team of product, developers and QA: [working-together.md](working-together.md).
- The sign-off, QA's path to it, and a regulated system: [sign-off.md](sign-off.md).
- Every command: [purlin_commands.md](../references/purlin_commands.md).
