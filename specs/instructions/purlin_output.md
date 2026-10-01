# Feature: purlin_output

> Description: The one check of what Purlin prints. The files under `scripts/` print Purlin's
>   terminal lines and build its dashboard, setup writes a project's files from `templates/`,
>   and the skills and the agent definition tell the model what to write, so no emoji and no
>   pictograph in those files means none in what Purlin prints or writes. Purlin also runs on
>   Python 3.9 and leaves no process of its own running.
> Scope: scripts/**, templates/**, skills/*/SKILL.md, agents/purlin.md
> Highest-Rule: 4
> Highest-Proof: 7

## Rules

- RULE-1: No file under `scripts/` or `templates/` carries an emoji or a pictograph other than `▶`
- RULE-2: Setup, a test run and the status run on Python 3.9
- RULE-3: No Purlin command leaves a process of its own running after it exits
- RULE-4: Neither a skill definition under `skills/` nor `agents/purlin.md` carries an emoji or a pictograph other than `▶`

## Proof

- PROOF-1 (RULE-1): Every tracked file under `scripts/` and `templates/` is read; none holds a character with the Unicode property `Extended_Pictographic`, or U+FE0F, other than `▶`
- PROOF-2 (RULE-2): Every Python file under `scripts/` is read with the grammar of Python 3.9; each is accepted
- PROOF-4 (RULE-2): Under Python 3.9, a test run over every feature of a set-up project whose one proof has a passing test exits 0 and prints `Markers: 1 tied to a test, 0 not tied.`
- PROOF-5 (RULE-2): Under Python 3.9, Purlin's server is asked for the status of a set-up project with one spec, `app`; it answers with a table row for `app` and exits 0 once its input closes
- PROOF-6 (RULE-3): In a scratch project, setup, a test run with `--commit` and the status each exit 0; afterwards no process any of them started is still running, and none whose command line names the scratch project
- PROOF-7 (RULE-4): Every character of each `skills/*/SKILL.md` and of `agents/purlin.md` is read; none has the Unicode property `Extended_Pictographic` or is U+FE0F, other than `▶`
