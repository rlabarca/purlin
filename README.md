<p align="center">
  <img src="design/assets/logo.svg" alt="Purlin" width="360">
</p>

# Purlin

For anyone deciding whether to put Purlin in a project, and for the engineer who sets it up.

Purlin is a Claude Code plugin for spec-driven development. A **rule** is one line in a spec
saying what the software must do. A **proof** says how that claim is observed. A **test** is the
executable form of a proof, tagged with the rule it settles. The **test results** are what a
run of the tagged tests saw, committed into the repository. A **record** is the machine's
evidence of one audit run, committed into the repository by the audit that wrote it, whether
that was yours or CI's. A **signature** is a named person's attestation that a rule, its proof
and its test belong together.

A rule answers up to three questions, each one an **evidence level**, each answered by a
**cell**: **passed**, every tagged test for the rule passed; **strong**, the tests are worth
trusting; **signed**, a person signed the rule, proof and test hashes. Three commands carry the
three levels: `purlin:test`, `purlin:audit` and `purlin:sign`. When every rule meets the gate,
`purlin:sign` writes the annotated tag `signed/<version>`, and pushing it is how a person says
this version is proven. [The gate](references/hard_gates.md) defines what the tag means.

Purlin cannot prove your code is correct. It gives you a paper trail: every claim, how it is
observed, what ran, on which commit, and who said so.

## Three ways to work

One setting, the **gate**, says what must be true of every rule before a version is proven.
`purlin:init` asks that question, and one more about this machine.

| Gate | Who it fits | What every rule must have | Where the evidence comes from |
|------|-------------|---------------------------|-------------------------------|
| `passed` | One person working alone | A tagged test for every proof, passing | the evidence `purlin:test --commit` commits; a pass from any source counts |
| `strong` | A team of PM, designers, engineers and QA | That, and a record at this commit with the test strength at or above `min_strength`, nothing outstanding the audit observed, and no hold | `purlin:audit`, run by anyone; its record counts |
| `signed` | The same team under GxP | That, and a current signature on every rule that needs one, in a signed commit | the same, plus a person's signature and the tag |

The whole loop runs on one machine: `purlin:spec`, `purlin:build`, `purlin:test`,
`purlin:audit`, `purlin:sign`, `git push`. A project at `signed` with no CI anywhere is the
ordinary case, not a special one.

Every rule also has a **level**, `passed`, `strong` or `signed`, meaning what the gate means,
written as `[level: passed]`, `[level: strong]` or `[level: signed]` on the rule line. A rule
with no tag takes the project's gate as its level, and the gate is the ceiling: a mark above it
is read as the gate. The level decides what evidence the rule needs, whether the AI audit runs
on it, and whether it needs a signature.

Raise or lower the gate later with `purlin:init --gate <level>`. Raising adds what is missing;
lowering deletes nothing. The one definition lives in
[references/hard_gates.md](references/hard_gates.md).

## Install

Purlin needs git, Python 3.9 or later, and
[Claude Code](https://docs.anthropic.com/en/docs/claude-code).

Install it from the marketplace, which is how a project uses it:

```bash
cd my-project
git init                # Purlin needs a git repository
claude plugin marketplace add https://github.com/rlabarca/purlin.git --scope project
```

Then, inside Claude Code, `/plugin install purlin@purlin` and `/reload-plugins`. The plugin
lands under `~/.claude/plugins/cache/purlin/purlin/<version>/`. `--scope project` records the
marketplace entry in the project's `.claude/settings.json`, so a teammate who clones the
repository resolves the same source; each teammate still runs the install and the reload in
their own checkout.

To work on Purlin itself, or to try a checkout before installing it, load it from disk:

```bash
claude --plugin-dir /path/to/purlin
```

A consumer project carries no copy of Purlin, so where a project has a remote runner the
workflow clones Purlin at a pinned tag and runs the same run script from that checkout. Set the
`PURLIN_REF` repository variable to move that pin without editing the workflow.

## Your first session

```
purlin:init
```

Answer the gate question with `passed`, and `y` to
`Do you trust your own machine for the tests and the signing?`. Init detects the language and
the test framework from the tree, reads the git host from the remote URL, writes `.purlin/` and
`specs/`, installs the proof plugin, and prints every file it wrote. It installs no git hook
and asks nothing of your git host.

```
purlin:spec "Users sign in with email and password. After five failed attempts the
account is locked for fifteen minutes."
```

That sentence becomes three rules, each with a proof, because each of the three can fail on its
own. The skill ends with `Spec created: login. Build it now?`

```
purlin:build login
```

Build writes the code and one tagged test per proof, runs them, commits the changeset, and
prints every rule's cells.

```
purlin:test
```

The tests run, and what they saw goes into `.purlin/evidence/local/login.json` and
`.purlin/tests.md`. The run commits nothing; `purlin:test --commit` commits both as
`purlin: evidence at <sha7>`. It ends with `gate passed: <n> of <rules>`. At `passed` that
line is the whole answer.

```
purlin:audit
```

The audit runs the tests, then breaks the code on purpose to measure how much the tests catch,
and prints the strength beside the minimum with everything it observed. It writes that into
the same evidence file, and `purlin:audit --commit` commits it as `purlin: evidence at <sha7>`.
The push is yours, it is free, and nothing runs when you make one:
nothing in Purlin pushes except `purlin:test --remote`, which pushes a run branch of its own.

Every command ends by naming the next step, computed from the cells it found.

## Commands

| Command | Purpose |
|---------|---------|
| `purlin:spec <name>` | Turn a requirement in any form into rules and proofs |
| `purlin:build [name]` | Load a spec's rules, write the code and the tagged tests, commit the changeset |
| `purlin:test [feature]` | Run the tagged tests and print each rule's passed cell |
| `purlin:audit [feature]` | Run the tests and the breaks, then write the audit into the evidence |
| `purlin:sign [feature] [RULE-N]` | Walk the review list, or sign a rule, a feature or a batch as a signed commit |
| `purlin:drift [role]` | Report what changed since the last record, by role |
| `purlin:init` | Set a project up for Purlin, and change the gate later |
| `purlin:anchor <cmd>` | Create anchors, pull them from another repository, and keep the pins current |
| `purlin:status [name]` | Show every rule's cells and what blocks the gate |
| `purlin:spec-from-code [dir]` | Read an existing codebase and write the specs it already implies |

Plain language reaches every one of them: "run the tests" reaches `purlin:test`, and "what is
left for me to look at" reaches `purlin:sign`. The syntax above is canonical, never required.

## Documentation

[docs/how-purlin-works.md](docs/how-purlin-works.md) is the whole model in one page: the chain
in one diagram, who writes each file, and the two reasons a project has a remote runner. Then
[docs/index.md](docs/index.md) maps every guide by who it is for, and
[docs/getting-started.md](docs/getting-started.md) walks the first session in full.
