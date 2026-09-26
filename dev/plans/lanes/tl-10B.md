# Lane 10B: the pages, the skills and the slides say spec, build, test

Plan: `dev/plans/three-levels.md` (Part A, decisions 23 to 28). Rules:
`dev/plans/lanes/tl-_rules.md` (in full). Read all of `design/readme.md` and `docs/_mermaid.md`.
Worktree `/Users/richlabarca/LocalCode/purlin-wt/10B`, branch `lane/10B` off `lane/10A`
**after lane 10A has landed**. **Do not push. Do not open a pull request.**

The user's words, which bind every sentence you write: the `passed` workflow is spec, build,
test, and that is it; nobody at `passed` runs a Python script; the value of a remote run is
explained in three plain reasons and the docs and the slides are as clear as those reasons;
everything matches how the code behaves exactly. Check every claim against lane 10A's code
(`purlin_run.py`, `records.py`, `remote.py`, `scaffold.py`, `states.py`, the templates) and
name the line in your report.

## The three reasons, verbatim

Use these sentences wherever a remote runner is explained, and no others:

- **Your tests need another operating system.** Your machine cannot run a test tagged for
  Windows or Linux. The runner can, so those rules stop reading `not run`.
- **Proof from a clean machine.** Your laptop may have uncommitted edits or leftover files.
  The runner runs exactly the code you pushed, on a machine nobody touched. That is what the
  `strong` and `signed` gates trust.
- **No merge while red.** The git host refuses to merge the pull request while a test fails
  or a rule has no test. Nobody has to remember to check.

Teammates do not need a remote runner to see results: `purlin:test` commits them, so they are
in the repository, readable on the git host and on the board after a pull. Say so once, on the
`passed` page.

## Pages

- `docs/solo-workflow.md` (gate `passed`): the loop is `purlin:spec`, `purlin:build`,
  `purlin:test`, `git push`. The diagram shows exactly that, plus the test results commit
  `purlin:test` makes and the reviewer reading `.purlin/tests.md` on the host. No audit, no
  gate check, no record on this page except one sentence saying `purlin:audit` can be run to
  see how good the tests are and counts for nothing here. Then "When you want a remote
  runner": the three reasons, `purlin:init` explains and asks, and what `purlin:test` prints
  when a proof needs another operating system.
- `docs/team-workflow.md` (gate `strong`): the runner runs the tests and the audit and writes
  the record; a local `purlin:audit` shows what CI will find and counts for nothing;
  `purlin:test --remote` for a counting record before the merge. The three reasons again,
  once, where the runner is introduced.
- `docs/regulated-workflow.md`: the same base, then signing; no `--commit`, no developer
  record anywhere.
- `docs/how-purlin-works.md`: sources are `local` and `ci`; the "Questions every developer
  asks" section says the `passed` loop in one line and points at the three reasons; the table
  of who writes what gains the test results row (`purlin:test`, `.purlin/tests/`, you, at
  every gate, counts at `passed`).
- `docs/running-and-records.md`: `purlin:test` and its two files; `purlin:audit` measures;
  the record is CI's; `--remote` on test; the developer record paragraph deleted.
- `docs/getting-started.md`, `docs/raising-the-gate-and-upgrading.md`, `docs/index.md`,
  `README.md`: the loop, the gate table's "Where the counting record comes from" column
  (`passed`: your machine's test results; `strong` and `signed`: CI), the command table.
- `references/formats/tests_format.md` (lane 10A wrote it): read it and link it from the
  pages that name the files.

## Skills

`skills/test`, `skills/audit`, `skills/init`, `skills/status`, `skills/build`, `skills/spec`
and `agents/purlin.md`: every sentence that names `--commit`, a developer record, `purlin:audit
--remote`, `--ci`, or a script a person runs at `passed`, rewritten to lane 10A's behaviour.
The `purlin:init` skill carries the three reasons verbatim and the prerequisite checks.
`dev/test_skills.py` follows. `references/purlin_commands.md` is the one home of each
command's sentence; the skill frontmatter descriptions match it word for word.

## The slides

The deck at `https://claude.ai/artifact/Rifxf2KXfH4CTzfQ9pZ9is` is the orchestrator's; you
write `dev/plans/lanes/tl-10B-slides.md` with the final step lists for the three gates in the
deck's shape (number, LOCAL or REMOTE, command, what happens, in the fewest words), and the
orchestrator republishes. The `passed` slide is four steps: spec, build, test, push.

## Acceptance

```
pytest dev/test_vocabulary.py dev/test_skills.py
grep -rn "\-\-commit\|developer record\|audit --remote\|--ci\b" docs/ README.md skills/ agents/ references/ | grep -v "retired\|glossary"   (nothing)
grep -rn "gate_check" docs/solo-workflow.md   (nothing)
```

Report in the DONE shape of `tl-_rules.md`, with one sentence per diagram, the code lines
each page was checked against, and decisions.
