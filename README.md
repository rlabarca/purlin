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

Purlin cannot prove your code is correct, and it makes no claim of compliance. In a regulated
environment, use it beside your document control system:
[the sign-off](docs/sign-off.md) says how.

## Who it is for

Agentic developers using Claude Code that need proof their AI-written code does what was asked,
requirement by requirement.

Choose something else when:

- **A spec only has to steer an agent.** GitHub Spec Kit, OpenSpec and Kiro do that with less
  to learn.
- **Your team does not use Claude Code.** Purlin is a plugin for it.
- **You need a validated system of record.** Purlin hands its evidence to one, and is not one.

## What it touches

- A settings file, `.purlin/config.json`, a folder for evidence and a few lines in `.gitignore`.
- Your specs: Markdown files you write, under `specs/`.
- One comment above a test: `# purlin: cart PROOF-1`. The test itself does not change.
- Your own test command. Nothing is installed in your test suite.
- A commit only when you ask. No git hook, no background job and no pipeline.

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

Coming from 0.9.5? See [Coming from 0.9.5](#coming-from-095).

## The first run

1. `purlin:init` sets the project up. Answer yes to commit the files it wrote.
2. `purlin:spec cart` writes the rules and proofs from what you say the feature must do.
3. `purlin:build cart` writes the code and a test for each proof, and runs the tests. The first
   run suggests your test command, and you confirm it.
4. `purlin:test --commit` commits the work and its evidence. The run ends:

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

When a test fails, the run names the rule and the test, and `Left to do` names the command that
fixes it. [docs/getting-started.md](docs/getting-started.md) walks the same path.

## The two facts

| Fact | What it reads | The command that moves it |
|------|---------------|---------------------------|
| `Tests` | `met` when every rule's tests pass on the committed evidence, `not met` otherwise | `purlin:test --all --commit` |
| `Sign-off` | `signed 0.1.0 at a1b2c3d`, `signed 0.1.0, 4 commits since` or `not signed` | `purlin:sign` |

- **Nothing is signed while the work goes on.** Product, QA and developers improve the rules,
  the proofs and the tests together.
- **When everyone is done, a person signs the evidence once.** `purlin:sign` builds the evidence
  package and takes one signature. Signing is optional.
- **The audit asks whether your tests would catch a bug.** `purlin:audit` plants a small bug for
  each proof, in a copy of the project, and runs that proof's test. Nothing waits on it.

[docs/how-purlin-works.md](docs/how-purlin-works.md) is the model in one page.

## Coming from 0.9.5

0.10.0 is a different tool. What differs:

- **Nothing is installed in your test suite.** A test is any test of yours with one comment
  above it. The proof plugins and the git hooks are gone.
- **Two facts replace the receipt.** `purlin:verify` is gone. `purlin:sign` signs the evidence,
  and it is optional.
- **The audit plants a bug.** A rule reads `strong` when its test catches the bug and `weak`
  when it does not. 0.9.5 graded a test by reading it.
- **A prompt or a skill is tested like code**, on the models a proof names.

To upgrade, after the plugin updates:

1. `purlin:init --update` lists each change, asks before it, and makes one commit with a
   backup.
2. `purlin:test --all --commit` runs every test. Every rule reads `not run` until it does.

[RELEASE_NOTES.md](RELEASE_NOTES.md) has every difference.
[docs/upgrading.md](docs/upgrading.md) walks the upgrade.

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

[docs/index.md](docs/index.md) lists every guide. Five to start with:

- [docs/how-purlin-works.md](docs/how-purlin-works.md): the model in one page.
- [docs/sign-off.md](docs/sign-off.md): the sign-off, and where to start in a regulated
  environment.
- [docs/audit.md](docs/audit.md): how Purlin asks whether your tests would catch a bug.
- [docs/testing-ai.md](docs/testing-ai.md): testing a prompt or a skill, on the models you
  name.
- [docs/graded-by-ai.md](docs/graded-by-ai.md): a proof a second model grades.
