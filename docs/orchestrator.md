# Running Purlin from an orchestrator

Most of a Purlin run needs no judgement. A spec does: it turns what someone wants into rules. A
build writes code against rules already decided, and a test run or an audit starts a script and
reads what it printed. This page shows how a script or an agent platform that drives the work,
an orchestrator, starts each step on the model it needs, and what that saved in a trial.

Purlin chooses no model for this. It keeps its state in files: the spec, the code, the tests and
the evidence. Any step can start in a new session, on any model, and read where the last one
left off.

## Where Purlin uses a model, and who chooses it

| Where | Who chooses | How |
|---|---|---|
| The session that runs a command: `purlin:spec`, `purlin:build`, `purlin:test`, ... | You, or your orchestrator | `claude --model`, `/model` in a session, `claude -p --model` |
| The test of an AI proof | The spec | The proof's `@ai(...)` tag. The model is part of what is tested, so it is never routed |
| A grader | The spec | The proof's `@graded(...)` tag |
| The audit's planted bugs | The environment | `ANTHROPIC_MODEL`, else Claude Code's default model. The audit starts `claude` with no settings, so the session's model and settings do not reach it |

The evidence records the model each time one answers: each model an AI proof ran on, each
grader, and, for each planted bug, the model that wrote it.

## The pattern

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

**Why it costs less.**

- **The build runs at Sonnet's price.** It writes code and tests against rules already
  written.
- **Test runs and the audit start no session.** A session that starts a script and reads its
  output pays for its whole context on each turn; the script alone costs nothing.
- **No session switches model.** A switch rewrites the conversation into the new model's cache.
  Each step here starts on its own model and ends.

## What it saved

A trial on 11 Nov 2026, with Purlin at `dae5bbc90` and Claude Code 2.1.322, built the order
system of [PR #10](https://github.com/rlabarca/purlin/pull/10)'s trial: inventory, orders and
invoicing, one spec, one build and one test run each, then one audit. It ran 3 times in each arm,
from a new project each time, with the same requirement, the same answer to each spec and the
planted bugs on `claude-opus-5-5` in both.

- **Opus throughout:** one Opus session, every step a turn of it.
- **The orchestrator:** as in the table above.

Mean cost per run, from each call's `total_cost_usd`, the audit's own calls included:

| Step | Opus throughout | The orchestrator |
|---|---|---|
| spec ×3 | $1.50 | $1.64 |
| build ×3 | $1.34 | $0.69 |
| test ×3 | $0.43 | $0.00 |
| audit, the session | $0.32 | $0.00 |
| audit, the planted bugs | $4.28 | $3.80 |
| **Total** | **$7.87** ($7.58 to $8.20) | **$6.12** ($5.85 to $6.57) |
| Sessions alone | $3.59 | $2.33 |
| Minutes per run | 12.0 | 9.8 |

The orchestrator cost 22% less per run, and its sessions 35% less. Part of the 22% is that its
specs held fewer rules, 121 against 138 over the three runs, and a planted bug costs about $0.09
per rule in both. With the same number of rules, the orchestrator costs about 15% less.

What the builds do, against 30 acceptance checks written from the requirement before any run,
and what the status and the audit found:

| | Opus throughout | The orchestrator |
|---|---|---|
| Acceptance checks passed | 90 of 90 | 82 of 90 |
| Rules passing their tests | 138 of 138 | 121 of 121 |
| Rules the audit found strong | 130 of 138 (94%) | 90 of 121 (74%) |

- **The 8 failed checks are one run's invoicing.** Its spec did not fix the order of the
  arguments of `invoice`, and its build, which started with the spec and nothing else, took
  `code` before `today`. In one session the build still had the requirement in its
  conversation.
- **Most of the difference in audit strength is one run.** Its audit found 21 of 44 rules
  strong: one proof covered 6 rules with one test, and the build's tests let planted bugs
  through. The other two runs found 87% and 92%.

The planted bugs are more than half the cost in both arms. The audit asks again only about the
rules whose test or code changed, so later audits cost a fraction of the first.

## Two things to do

- **Put every requirement the code must meet in a rule.** A build started in a new session reads
  the spec and the code alone. A detail that lives only in a conversation, such as the order
  of a function's arguments, is a detail the build guesses.
- **Run the audit, and send its weak rules back to the build.** It is how a cheaper build is
  checked: a weak rule names the test that let a bug through.

## Working by hand

Without an orchestrator, the same pattern is two habits:

- Write and sign specs in a session on Opus: `claude --model opus`. Build in a new session on
  Sonnet: `claude --model sonnet`, then `purlin:build <feature>`. Each session starts from the
  files.
- Ask for the build in a subagent on Sonnet from an Opus session: "run purlin:build orders in a
  subagent on sonnet". The trial did not measure this.

## Limits

- One requirement, three parts, 3 runs per arm, measured on one day at that day's prices.
- Spec and sign need a person, so an orchestrator runs them in a session someone answers.
- The planted bugs ran on Opus in both arms. On a cheaper model they cost less, and the trial did
  not measure what that does to the audit.
- The harness, the requirement and the acceptance checks are in
  [`dev/model_cost_trial/`](../dev/model_cost_trial/requirement.md).

The idea and the first trial came from [PR #10](https://github.com/rlabarca/purlin/pull/10).
Its trial found routing inside one session 16% cheaper, from session transcripts, which do not
hold the audit's own calls.
