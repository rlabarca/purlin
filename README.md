<p align="center">
  <img src="design/assets/logo.svg" alt="Purlin" width="360">
</p>

# Purlin

Purlin is a Claude Code plugin for spec-driven development. You write the rules your software
must follow, one comment above a test ties it to a rule, and Purlin runs your own test command
and tells you which rules pass over the code as it is now. A release is a commit, its evidence
package and a tag. A team can ask for more: a person's sign-off on each release, with a signed
git tag, and an AI audit of whether the tests are sound, a tool nothing waits on. Purlin keeps that evidence in the repository, for the people who build the
software and for whoever signs it off; where sign-off happens in a regulated system, Purlin's
evidence package is an input to it. Purlin cannot prove your code is correct, and it makes no
claim of compliance.

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
  command ends. A runner file for the git host is written only where a proof is tagged for an
  operating system this machine is not.
- Nothing added to your test suite.

## Ten minutes

1. **Install.** You need git, Python 3.9 or later and
   [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

   ```bash
   cd my-project
   claude plugin marketplace add https://github.com/rlabarca/purlin.git --scope project
   ```

   Inside Claude Code: `/plugin install purlin@purlin`, then `/reload-plugins`.

2. **Set up.** Type `purlin:init`. Answer `passed` to the gate question and yes to committing
   the files it wrote. In a project with no code yet it ends:

   <!-- sample: setup -->
   ```text
   No specs found under specs/.
   → Run: purlin:spec <name> to write the first spec.
   ```

3. **Write the rules.** Type `purlin:spec cart` and say what the feature does. It shows you the
   rules and the proofs it drafted, commits the spec once you agree, and ends on
   `Spec saved: cart. Next: purlin:build cart`.

4. **Build.** Type `purlin:build cart`. It writes the code and a test for each proof, with one
   comment above each test naming the proof, commits them, and runs `purlin:test cart`. The
   first test run in a project has no test command to run, so it suggests one:

   <!-- sample: first-run -->
   ```text
   No test command is set in .purlin/config.json, so nothing ran.
   Suggested for pytest: python3 -m pytest --ignore=mutants {files} --junitxml={report}
   ```

   Say yes. The command is written into `.purlin/config.json`, the tests run, and the run ends:

   <!-- sample: confirmed-run -->
   ```text
   Spec  Rules  Proofs  Tests
   ───────────────────────────
   cart  3      3       3 of 3
   ───────────────────────────

   3 rules. 3 pass their tests.
   Nothing left to do. To release a version: purlin:test --release
   ```

5. **Read it.** Where a test fails, here the test of `RULE-2`, the run names the rule and the
   test, ends on what is left to do, and exits 1:

   <!-- sample: failing-run -->
   ```text
   cart RULE-2 fails: tests/test_cart.py::test_sum. Run purlin:build cart.
   ```

   <!-- sample: failing-run -->
   ```text
   3 rules. 2 pass their tests.
   Left to do:
     1 rule to fix: purlin:build
   ```

   Change the code the spec covers and its rules are out of date; the next `purlin:test` runs
   them again and names what changed.

[docs/getting-started.md](docs/getting-started.md) walks the same path in full.

## Releasing, and when a team wants more

The **gate** is the one project setting: what a release needs.

| Gate | What a release needs | The commands |
|------|----------------------|--------------|
| `passed` | every rule's tests pass on the evidence committed at the release commit | `purlin:test --release`, which tags `passed/<version>` |
| `signed` | the same, and at least one person signs the evidence package | `purlin:test --release`, then `purlin:sign`, whose first sign-off writes `signed/<version>` |

Nothing is signed while the specs change: product, QA and developers improve the rules, the
**proofs**, plain sentences saying how each rule is shown, and the tests together. On a release
branch, `purlin:test --release` runs every test, commits the evidence and the package, and at
`passed` tags the release. At `signed`, `purlin:sign` walks each hand check, each weak rule and
each rule the audit has not read, then signs the package; several people may sign. `purlin:audit`
reads each rule, its proofs and its tests, and nothing waits on it. The whole loop runs on one
machine at either gate. [references/hard_gates.md](references/hard_gates.md) is the one
definition.

## Commands

| Command | Purpose |
|---------|---------|
| `purlin:init` | Set a project up for Purlin, and change the gate later |
| `purlin:spec <name>` | Turn a requirement in any form into rules and proofs |
| `purlin:spec-from-code [dir]` | Read an existing codebase and write the specs it already implies |
| `purlin:build [name]` | Load a spec's rules, write the code and the marked tests, commit the changeset |
| `purlin:test [feature ...] [--all] [--release [<version>]] [--arm-timeout <seconds>]` | Run the marked tests and print each rule's passed cell |
| `purlin:audit [feature ...] [--all] [--arm-timeout <seconds>]` | Run the tests, the breaks where mutation testing is on, and the AI audit, then write what it found into the evidence |
| `purlin:sign [--release <version>]` | Walk what a person has to look at in a release, then sign its evidence package in a signed commit |
| `purlin:export` | Write the evidence package for a version, the data file a regulated system of record reviews |
| `purlin:status [name]` | Show every rule's cells and what blocks the gate |
| `purlin:drift [role]` | Report what changed since your last pull, by role |
| `purlin:anchor <cmd>` | Create anchors, pull them from another repository, and keep the pins current |

[references/purlin_commands.md](references/purlin_commands.md) has every flag.

## Install from a checkout

To work on Purlin itself, or to try a version before installing it:

```bash
claude --plugin-dir /path/to/purlin
```

No file setup writes into a project names the folder Purlin ran from, so a project is the same
on every machine.

## Documentation

[docs/index.md](docs/index.md) maps every guide by role, and
[docs/qa-guide.md](docs/qa-guide.md) takes a QA person from acceptance criteria to the sign-off.
[docs/how-purlin-works.md](docs/how-purlin-works.md) is the model in one page, and
[docs/regulated-workflow.md](docs/regulated-workflow.md) says what Purlin hands a regulated
sign-off system and where its part ends.
