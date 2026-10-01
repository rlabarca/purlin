<p align="center">
  <img src="design/assets/logo.svg" alt="Purlin" width="360">
</p>

# Purlin

Purlin is a Claude Code plugin for spec-driven development. You write the rules your software
must follow, one comment above a test ties it to a rule, and Purlin runs your own test command
and tells you which rules pass over the code as it is now. It keeps two things in the
repository: the evidence of what the tests saw, and a person's sign-off over it. It shows them
as two facts, `Tests: met` and `Sign-off: signed 0.1.0 at a1b2c3d`. Where sign-off happens in a
regulated system, Purlin's evidence package is an input to it. Purlin cannot prove your code is
correct, and it makes no claim of compliance.

## What it touches

- A settings file, the specs and the evidence: `.purlin/config.json`, `specs/`,
  `.purlin/evidence/`, a block in `.gitignore`, and a copy of the dashboard page,
  `purlin-report.html`, which that block keeps out of git.
- One comment above a test: `# purlin: cart PROOF-1`.
- Your own test command, in your own framework, with the flag that makes it write a report. The
  first test run suggests it, and you confirm it.
- A commit when you agree to one: setup asks before it commits the files it wrote, and a test
  run commits its results only with `--commit`.
- Nothing running unless you ran it: no git hook, and no Purlin process left running after a
  command ends. A runner file for the git host is written by the first `purlin:test --remote`,
  only where a proof is tagged for an operating system this machine is not.
- Nothing added to your test suite.

## Install

You need git, Python 3.9 or later and
[Claude Code](https://docs.anthropic.com/en/docs/claude-code).

```bash
cd my-project
claude plugin marketplace add https://github.com/rlabarca/purlin.git --scope project
claude plugin install purlin@purlin --scope project
```

Start Claude Code in the project, or run `/reload-plugins` in a session that is already open,
and the `purlin:` commands are there.

## Ten minutes

1. **Set up.** Type `purlin:init`. It names each file it wrote and asks one question,
   `Commit the files setup wrote? [y/N]`. Answer yes.

2. **Write the rules.** Type `purlin:spec cart` and say what the feature does. It shows you the
   rules and the proofs it drafted, commits the spec once you agree, and ends on
   `Spec saved: cart. Next: purlin:build cart`.

3. **Build.** Type `purlin:build cart`. It writes the code and a test for each proof, with one
   comment above each test naming the proof, commits them, and runs `purlin:test cart`. The
   first test run in a project has no test command to run, so it suggests one:

   ```text
   No test command is set in .purlin/config.json, so nothing ran.
   Suggested for pytest: python3 -m pytest --ignore=mutants {files} --junitxml={report}
   ```

   Say yes. The command is written into `.purlin/config.json`, the tests run, and
   `purlin:test --commit` commits the work and its evidence. The run ends:

   ```text
   Purlin status: shop, plugin 0.10.0
   Tests: met
   Sign-off: not signed

   Spec  Rules  Proofs  Tests
   ───────────────────────────
   cart  3      3       3 of 3
   ───────────────────────────

   3 rules. 3 pass their tests.
   Every rule passes its tests on the committed evidence. To sign it: purlin:sign
   ```

4. **Read it.** Where a test fails, here the test of `RULE-2`, the run names the rule and the
   test, ends on what is left to do, and exits 1:

   ```text
   cart RULE-2 fails: tests/test_cart.py::test_sum. Run purlin:build cart.
   ```

   ```text
   3 rules. 2 pass their tests.
   Left to do:
     1 rule to fix: purlin:build
   ```

   Change the code the spec covers and its rules are out of date; the next `purlin:test` runs
   them again and names what changed.

[docs/getting-started.md](docs/getting-started.md) walks the same path in full.

## The two facts

| Fact | What it reads | The command that moves it |
|------|---------------|---------------------------|
| `Tests` | `met` when every rule's tests pass on the committed evidence, `not met` otherwise | `purlin:test --all --commit`, and `purlin:test --remote` for a proof tagged for another operating system |
| `Sign-off` | `signed 0.1.0 at a1b2c3d`, `signed 0.1.0, 4 commits since` or `not signed` | `purlin:sign`, whose first sign-off of a version writes the signed tag `signed/<version>` |

Nothing is signed while the specs change: product, QA and developers improve the rules, the
**proofs**, plain sentences saying how each rule is shown, and the tests together. When the
tests are met, any project may run `purlin:sign` whenever it chooses: it builds the evidence
package from the committed evidence, stops at each hand check, and takes one signature over the
package; several people may sign. `purlin:audit` asks whether the tests would catch a bug: it
runs heuristic spot tests, then plants one bug per proof in a copy of the project, and reports
the share of rules it found strong. Nothing waits on it. The whole loop runs on one machine.
[references/evidence_and_signoff.md](references/evidence_and_signoff.md) is the one definition.

## Commands

| Command | Purpose |
|---------|---------|
| `purlin:init` | Set a project up for Purlin |
| `purlin:spec <name>` | Turn a requirement in any form into rules and proofs |
| `purlin:build [name]` | Load a spec's rules, write the code and the marked tests, commit the changeset |
| `purlin:test [feature ...] [--all] [--commit] [--remote [--commit-runner]] [--arm-timeout <seconds>]` | Run the marked tests and print each rule's passed cell |
| `purlin:audit [feature ...] [--all] [--commit] [--arm-timeout <seconds>]` | Run the tests, the heuristic spot tests, one planted bug per proof and the model's reading, then write what it found into the evidence |
| `purlin:sign [--version <version>]` | Build the evidence package from the committed evidence, walk its hand checks with a person, then sign it in a signed commit |
| `purlin:status [name]` | Show the two facts, every rule's cells and what is left to do |
| `purlin:drift` | Report what changed since your last pull |
| `purlin:anchor <cmd>` | Create anchors, pull them from another repository, and keep the pins current |
| `purlin:spec-from-code [dir]` | Read an existing codebase and write the specs it already implies |

[references/purlin_commands.md](references/purlin_commands.md) has every flag.

## Run from a checkout

To work on Purlin itself, or to try a version before installing it:

```bash
claude --plugin-dir /path/to/purlin
```

No file setup writes into a project names the folder Purlin ran from, so a project is the same
on every machine.

## Documentation

[docs/index.md](docs/index.md) lists every guide.
[docs/how-purlin-works.md](docs/how-purlin-works.md) is the model in one page,
[docs/sign-off.md](docs/sign-off.md) takes a signer from acceptance criteria to the sign-off
and says what Purlin hands a regulated sign-off system and where its part ends, and
[docs/audit.md](docs/audit.md) says how Purlin asks whether your tests would catch a bug.
