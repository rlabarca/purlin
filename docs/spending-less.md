# Spending less on models

Most of a Purlin run needs no judgement. A spec does: it turns what someone wants into rules. A
build writes code against rules already decided, and a test run or an audit starts a script and
reads what it printed. This page says where Purlin uses a model, what Purlin does by default to
keep a run cheap and its results sound, what you can do to spend less, and what each saved in a
trial.

## Where Purlin uses a model, and who chooses it

| Where | Who chooses | How |
|---|---|---|
| The session that runs a command: `purlin:spec`, `purlin:build`, `purlin:test`, ... | You, or your orchestrator | `claude --model`, `/model` in a session, `claude -p --model` |
| The test of an AI proof | The spec | The proof's `@ai(...)` tag. The model is part of what is tested, so it is never routed |
| A grader | The spec | The proof's `@graded(...)` tag |
| The audit's planted bugs | The environment | `ANTHROPIC_MODEL`, else Claude Code's default model. The audit starts `claude` with no settings, so the session's model and settings do not reach it |

## What Purlin does by default

- **It keeps its state in files.** The spec, the code, the tests and the evidence are all on
  disk, so any step can start in a new session, on any model, and read where the last one left
  off.
- **The spec holds every name the input gives.** A function and its arguments in their order, a
  field, a file, a format: each goes into a rule or a proof word for word, and the spec skill
  checks each one before it shows the rules. A build that starts in a new session reads the spec
  and the code alone, so it guesses nothing the input settled.
- **Each rule has a proof of its own.** A proof names several rules only where it drives one flow
  through all of them, so one weak test does not make several rules weak.
- **Results carry forward.** `purlin:test` runs the features whose spec, code or tests changed,
  and the audit asks the model again only about the rules whose test or code changed.
- **The audit says what it asked and what that cost**, on the line before its last:
  `The audit asked claude-opus-5-5 about 15 rules: $1.35.`
- **The evidence records each model that answered:** each model an AI proof ran on, each grader,
  and, for each planted bug, the model that wrote it.

These defaults do not lower the price of a run on their own: in the trial below, one Opus session
cost the same with them as without. They are what makes a build in a cheaper session safe: with
them, the orchestrator below passed every acceptance check.

## What you can do to spend less

### Run Purlin from an orchestrator

An orchestrator is a script or an agent platform that drives the work. It starts each step on the
model it needs:

| Step | How it starts | Model |
|---|---|---|
| `purlin:spec` | An interactive session: a person answers its questions | Opus |
| `purlin:build` | `claude -p --model sonnet "/purlin:build <feature>"`, a new session | Sonnet |
| `purlin:test` | `purlin_run.py --test`, no session | none |
| `purlin:audit` | `purlin_run.py --audit`, no session | the planted bugs' model |
| `purlin:status` | `purlin_status.py`, no session | none |
| `purlin:sign` | An interactive session: a person signs | Opus |

The scripts are the ones `purlin:test`, `purlin:audit` and `purlin:status` start. Run them from
a clone of Purlin at the tag `signed/<version>` of the version in your `.purlin/config.json`, as
[Running the tests](running-and-evidence.md#one-example-github-started-from-your-desk) does
for another system. The audit's planted bugs need the `claude` program signed in.

For one feature:

```bash
PURLIN="$HOME/purlin"        # a clone at signed/<version>
feature=orders

claude --model opus "/purlin:spec $feature"      # you read the draft and answer

for attempt in 1 2 3; do
  claude -p --model sonnet "/purlin:build $feature"
  python3 "$PURLIN/scripts/run/purlin_run.py" --test --feature "$feature" && break
done

ANTHROPIC_MODEL=claude-opus-5-5 \
  python3 "$PURLIN/scripts/run/purlin_run.py" --audit --feature "$feature"
python3 "$PURLIN/scripts/run/purlin_status.py"
```

`purlin_run.py --test` exits 1 when a tied test failed or did not run, so the loop sends the
feature back to the build. A rule the audit found `weak` goes back to the build the same way:
`claude -p --model sonnet "/purlin:build $feature"` strengthens its test and settles it.

Write the `tests` setting before the first build, with `purlin_run.py --write-tests` or the
`purlin_config` tool, so a build started with `-p` has no question to ask about the test command.

It costs less for three reasons:

- **The build runs at Sonnet's price.** It writes code and tests against rules already written.
- **Test runs and the audit start no session.** A session that starts a script and reads its
  output pays for its whole context on each turn; the script alone costs nothing.
- **No session switches model.** A switch rewrites the conversation into the new model's cache.
  Each step here starts on its own model and ends.

### Choose the planted bugs' model

The planted bugs are more than half of a first audit's cost: one call per rule read, about $0.09
a rule on Opus. `ANTHROPIC_MODEL` sets the model they go to. A cheaper model costs less, and the
trial did not measure what it does to the audit's findings.

### Work by hand

Without an orchestrator, the same pattern is two habits:

- Write and sign specs in a session on Opus: `claude --model opus`. Build in a new session on
  Sonnet: `claude --model sonnet`, then `purlin:build <feature>`. Each session starts from the
  files.
- Ask for the build in a subagent on Sonnet from an Opus session: "run purlin:build orders in a
  subagent on sonnet". The trial did not measure this.

## What each saved

Two trials on 11 Nov 2026, with Claude Code 2.1.322, built the order system of
[PR #10](https://github.com/rlabarca/purlin/pull/10)'s trial: inventory, orders and invoicing,
one spec, one build and one test run each, then one audit. The first ran Purlin at `dae5bbc90`,
before the spec checks above; the second at `892f7ae22`, with them. Each ran 3 times in each arm,
from a new project each time, with the same requirement, the same answer to each spec and the
planted bugs on `claude-opus-5-5`.

- **Opus throughout:** one Opus session, every step a turn of it.
- **The orchestrator:** as in the table above.

Mean cost per run, from each call's `total_cost_usd`, the audit's own calls included:

| | Opus throughout, before | Orchestrator, before | Opus throughout, with the defaults | Orchestrator, with the defaults |
|---|---|---|---|---|
| spec ×3 | $1.50 | $1.64 | $1.60 | $1.71 |
| build ×3 | $1.34 | $0.69 | $1.37 | $0.70 |
| test ×3 | $0.43 | $0.00 | $0.45 | $0.00 |
| audit, the session | $0.32 | $0.00 | $0.35 | $0.00 |
| audit, the planted bugs | $4.28 | $3.80 | $4.13 | $3.95 |
| **Total** | **$7.87** | **$6.12** | **$7.90** | **$6.37** |
| Range over 3 runs | $7.58 to $8.20 | $5.85 to $6.57 | $7.70 to $8.19 | $5.89 to $6.72 |
| Sessions alone | $3.59 | $2.33 | $3.77 | $2.42 |
| Minutes per run | 12.0 | 9.8 | 12.2 | 10.0 |

What the builds do, against 30 acceptance checks written from the requirement before any run,
and what the status and the audit found:

| | Opus throughout, before | Orchestrator, before | Opus throughout, with the defaults | Orchestrator, with the defaults |
|---|---|---|---|---|
| Acceptance checks passed | 90 of 90 | 82 of 90 | 90 of 90 | 90 of 90 |
| Rules passing their tests | 138 of 138 | 121 of 121 | 133 of 133 | 129 of 129 |
| Rules the audit found strong | 130 of 138 (94%) | 90 of 121 (74%) | 124 of 133 (93%) | 113 of 129 (88%) |

- **The defaults alone:** one Opus session cost $7.90 a run with them and $7.87 without, a
  difference inside the spread of either. Every acceptance check passed both ways.
- **The orchestrator, with the defaults:** $6.37 a run, 19% less than one Opus session, its
  sessions 36% less. Every acceptance check passed, and the audit found 88% of rules strong
  against 93%.
- **What the defaults did for the orchestrator:** without them, one run's spec did not fix the
  order of the arguments of `invoice`, and its build, which started with the spec and nothing
  else, took `code` before `today`: 8 checks failed. Another run's spec gave one proof to 6
  rules, and its audit found 21 of 44 rules strong. With the defaults neither happened.

The planted bugs are more than half the cost in every arm. A later audit asks only about the
rules whose test or code changed, so it costs a fraction of the first.

## Limits

- One requirement, three parts, 3 runs per arm, measured on one day at that day's prices.
- Spec and sign need a person, so an orchestrator runs them in a session someone answers.
- The planted bugs ran on Opus in every arm.
- The harness, the requirement, the acceptance checks and each run's results are in
  [`dev/model_cost_trial/`](../dev/model_cost_trial/requirement.md).

The idea and the first trial came from [PR #10](https://github.com/rlabarca/purlin/pull/10).
Its trial found routing inside one session 16% cheaper, from session transcripts, which do not
hold the audit's own calls.
