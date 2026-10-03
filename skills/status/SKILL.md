---
name: status
description: "Show where the project stands: whether the tests are met, whether it is signed, each rule's two cells, and what is left to do"
---

Show where every feature stands: whether the tests are met, whether this code is signed, how many
rules pass their tests, what is left to do, and what to do next. This skill writes no file you
commit; it refreshes the dashboard's data, which git ignores. For a project Purlin 0.9.5 set up,
while its upgrade is pending, it writes nothing.

**Paths in this skill:** every `references/`, `templates/`, `scripts/` and `agents/` path below
is relative to the plugin root; see `references/purlin_commands.md#path-resolution`.

## Usage

```
purlin:status                   Every feature and anchor
purlin:status <name>            One spec: its rules and their cells
```

Plain language reaches the same place: "where are we", "what is left", "show the board".

## Step 1: call the tool

Get the status from the tool `mcp__plugin_purlin_purlin__sync_status`, passing `project_root`:
the top folder of the git checkout you are working in. Where the session lists it as a
deferred tool, load it with ToolSearch first. Where the session does not have it, run the
script, which prints the same status:

```bash
sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_status.py" --project-root .
```

Never read `.purlin/report-data.js` or `purlin-report.html` as the status: they hold what the
last command saw.

In a worktree the top folder is the worktree's own, since each checkout has its own results,
status and dashboard.

`No Purlin project root at <folder>: .purlin/config.json is not there. Run purlin:init.` means
this folder is not set up. Say so and name `purlin:init`. Never pass another folder to get an
answer.

## Step 2: print the two facts and the table

Print the status as the tool or the script printed it. Never rebuild it as a table of your own.
It opens on three lines, then the table:

```
Purlin status: labconnect, plugin <version>
Tests: not met
Sign-off: signed 0.1.0, 4 commits since

Spec                            Rules  Proofs          Tests
──────────────────────────────────────────────────────────────
Anchors
security_no_dangerous_patterns  8      21              8 of 8
Specs
billing                         14     22 · 2 no test  12 of 14 · 1 partial · 1 failing
login                           11     20              11 of 11
```

`Tests:` reads `met` when every rule passes its tests on the committed evidence, else `not met`.
`Sign-off:` reads `signed <version> at <sha7>`, `signed <version>, <n> commits since` or
`not signed`. `references/evidence_and_signoff.md` defines both.

The table has a row per spec, most work left first, the anchors under `Anchors` above the rest
under `Specs`. `Rules` counts the spec's rules. `Proofs` counts every proof line, then
`· <k> no test` where no test carries a proof's marker. `Tests` is `<passed> of <rules>`, then
`· <k> by hand`, `· <k> partial` and `· <k> failing` where not zero; `by hand` counts the rules
checked at sign-off, and `partial` means the tests pass on one operating system and not another.
An anchor's cell then adds `· <k> out of date`, as in `0 of 11 · 11 out of date`: an anchor
covers the whole project, so a change to any tracked file puts its results out of date until
the next run.
A `Strong` column shows only where the audit read a rule, as `<strong> of <n>`: of the rules
that pass their tests and have a tested proof, the ones it found strong. An anchor's cell reads
one word, `weak`, `out of date` or `spot-checked`, or nothing: no bug is planted for an anchor's
rule.

For a project Purlin 0.9.5 set up, while its upgrade is pending, the tool answers three lines
and no table: the first line, `This project was set up by Purlin 0.9.5. Nothing here counts
until it is brought to <version>.` and `→ Run: purlin:init --update`. Print them and stop. The
dashboard page and its data file are left as they were.

## Step 3: print the summary and `Left to do`

The tool ends on one sentence and `Left to do`, the words every command ends on in the terminal:

```
40 rules. 35 pass their tests. The audit found 30 of 35 rules strong (85%): 30 strong, 2 weak, 3 spot-checked.
Left to do:
  3 rules to write a test for: purlin:build
  2 rules to test: purlin:test
```

The sentence counts the rules that pass their tests, then the share the audit found strong where
it read any. `Left to do` holds one line per kind of work, in the order it is done, with its count
and its command. Print the lines the status holds. Never recount them: the command line and
the dashboard must show one answer from one computation.

The line `<n> features whose results are not committed: purlin:test --commit` shows only once
nothing else stops the tests being met. While a rule is still to fix, to test or to write a test
for, results that are written and not committed are not listed: the run that clears that work
writes them again.

Anything the tool prints between the table and the sentence is its own: a rule of an anchor that
passes with nothing to check, a spec whose scope names files not written yet, an anchor behind its
source, the line saying the tests setting changed, each test comment to correct, its warnings
and `→ Run: purlin:init --update`. Print them
as they are, or nothing when the tool returned nothing. Where a warning says a number is written
twice, follow `Renumbering` in `skills/spec/SKILL.md`.

The last warning lists each test that still carries a marker from Purlin 0.9.5, one per line,
with the feature and the rule the marker names:

```
9 tests still carry a marker from Purlin 0.9.5, which is not read:
  packages/web/test/parameter_lfo.test.ts:154  parameter_lfo RULE-4
  ...
For each, write the proof with purlin:spec, put the comment above the test, and take the old tag out.
```

The line number is the old tag's own, in the file as it stands. Over 20 tests, the first 20 are
listed and the rest counted. `purlin:sign` refuses while one remains.

## With a name

Naming a spec shows its rules and their standing. Match `specs/**/<name>.md`, then the name
as part of a spec file name; when several match, list them and ask which one, and when none
does, print the whole table. The tool shows every spec at once, so for one spec run the script
with the spec's name, the file name without `.md`:

```bash
sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_status.py" --project-root . --spec <name>
```

Print what it prints. It opens on the spec's path and how many rules it has, then gives one line
per rule with its two cells. Under a cell that reads neither `passed` nor `strong` come its
reasons, each after the cell's word; then one line per proof with its result and its tests:

```
specs/auth/login.md: 3 rules
  RULE-1  passed  strong
    PROOF-1  passed  tests/test_login.py::test_proof_1
  RULE-2  no test  waiting
    no test: no test for PROOF-2
    waiting: waiting for its tests to pass
    PROOF-2  no test
  RULE-3  checked at sign-off  checked at sign-off
    checked at sign-off: no sign-off has checked it yet
    PROOF-3  hand check
```

Where the spec has a mistake, the script prints each mistake first, as the status's warnings
word it. The view writes nothing. The next step is the Step 4 row for the first kind of work
this spec's rules wait for.

## Step 4: name the next step

The next step is the first line of `Left to do`. Add no line of your own; a
`→ Run: purlin:init --update` the tool printed comes first.

| The first line after the sentence | Next step |
|-----------------------------------|-----------|
| `<n> specs to repair` or `<n> rules to write a proof for` | `→ Run: purlin:spec` |
| `<n> test comments to correct` | `→ Run: purlin:build` |
| `<n> rules to fix`, `to write a test for` or `to strengthen` | `→ Run: purlin:build` |
| `<n> rules to test` | `→ Run: purlin:test` |
| `<n> slow proofs to run` | `→ Run: purlin:test --all` |
| `<n> rules to test on <systems>` | `→ Run purlin:test on <systems>`. It is an instruction, not a command line: do as `skills/test/SKILL.md`, Step 5 says |
| `<n> features whose results are not committed` | `→ Run: purlin:test --commit` |
| `Every rule passes its tests on the committed evidence. To sign it: purlin:sign` | `→ Run: purlin:sign`, when a person chooses to sign |
| `Every rule passes its tests on the committed evidence. Before a sign-off, run <command>: ...` | `→ Run: <command>`. `purlin:sign` refuses these results as they stand: some were taken on an earlier version of the code, or while files were changed and not committed |
