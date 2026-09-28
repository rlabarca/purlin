<p align="center">
  <img src="design/assets/logo.svg" alt="Purlin" width="360">
</p>

# Purlin

Purlin is a Claude Code plugin for spec-driven development. You write the rules your software
must follow, put one comment above each test that shows a rule, and Purlin runs your own test
command and tells you which rules pass over the code as it is now. A team can ask for more: an
AI audit of whether the tests are sound, and a person's signature on each rule, locked with a
signed git tag. Its intended use is to produce that evidence, in the repository, for the people
who build the software and for whoever must sign it off; where sign-off happens in a regulated
system, Purlin's evidence package is an input to it. Purlin cannot prove your code is correct,
and it makes no claim of compliance.

## What it touches

- A settings file and the specs you write: `.purlin/config.json`, `.purlin/evidence/`,
  `specs/`, a block in `.gitignore`, and an ignored copy of the dashboard page.
- One comment above a test: `# purlin: cart RULE-1`.
- Your own test command, in your own framework, with the flag that makes it write a report.
- Nothing committed unless you ask: a run commits its results only with `--commit`.
- Nothing running unless you ran it: no git hook, no background job, and no CI workflow unless
  a rule needs another operating system or you do not trust this machine.
- Nothing installed in your test suite.
- If you leave, the markers are comments.

## Ten minutes

1. **Install.** You need git, Python 3.9 or later and
   [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

   ```bash
   cd my-project
   claude plugin marketplace add https://github.com/rlabarca/purlin.git --scope project
   ```

   Inside Claude Code: `/plugin install purlin@purlin`, `/reload-plugins`, then `purlin:init`,
   answering `passed` to the gate question.

2. **Write three rules** in `specs/shop/cart.md`:

   ```markdown
   # Feature: cart

   > Scope: src/cart.py

   ## Rules

   - RULE-1: An empty cart totals 0
   - RULE-2: The total is the sum of price times quantity
   - RULE-3: A negative quantity is refused
   ```

3. **Add one comment above each of three tests:**

   ```python
   # purlin: cart RULE-1
   def test_empty():
       assert total([]) == 0
   ```

4. **Run one command:** `purlin:test`. It ends:

   ```
   3 of 3 rules meet the gate passed.
   Untested 0 · Failing 0 · Partial 0 · Passing 3.
   1 feature.

   → Next: nothing is outstanding at gate passed.

   gate passed: 3 of 3
   ```

5. **Read it.** A failing rule is counted under `Failing` and the last line reads
   `gate not met: 2 of 3`. Change `src/cart.py` and the rules of `cart` are out of date until
   the next run, which says why it picked them:
   `Selected 1 of 1 feature: cart (code changed since bf3709e).`

[docs/getting-started.md](docs/getting-started.md) walks the same path in full.

## When a team wants more

The **gate** is how far the project asks every rule to go, and each step up has one command:

| Gate | What every rule must have | The command |
|------|---------------------------|-------------|
| `passed` | its tests pass over the current code | `purlin:test` |
| `strong` | that, and an AI audit that found the tests sound | `purlin:audit` |
| `signed` | that, and a person's signature | `purlin:sign` |

From `strong` up, each rule carries a **proof**, a plain sentence saying how the rule is shown,
and the marker names it: `# purlin: cart PROOF-2`. `purlin:sign` walks the rules that wait on
a person and, at the gate `signed` once every rule meets it, writes the evidence package and the
signed tag `signed/<version>`. The whole loop runs on one machine at every gate. A single rule
can ask for less with `[level: passed]`; the gate is the ceiling.
[references/hard_gates.md](references/hard_gates.md) is the one definition.

## Commands

| Command | Purpose |
|---------|---------|
| `purlin:init` | Set a project up for Purlin, and change the gate later |
| `purlin:spec <name>` | Turn a requirement in any form into rules and proofs |
| `purlin:spec-from-code [dir]` | Read an existing codebase and write the specs it already implies |
| `purlin:build [name]` | Load a spec's rules, write the code and the marked tests, commit the changeset |
| `purlin:test [feature]` | Run the marked tests and print each rule's passed cell |
| `purlin:audit [feature]` | Run the tests, the breaks where mutation testing is on, and the AI audit, then write what it found into the evidence |
| `purlin:sign [feature] [RULE-N]` | Walk the queue, or sign a rule, a feature or a batch as a signed commit |
| `purlin:export` | Write the evidence package for a version, the data file a regulated system of record reviews |
| `purlin:status [name]` | Show every rule's cells and what blocks the gate |
| `purlin:drift [role]` | Report what changed since your last pull, by role |
| `purlin:anchor <cmd>` | Create anchors, pull them from another repository, and keep the pins current |

Plain language reaches every one of them: "run the tests" reaches `purlin:test`. The syntax
above is canonical, never required. [references/purlin_commands.md](references/purlin_commands.md)
has every flag.

## Install from a checkout

To work on Purlin itself, or to try a version before installing it:

```bash
claude --plugin-dir /path/to/purlin
```

A project never carries a copy of Purlin. `--scope project` records the marketplace in the
project's `.claude/settings.json`, so a teammate who clones the repository resolves the same
source and runs the install and the reload once.

## Documentation

[docs/index.md](docs/index.md) maps every guide by role.
[docs/how-purlin-works.md](docs/how-purlin-works.md) is the model in one page, and
[docs/regulated-workflow.md](docs/regulated-workflow.md) says what Purlin hands a regulated
sign-off system and where its part ends.
