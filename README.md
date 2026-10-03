<p align="center">
  <img src="design/assets/logo.svg" alt="Purlin" width="360">
</p>

# Purlin

Purlin is a Claude Code plugin for spec-driven development. It shows, rule by rule, that your
software does what you said it must.

You write each requirement as a rule. One comment above a test ties the test to a rule. Purlin
runs your own test command and tells you which rules pass on the code as it is now.

Purlin keeps two things in your repository: the evidence of what the tests saw, and a person's
sign-off over it. It shows them as two facts, `Tests: met` and
`Sign-off: signed 0.1.0 at a1b2c3d`.

Purlin cannot prove your code is correct, and it makes no claim of compliance. Where sign-off
happens in a regulated system, Purlin's evidence package is an input to it.

## What it touches

- A settings file, the specs and the evidence: `.purlin/config.json`, `specs/`,
  `.purlin/evidence/` and a few lines in `.gitignore`. Setup also copies the dashboard page,
  `purlin-report.html`, into the project, where git ignores it.
- One comment above a test: `# purlin: cart PROOF-1`. The test itself does not change.
- Your own test command, in your own framework. The first test run suggests it, with the flag
  that makes it write a report, and you confirm it.
- A commit when you agree to one. Setup asks before it commits the files it wrote. The first
  test run commits the settings file once you confirm the test command. A test run commits its
  results only with `--commit`.
- Nothing running unless you ran it: no git hook, no background job and no pipeline, and no
  Purlin process left running after a command ends.
- Nothing added to your test suite.

## Install

You need git, Python 3.9 or later and
[Claude Code](https://docs.anthropic.com/en/docs/claude-code).

```bash
cd my-project
claude plugin marketplace add https://github.com/rlabarca/purlin.git --scope project
claude plugin install purlin@purlin --scope project
```

Start Claude Code in the project, or run `/reload-plugins` in a session that is already open.
The `purlin:` commands are there.

Coming from 0.9.5? See [docs/upgrading.md](docs/upgrading.md).

## Ten minutes

1. **Set up.** Type `purlin:init`. It names each file it wrote and asks one question,
   `Commit the files setup wrote? [y/N]`. Answer yes.

2. **Write the rules.** Type `purlin:spec cart` and say what the feature does. It shows you the
   rules and the proofs it drafted. Once you agree, it commits the spec and ends on
   `Spec saved: cart. Next: purlin:build cart`.

3. **Build.** Type `purlin:build cart`. It writes the code and a test for each proof, with one
   comment above each test naming the proof. It commits them and runs `purlin:test cart`. The
   first test run in a project has no test command yet, so it suggests one:

   ```text
   No test command is set in .purlin/config.json, so nothing ran.
   Suggested for pytest: python3 -m pytest {files} --junitxml={report}
   ```

   Say yes. The command is written into `.purlin/config.json`, that file is committed, and the
   tests run. Then `purlin:test --commit` commits the work and its evidence. The run ends:

   ```text
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

4. **Read it.** When a test fails, the run names the rule and the test. Here it is the test of
   `RULE-2`:

   ```text
   cart RULE-2 fails: tests/test_cart.py::test_sum. Run purlin:build cart.
   ```

   The run ends on what is left to do, and exits 1:

   ```text
   3 rules. 2 pass their tests.
   Left to do:
     1 rule to fix: purlin:build
   ```

   When you change the code a spec covers, its rules are out of date. The next `purlin:test`
   runs them again and names what changed.

[docs/getting-started.md](docs/getting-started.md) walks the same path in full.

## The two facts

| Fact | What it reads | The command that moves it |
|------|---------------|---------------------------|
| `Tests` | `met` when every rule's tests pass on the committed evidence, `not met` otherwise | `purlin:test --all --commit`, and your project's own run for a proof tagged for another operating system |
| `Sign-off` | `signed 0.1.0 at a1b2c3d`, `signed 0.1.0, 4 commits since` or `not signed` | `purlin:sign`, whose first sign-off of a version writes the signed tag `signed/<version>` |

**Nothing is signed while the work goes on.** Product, QA and developers improve the rules, the
proofs and the tests together. A **proof** is a plain sentence saying how a rule is shown.

**When everyone is done, a person signs the evidence once.** Any project may run `purlin:sign`
whenever it chooses. It builds the evidence package from the committed evidence, stops at each
hand check, and takes one signature over the package. Several people may sign.

**The audit asks whether your tests would catch a bug.** `purlin:audit` runs heuristic spot
tests. Then, for each proof, an AI writes the one small bug that proof's test is most likely to
miss, and the bug is planted in a copy of the project. It reports the share of rules it found
strong. Nothing waits on it. `purlin:build` strengthens a weak test and settles the finding with
a test run.

The whole loop runs on one machine.
[references/evidence_and_signoff.md](references/evidence_and_signoff.md) is the one definition.

## Commands

| Command | Purpose |
|---------|---------|
| `purlin:init` | Set a project up for Purlin, or bring a project Purlin 0.9.5 set up to this version |
| `purlin:spec <name>` | Write or change a spec: turn a requirement into rules and proofs, or add, sharpen, reword or remove a rule, a case or a proof of an existing spec. Use it for any change to a file under specs/, instead of editing the file by hand |
| `purlin:build [name]` | Write the code and the marked tests for a spec's rules, fix a failing rule, strengthen a weak test, and commit the changeset |
| `purlin:test [feature ...] [--all \| --clean] [--commit] [--arm-timeout <seconds>]` | Run the project's marked tests and record the results as evidence; with --all --commit, the hand-off before a sign-off |
| `purlin:audit [feature ...] [--all] [--commit] [--arm-timeout <seconds>]`, `purlin:audit <feature> RULE-N --settle [--sound PROOF-N]` | Check how much the tests are worth: heuristic spot tests and one planted bug per proof, written into the evidence |
| `purlin:sign [--version <version>]` | Sign off a version: build the evidence package from the committed evidence, walk its hand checks with a person, and sign it in a signed commit; also check a package against its fingerprint |
| `purlin:status [name]` | Show where the project stands: whether the tests are met, whether it is signed, each rule's two cells, and what is left to do |
| `purlin:drift` | Report what a pull, a merge, a rebase or a checkout changed in the rules, the proofs and the tests, and name a number two branches both took |
| `purlin:anchor <cmd>` | Write rules that hold across the whole project as an anchor, pull an anchor from another repository, and keep its pin current |
| `purlin:spec-from-code [dir]` | Write the specs for a codebase that has none, from the code and the tests it already has |

[references/purlin_commands.md](references/purlin_commands.md) has every flag.

## Run from a checkout

To work on Purlin itself, or to try a version before installing it:

```bash
claude --plugin-dir /path/to/purlin
```

Setup writes no file that names the folder Purlin ran from. A project is the same on every
machine.

## Documentation

[docs/index.md](docs/index.md) lists every guide. Three to start with:

- [docs/how-purlin-works.md](docs/how-purlin-works.md): the model in one page.
- [docs/sign-off.md](docs/sign-off.md): from acceptance criteria to the sign-off, what Purlin
  hands a regulated sign-off system, and where its part ends.
- [docs/audit.md](docs/audit.md): how Purlin asks whether your tests would catch a bug.
